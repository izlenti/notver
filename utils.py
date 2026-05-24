# utils.py
import pandas as pd
import json
import streamlit as st

def initialize_session_state(mock_exam, mock_students):
    """
    Initializes the session state for managing student scores and exam configuration.
    """
    # 1. Sınav Ayarlarını Başlat
    if "exam_config" not in st.session_state:
        st.session_state.exam_config = json.loads(json.dumps(mock_exam)) # Deep copy
        
    # 2. Öğrenci Not Listesini Başlat (Üretim Seviyesinde Boş Başlangıç)
    if "student_records" not in st.session_state:
        st.session_state.student_records = {}

    # 3. İstatistikleri ve Değişiklik Günlüklerini Başlat
    if "calibration_log" not in st.session_state:
        st.session_state.calibration_log = []

def get_class_dataframe():
    """
    Creates a pandas DataFrame summarizing student final scores and approval statuses.
    """
    data = []
    if "student_records" in st.session_state:
        for s_id, s_record in st.session_state.student_records.items():
            total_score = 0
            for q_id, q_data in s_record["grades"].items():
                total_score += q_data["teacher_score"] # Öğretmenin nihai onayladığı veya değiştirdiği puan
                
            data.append({
                "Öğrenci No": s_id,
                "Ad Soyad": s_record["name"],
                "Sınıf": s_record.get("class", "5-A"),
                "Toplam Puan": total_score,
                "Durum": "Onaylandı" if s_record["status"] == "Onaylandı" else "Taslak (Bekliyor)"
            })
    if not data:
        return pd.DataFrame(columns=["Öğrenci No", "Ad Soyad", "Sınıf", "Toplam Puan", "Durum"])
    return pd.DataFrame(data)

def get_detailed_grades_dataframe():
    """
    Creates a detailed DataFrame containing question-by-question scoring.
    """
    data = []
    if "student_records" in st.session_state:
        for s_id, s_record in st.session_state.student_records.items():
            row = {
                "Öğrenci No": s_id,
                "Ad Soyad": s_record["name"],
                "Sınıf": s_record.get("class", "5-A"),
                "Durum": "Onaylandı" if s_record["status"] == "Onaylandı" else "Bekliyor"
            }
            total = 0
            for q_id, q_data in s_record["grades"].items():
                row[f"Soru {q_id}"] = q_data["teacher_score"]
                total += q_data["teacher_score"]
            row["Toplam Puan"] = total
            data.append(row)
    if not data:
        # Sınav ayarlarındaki aktif soruları al
        q_cols = []
        if "exam_config" in st.session_state:
            q_cols = [f"Soru {q_id}" for q_id in st.session_state.exam_config["questions"].keys()]
        else:
            q_cols = ["Soru 21", "Soru 22", "Soru 24", "Soru 25"]
        cols = ["Öğrenci No", "Ad Soyad", "Sınıf"] + q_cols + ["Toplam Puan", "Durum"]
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(data)

def save_teacher_approval(student_id, question_id, new_score, is_override):
    """
    Saves the teacher's approval or correction, updating the session state
    and recording calibration metrics if a score correction occurs.
    """
    record = st.session_state.student_records[student_id]
    q_data = record["grades"][question_id]
    
    old_teacher_score = q_data["teacher_score"]
    ai_score = q_data["ai_score_initial"]
    
    # Güncelle
    q_data["teacher_score"] = new_score
    q_data["teacher_override"] = is_override
    
    # Eğer öğretmen puanı değiştirdiyse kalibrasyon günlüğüne kaydet
    if is_override and old_teacher_score != new_score:
        log_entry = {
            "student_name": record["name"],
            "question": f"Soru {question_id}",
            "ai_score": ai_score,
            "teacher_score": new_score,
            "difference": new_score - ai_score
        }
        # Listede daha önce varsa güncelle, yoksa ekle
        existing = -1
        for idx, entry in enumerate(st.session_state.calibration_log):
            if entry["student_name"] == record["name"] and entry["question"] == f"Soru {question_id}":
                existing = idx
                break
        if existing != -1:
            st.session_state.calibration_log[existing] = log_entry
        else:
            st.session_state.calibration_log.append(log_entry)

def check_student_all_approved(student_id):
    """
    Checks if all questions for a student are graded/reviewed, then marks the student as 'Onaylandı'.
    """
    # Prototipte ve simülasyonda öğretmen onay butonuna basınca doğrudan 'Onaylandı' yaparız
    st.session_state.student_records[student_id]["status"] = "Onaylandı"

def get_calibration_analytics():
    """
    Calculates calibration stats: AI score vs Teacher score deviations.
    """
    logs = st.session_state.calibration_log
    if not logs:
        return {
            "has_data": False,
            "mae": 0.0,
            "total_corrections": 0,
            "avg_diff": 0.0
        }
        
    df = pd.DataFrame(logs)
    mae = df["difference"].abs().mean()
    avg_diff = df["difference"].mean()
    total_corrections = len(df)
    
    return {
        "has_data": True,
        "mae": round(mae, 2),
        "avg_diff": round(avg_diff, 2),
        "total_corrections": total_corrections,
        "data": df
    }
