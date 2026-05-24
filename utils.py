# utils.py
import pandas as pd
import json
import streamlit as st


def initialize_session_state():
    """Oturum değişkenlerini başlatır. Boş başlangıç — sıfır mock veri."""

    # Aktif sekme
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "cevap_anahtari"

    # Sınav konfigürasyonu (cevap anahtarı bilgileri)
    if "exam_config" not in st.session_state:
        st.session_state.exam_config = {
            "grade": "",          # "5", "6", "7", "8"
            "branch": "",         # "A", "B", ..., "I"
            "answer_key_images": [],   # PIL Image listesi (cevap anahtarı sayfaları)
            "questions": {},      # {q_id: {title, max_score, correct_solution}}
            "total_max_score": 0,
            "key_saved": False,
        }

    # Öğrenci kayıtları
    # {
    #   "101": {
    #     "name": "Ali Veli", "no": "101", "class": "5", "branch": "A",
    #     "image": PIL Image,
    #     "status": "Bekliyor" | "Değerlendirildi" | "Onaylandı",
    #     "grades": {"1": {"score": 17, "max_score": 17, "feedback": "..."}, ...},
    #     "total_score": 0
    #   }
    # }
    if "student_records" not in st.session_state:
        st.session_state.student_records = {}

    # Öğrenci görsel deposu (PIL Image, session_state'de büyük objeler ayrı key'de)
    if "student_images" not in st.session_state:
        st.session_state.student_images = {}


def get_approved_grades_dataframe():
    """
    Onaylanmış öğrencilerin soru bazlı puanlarını
    okul numarasına göre sıralı DataFrame olarak döndürür.
    """
    records = st.session_state.get("student_records", {})
    questions = st.session_state.get("exam_config", {}).get("questions", {})

    data = []
    for s_no, rec in records.items():
        if rec.get("status") != "Onaylandı":
            continue

        row = {
            "No": rec.get("no", s_no),
            "Ad Soyad": rec.get("name", "—"),
            "Sınıf": f"{rec.get('class', '')}",
            "Şube": rec.get("branch", ""),
        }

        total = 0
        for q_id in sorted(questions.keys(), key=lambda x: int(x) if x.isdigit() else x):
            grade = rec.get("grades", {}).get(q_id, {})
            score = grade.get("score", 0)
            max_s = grade.get("max_score", questions.get(q_id, {}).get("max_score", 0))
            row[f"Soru {q_id} ({max_s}p)"] = score
            total += score

        row["Toplam"] = total
        data.append(row)

    if not data:
        # Boş ama doğru sütunlu DataFrame
        base_cols = ["No", "Ad Soyad", "Sınıf", "Şube"]
        q_cols = [f"Soru {q_id} ({q['max_score']}p)" for q_id, q in questions.items()]
        return pd.DataFrame(columns=base_cols + q_cols + ["Toplam"])

    df = pd.DataFrame(data)
    # Numara sırasına göre sırala
    try:
        df["_sort"] = pd.to_numeric(df["No"], errors="coerce")
        df = df.sort_values("_sort").drop(columns=["_sort"])
    except Exception:
        df = df.sort_values("No")

    return df.reset_index(drop=True)


def get_all_students_dataframe():
    """Tüm öğrencilerin özet listesini döndürür (Not Defteri için değil, genel liste)."""
    records = st.session_state.get("student_records", {})
    data = []
    for s_no, rec in records.items():
        data.append({
            "No": rec.get("no", s_no),
            "Ad Soyad": rec.get("name", "—"),
            "Sınıf": f"{rec.get('class', '')}",
            "Şube": rec.get("branch", ""),
            "Toplam Puan": rec.get("total_score", 0),
            "Durum": rec.get("status", "Bekliyor"),
        })
    if not data:
        return pd.DataFrame(columns=["No", "Ad Soyad", "Sınıf", "Şube", "Toplam Puan", "Durum"])
    return pd.DataFrame(data)


# Legacy uyumluluk
def get_class_dataframe():
    return get_all_students_dataframe()

def get_detailed_grades_dataframe():
    return get_approved_grades_dataframe()

def save_teacher_approval(student_id, question_id, new_score, is_override):
    record = st.session_state.student_records.get(student_id)
    if not record:
        return
    if question_id in record.get("grades", {}):
        record["grades"][question_id]["score"] = new_score
        record["grades"][question_id]["teacher_override"] = is_override

def check_student_all_approved(student_id):
    st.session_state.student_records[student_id]["status"] = "Onaylandı"

def get_calibration_analytics():
    return {"has_data": False, "mae": 0.0, "total_corrections": 0, "avg_diff": 0.0}
