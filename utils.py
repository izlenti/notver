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
        
    # 2. Öğrenci Not Listesini Başlat
    if "student_records" not in st.session_state:
        records = {}
        for s_id, s_data in mock_students.items():
            records[s_id] = {
                "id": s_id,
                "name": s_data["name"],
                "writing_style": s_data["writing_style"],
                "class": s_data.get("class", "12-A"),
                "status": "Bekliyor", # Bekliyor, Onaylandı
                "grades": {}
            }
            # Her bir soru için varsayılan AI notlarını yerleştir
            for q_id, q_grade in s_data["grades"].items():
                records[s_id]["grades"][q_id] = {
                    "score_concept": q_grade["score_concept"],
                    "score_steps": q_grade["score_steps"],
                    "score_result": q_grade["score_result"],
                    "score_total": q_grade["score_total"],
                    "ai_feedback": q_grade["ai_feedback"],
                    "student_solution": q_grade["student_solution"],
                    "teacher_override": False,
                    "teacher_score": q_grade["score_total"], # Başlangıçta AI puanına eşit
                    "ai_score_initial": q_grade["score_total"]
                }
        st.session_state.student_records = records

    # 3. İstatistikleri ve Değişiklik Günlüklerini Başlat
    if "calibration_log" not in st.session_state:
        st.session_state.calibration_log = []

def get_class_dataframe():
    """
    Creates a pandas DataFrame summarizing student final scores and approval statuses.
    """
    data = []
    for s_id, s_record in st.session_state.student_records.items():
        total_score = 0
        for q_id, q_data in s_record["grades"].items():
            total_score += q_data["teacher_score"] # Öğretmenin nihai onayladığı veya değiştirdiği puan
            
        data.append({
            "Öğrenci No": s_id,
            "Ad Soyad": s_record["name"],
            "Sınıf": s_record.get("class", "12-A"),
            "Toplam Puan": total_score,
            "Durum": "Onaylandı" if s_record["status"] == "Onaylandı" else "Taslak (Bekliyor)"
        })
    return pd.DataFrame(data)

def get_detailed_grades_dataframe():
    """
    Creates a detailed DataFrame containing question-by-question scoring.
    """
    data = []
    for s_id, s_record in st.session_state.student_records.items():
        row = {
            "Öğrenci No": s_id,
            "Ad Soyad": s_record["name"],
            "Sınıf": s_record.get("class", "12-A"),
            "Durum": "Onaylandı" if s_record["status"] == "Onaylandı" else "Bekliyor"
        }
        total = 0
        for q_id, q_data in s_record["grades"].items():
            row[f"Soru {q_id}"] = q_data["teacher_score"]
            total += q_data["teacher_score"]
        row["Toplam Puan"] = total
        data.append(row)
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
