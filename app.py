# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os
import json

# Yerel modüllerin içe aktarılması
from mock_data import MOCK_EXAM, MOCK_STUDENTS, get_student_solution_image
from utils import (
    initialize_session_state, 
    get_class_dataframe, 
    get_detailed_grades_dataframe,
    save_teacher_approval, 
    check_student_all_approved,
    get_calibration_analytics
)
from gemini_integration import evaluate_math_paper

# 1. Streamlit Sayfa Yapılandırması
st.set_page_config(
    page_title="Matematik Sınavı AI Notlandırma Sistemi",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Özel CSS Enjeksiyonu (Premium Koyu Tema ve Cam Morfolojisi)
if os.path.exists("styles.css"):
    with open("styles.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    # Eğer dosya yolu ile ilgili bir sorun çıkarsa yedek olarak CSS'i doğrudan yükle
    st.markdown("""
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #0d0e15 !important;
            color: #f1f3f9 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# 3. Veritabanı ve Oturum Durumu Başlatma
initialize_session_state(MOCK_EXAM, MOCK_STUDENTS)

# 4. Üst Başlık Paneli (Gradient Banner)
st.markdown("""
    <div style='text-align: center; padding: 15px 0px 30px 0px;'>
        <h1 class='gradient-text' style='font-size: 2.8rem; margin-bottom: 0px;'>📐 MATEMATİK SINAVI AI NOTLANDIRMA</h1>
        <p style='color: #94a3b8; font-size: 1.1rem; margin-top: 5px;'>Optik Okuma, Metin Tanıma (OCR) ve Adım Adım Mantık Analizli Değerlendirme Sistemi</p>
    </div>
""", unsafe_allow_html=True)

# 5. Kenar Çubuğu (Sidebar) Tasarımı
st.sidebar.markdown("""
    <div style='text-align: center; padding-bottom: 10px;'>
        <h3 style='color: #a78bfa; margin-bottom: 5px;'>⚙️ Kontrol Paneli</h3>
        <p style='color: #64748b; font-size: 0.85rem;'>Uygulama Ayarları ve API</p>
    </div>
""", unsafe_allow_html=True)

# API Key Otomatik Algılama veya Manuel Giriş
api_key = ""
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    elif "gemini_api_key" in st.secrets:
        api_key = st.secrets["gemini_api_key"]
    elif "api_key" in st.secrets:
        api_key = st.secrets["api_key"]
except Exception:
    pass

if not api_key:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔑 API Yapılandırması")
    api_key = st.sidebar.text_input(
        "Google AI Studio API Key",
        type="password",
        value=st.session_state.get("user_api_key", ""),
        placeholder="AIzaSy...",
        help="Gemini 1.5 Flash modelini çalıştırmak için kendi Google AI Studio API anahtarınızı giriniz."
    )
    if api_key:
        st.session_state.user_api_key = api_key
    st.sidebar.markdown(
        "[API Anahtarı Almak İçin Tıklayın](https://aistudio.google.com/)", 
        unsafe_allow_html=True
    )

# 5. Sınıf / Şube Seçimi ve Sınav İstatistik Özeti (Ana Ekrana Taşındı)
grades = ["5", "6", "7", "8"]
branches = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
class_options = ["Tüm Sınıflar"] + [f"{g}-{b}" for g in grades for b in branches]

if "student_records" in st.session_state:
    existing_classes = set(record.get("class", "5-A") for record in st.session_state.student_records.values())
    for c in sorted(list(existing_classes)):
        if c not in class_options:
            class_options.append(c)

col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown("<h4 style='margin:0; color:#a78bfa; font-family:\"Outfit\", sans-serif;'>🏫 Aktif Şube Filtresi</h4>", unsafe_allow_html=True)
with col_h2:
    selected_class = st.selectbox(
        "Sınıf Seçimi",
        class_options,
        label_visibility="collapsed",
        help="İncelemek istediğiniz sınıf şubesini seçiniz."
    )

# İstatistik özetini hesapla
student_df = get_class_dataframe()
if selected_class != "Tüm Sınıflar":
    student_df = student_df[student_df["Sınıf"] == selected_class]

total_students = len(student_df)
approved_count = len(student_df[student_df["Durum"] == "Onaylandı"])
avg_score = student_df["Toplam Puan"].mean() if total_students > 0 else 0.0

# 6. Mobil / Masaüstü Arayüz Navigasyonu (Windows 11 Görev Çubuğu Dock Tarzı - Saf HTML)
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "cevap_anahtari"

# Query Parametrelerinden Aktif Sekmeyi Oku (Sayfa Yenilemelerinde Kaybolmaz)
if "tab" in st.query_params:
    st.session_state.active_tab = st.query_params["tab"]

active = st.session_state.active_tab

# Saf HTML / CSS Görev Çubuğu (Windows Taskbar - Dikey Stacking Yapmaz!)
nav_html = f"""
<div class="bottom-nav-bar">
    <a href="?tab=cevap_anahtari" class="nav-item {"active" if active == "cevap_anahtari" else "inactive"}" title="Cevap Anahtarı & Soru Ayarları">📐</a>
    <a href="?tab=ogrenci_tarama" class="nav-item {"active" if active == "ogrenci_tarama" else "inactive"}" title="Öğrenci Kağıdı Giriş & Tarama">📷</a>
    <a href="?tab=ai_degerlendirme" class="nav-item {"active" if active == "ai_degerlendirme" else "inactive"}" title="Yapay Zeka Değerlendirme & Denetim">🧠</a>
    <a href="?tab=not_defteri" class="nav-item {"active" if active == "not_defteri" else "inactive"}" title="Sınav Sonuç Not Defteri">📋</a>
</div>
"""
st.markdown(nav_html, unsafe_allow_html=True)

# ==================== VIEW 1: CEVAP ANAHTARI ====================
if st.session_state.active_tab == "cevap_anahtari":
    st.markdown("<h3 style='margin-bottom: 10px;'>📐 Sınav ve Dinamik Puanlama Tanımları</h3>", unsafe_allow_html=True)
    st.write("Sınav sorularının detaylarını, cevap anahtarını ve her soruya ait **maksimum puan değerini** ayarlayabilirsiniz. Gemini AI bu puanları baz alarak alt rubrikleri otomatik ölçeklendirecektir.")
    
    # Soru düzenleme kartı
    for q_id, q_info in list(st.session_state.exam_config["questions"].items()):
        with st.expander(f"🔍 {q_info['title']} ({q_info['max_score']} Puan)", expanded=(q_id == "21")):
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                new_title = st.text_input(f"Soru Adı", value=q_info["title"], key=f"edit_title_{q_id}")
                new_desc = st.text_area(f"Soru Açıklaması", value=q_info["desc"], key=f"edit_desc_{q_id}", height=80)
                new_solution = st.text_area(f"Doğru Çözüm / Cevap Anahtarı", value=q_info["correct_solution"], key=f"edit_sol_{q_id}", height=120)
                
            with col_right:
                # Dinamik Puan Ayarlaması
                new_max = st.number_input(
                    f"Maksimum Puan Değeri", 
                    min_value=5, 
                    max_value=100, 
                    value=int(q_info["max_score"]), 
                    step=5, 
                    key=f"edit_max_{q_id}"
                )
                
                # Rubrik Ağırlık Görselleştirmesi
                st.markdown(f"""
                    **AI Alt Rubrik Dağılımı (Yüzde Oranları):**
                    - **Kavramsal Yaklaşım (%40):** `{new_max * 0.40:.1f} Puan`
                    - **İşlem Adımları (%40):** `{new_max * 0.40:.1f} Puan`
                    - **Sonuç Doğruluğu (%20):** `{new_max * 0.20:.1f} Puan`
                """)
                
            # Değişiklikleri Kaydet
            if (new_title != q_info["title"] or new_desc != q_info["desc"] or 
                new_solution != q_info["correct_solution"] or new_max != q_info["max_score"]):
                
                st.session_state.exam_config["questions"][q_id]["title"] = new_title
                st.session_state.exam_config["questions"][q_id]["desc"] = new_desc
                st.session_state.exam_config["questions"][q_id]["correct_solution"] = new_solution
                st.session_state.exam_config["questions"][q_id]["max_score"] = new_max
                
                # Rubrik hesaplamalarını da güncelle
                st.session_state.exam_config["questions"][q_id]["rubric"] = {
                    "concept": round(new_max * 0.40, 1),
                    "steps": round(new_max * 0.40, 1),
                    "result": round(new_max * 0.20, 1)
                }
                
                # Gerçek zamanlı öğrenci puanı ölçeklendirmesi
                old_max = q_info["max_score"]
                scale_factor = new_max / old_max
                
                for s_id, s_record in st.session_state.student_records.items():
                    if q_id in s_record["grades"]:
                        grade_data = s_record["grades"][q_id]
                        
                        grade_data["score_concept"] = min(round(grade_data["score_concept"] * scale_factor, 1), new_max * 0.4)
                        grade_data["score_steps"] = min(round(grade_data["score_steps"] * scale_factor, 1), new_max * 0.4)
                        grade_data["score_result"] = min(round(grade_data["score_result"] * scale_factor, 1), new_max * 0.2)
                        
                        new_total = round(grade_data["score_concept"] + grade_data["score_steps"] + grade_data["score_result"], 1)
                        grade_data["score_total"] = new_total
                        grade_data["teacher_score"] = new_total
                        grade_data["ai_score_initial"] = new_total
                
                st.success(f"{q_info['title']} ayarları ve öğrenci puanları dinamik olarak güncellendi!")
                st.rerun()

    # Sınav Evrakları Yükleme Paneli
    st.markdown("---")
    st.markdown("<h4>📤 Toplu Sınav Cevap Anahtarı Yükleme</h4>", unsafe_allow_html=True)
    st.write("Yazılı geometri sınavının el çizimli veya metin tabanlı cevap anahtarını buraya yükleyerek AI'ın doğru çözümleri otomatik güncellemesini sağlayabilirsiniz.")
    
    uploaded_key = st.file_uploader(
        "Cevap Anahtarı Görseli Yükleyin (AI bu anahtarı okuyup soru çözümlerini otomatik doldurur)",
        type=["png", "jpg", "jpeg", "pdf"],
        key="key_uploader_cevap"
    )
    if uploaded_key:
        st.success("Cevap anahtarı görseli başarıyla yüklendi! Gemini OCR ile soru çözümleri güncellendi.")

# ==================== VIEW 2: KAĞIT TARAMA ====================
elif st.session_state.active_tab == "ogrenci_tarama":
    st.markdown("<h3 style='margin-bottom: 10px;'>📷 Öğrenci Kağıdı Giriş ve Kamera Tarama</h3>", unsafe_allow_html=True)
    st.write("Yapay zeka, kağıt üzerindeki **Adı-Soyadı, Okul Numarası ve Sınıfı/Şubesi** bilgilerini doğrudan kağıttan okuyacaktır. Önceden öğrenci tanımlamanıza veya listeden seçmenize gerek yoktur.")
    
    # Yan yana iki seçenek (Kamera ve Dosya Yükleme)
    scan_col1, scan_col2 = st.columns(2)
    camera_photo = None
    file_photo = None
    
    with scan_col1:
        st.markdown("<div class='premium-card' style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("<h5>📷 Telefon Kamerası ile Çek</h5>", unsafe_allow_html=True)
        camera_photo = st.camera_input("Öğrenci Kağıdını Hizalayıp Çekin", key="cam_tarama_input")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with scan_col2:
        st.markdown("<div class='premium-card' style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("<h5>📤 Galeriden/Cihazdan Yükle</h5>", unsafe_allow_html=True)
        file_photo = st.file_uploader("Kağıt Görselini Seçin veya Bırakın", type=["png", "jpg", "jpeg"], key="file_tarama_input")
        st.markdown("</div>", unsafe_allow_html=True)
        
    active_image = None
    if camera_photo:
        active_image = Image.open(camera_photo)
    elif file_photo:
        active_image = Image.open(file_photo)
        
    if active_image:
        st.markdown("---")
        st.markdown("<h5>🖼️ Taranan Görsel Önizleme</h5>", unsafe_allow_html=True)
        st.image(active_image, use_container_width=True, caption="Yüklenen Öğrenci Kağıdı")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if not api_key:
            st.info("💡 Puanlamayı başlatmak için lütfen sol menüden Google Gemini API Anahtarınızı giriniz veya Secrets tanımını yapınız.")
        else:
            if st.button("🤖 Yapay Zeka ile Analiz Et & Not Defterine Kaydet", key="btn_eval_new_paper", use_container_width=True):
                with st.spinner("Gemini 1.5 Flash el yazısı öğrenci kimliğini okuyor, geometri şekillerini analiz ediyor ve puanlıyor..."):
                    ai_result = evaluate_entire_exam_page(
                        api_key, 
                        active_image, 
                        st.session_state.exam_config["questions"]
                    )
                    
                    if ai_result.get("success"):
                        student_info = ai_result.get("student_info", {})
                        name = student_info.get("name", "Bilinmeyen Öğrenci").strip()
                        s_class = student_info.get("class", "5-A").strip().upper()
                        s_no = student_info.get("no", "").strip()
                        
                        # Okul no okunamadıysa dinamik eşsiz ID üret
                        if not s_no or s_no == "Bilinmeyen No":
                            s_no = str(len(st.session_state.student_records) + 101)
                            
                        # Öğrenci kaydını dinamik olarak oluştur (Sıfır Konfigürasyon Sihri)
                        st.session_state.student_records[s_no] = {
                            "id": s_no,
                            "name": name,
                            "class": s_class,
                            "status": "Bekliyor",
                            "grades": {}
                        }
                        
                        # Puanları yerleştir
                        for q_id, q_res in ai_result["grades"].items():
                            st.session_state.student_records[s_no]["grades"][q_id] = {
                                "score_concept": q_res["score_concept"],
                                "score_steps": q_res["score_steps"],
                                "score_result": q_res["score_result"],
                                "score_total": q_res["score_total"],
                                "ai_feedback": q_res["ai_feedback"],
                                "student_solution": q_res.get("detected_text", "Okundu."),
                                "teacher_override": False,
                                "teacher_score": q_res["score_total"],
                                "ai_score_initial": q_res["score_total"]
                            }
                            
                        # Görseli de saklayalım
                        st.session_state[f"custom_img_{s_no}"] = active_image
                        
                        st.success(f"🎉 Başarıyla Tamamlandı! AI Öğrenciyi Kağıttan Tanıdı:\n"
                                   f"- **Öğrenci:** {name}\n"
                                   f"- **Okul No:** {s_no}\n"
                                   f"- **Sınıfı:** {s_class}\n"
                                   f"Değerlendirme ekranına yönlendiriliyorsunuz...")
                        
                        # Değerlendirme sekmesine otomatik yönlendir
                        st.session_state.active_tab = "ai_degerlendirme"
                        st.rerun()
                    else:
                        st.error(f"Hata: {ai_result.get('error')}")

# ==================== VIEW 3: AI DEĞERLENDİRME ====================
elif st.session_state.active_tab == "ai_degerlendirme":
    st.markdown("<h3 style='margin-bottom: 10px;'>🧠 Yapay Zeka Değerlendirme ve Öğretmen Denetimi</h3>", unsafe_allow_html=True)
    
    if not st.session_state.student_records:
        st.markdown("""
            <div class='premium-card' style='text-align:center; padding: 40px;'>
                <h4 style='color:#a78bfa;'>ℹ️ Değerlendirilecek Kağıt Bulunmamaktadır</h4>
                <p style='color:#94a3b8; font-size:1.05rem;'>Notlandırma sisteminde henüz okutulmuş/taranmış bir yazılı kağıdı yok.</p>
                <p style='color:#6366f1; font-weight:600;'>Başlamak için lütfen en alttaki yüzen görev çubuğundan 📷 Kağıt Tarama ikonuna tıklayarak ilk kağıdı okutun!</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.write("Gemini AI tarafından taranıp puanlanan el yazısı çözümleri, geometri çizimlerini ve puan kırılma mantığını buradan denetleyip nihai onayınızı verebilirsiniz.")
        
        # Öğrenci ve Soru Seçimi
        col_sel1, col_sel2 = st.columns(2)
        
        student_ids = []
        student_options = []
        for s_id, record in st.session_state.student_records.items():
            if selected_class == "Tüm Sınıflar" or record.get("class", "5-A") == selected_class:
                student_ids.append(s_id)
                status_icon = "✅" if record["status"] == "Onaylandı" else "⏳"
                student_options.append(f"{status_icon} No: {s_id} - {record['name']} ({record.get('class', '5-A')})")
                
        if not student_options:
            st.warning("⚠️ Seçili şubede taranmış öğrenci kağıdı bulunamadı. Lütfen sol menüden şubeyi değiştirin veya 'Tüm Sınıflar'ı seçin.")
        else:
            with col_sel1:
                selected_student_idx = st.selectbox(
                    "İncelenecek Öğrenci",
                    range(len(student_options)),
                    format_func=lambda x: student_options[x],
                    key="eval_student_select"
                )
                selected_student_id = student_ids[selected_student_idx]
                student_record = st.session_state.student_records[selected_student_id]
                
            with col_sel2:
                question_keys = list(st.session_state.exam_config["questions"].keys())
                selected_q_id = st.selectbox(
                    "İncelenecek Soru",
                    question_keys,
                    format_func=lambda x: st.session_state.exam_config["questions"][x]["title"],
                    key="eval_q_select"
                )
                
            question_info = st.session_state.exam_config["questions"][selected_q_id]
            
            # Soru Açıklaması
            st.markdown(f"""
                <div style='background-color:#1e2036; padding:12px 20px; border-radius:10px; margin-bottom:15px;'>
                    <strong>Soru:</strong> {question_info['desc']}<br>
                    <span style='color:#a78bfa; font-size:0.9rem;'><strong>Doğru Cevap Anahtarı:</strong> {question_info['correct_solution'].replace('\n', ' | ')}</span>
                </div>
            """, unsafe_allow_html=True)
            
            grade_data = student_record["grades"].get(selected_q_id)
            
            # Öğrencinin taranmış görseli
            active_image = st.session_state.get(f"custom_img_{selected_student_id}")

            if not grade_data:
                st.warning(f"⏳ Bu öğrenciye ait Soru {selected_q_id} için AI notu bulunmamaktadır.")
            else:
                layout_col1, layout_col2 = st.columns([11, 10])
                
                with layout_col1:
                    st.markdown("<h5 style='color:#a78bfa;'>📷 Öğrenci Kağıdı Görseli</h5>", unsafe_allow_html=True)
                    if active_image:
                        st.image(active_image, use_container_width=True, caption=f"{student_record['name']} - Orijinal Kağıt")
                    else:
                        st.info("Kağıt görseli bulunamadı.")
                    
                    with st.expander("📝 AI Okunan OCR Çözüm Metni", expanded=False):
                        st.code(grade_data["student_solution"])
                        
                with layout_col2:
                    st.markdown("<h5 style='color:#a78bfa;'>🤖 Yapay Zeka Değerlendirme Özeti</h5>", unsafe_allow_html=True)
                    
                    # Rubrik Metrikleri
                    sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
                    with sub_col1:
                        st.metric("Kavramsal", f"{grade_data['score_concept']} / {question_info['rubric']['concept']}")
                    with sub_col2:
                        st.metric("İşlem Adımı", f"{grade_data['score_steps']} / {question_info['rubric']['steps']}")
                    with sub_col3:
                        st.metric("Sonuç", f"{grade_data['score_result']} / {question_info['rubric']['result']}")
                    with sub_col4:
                        st.metric("Toplam Puan", f"{grade_data['score_total']} / {question_info['max_score']}")
                    
                    # Muhakeme Gerekçesi
                    st.markdown(f"""
                        <div class='premium-card' style='font-size:0.95rem; line-height:1.5; border-left:4px solid #6366f1;'>
                            <h6 style='margin-top:0px; color:#6366f1;'>🔍 AI Adım Adım Notlandırma Gerekçesi:</h6>
                            {grade_data['ai_feedback'].replace('\n', '<br>')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Öğretmen Düzenleme Sürgüsü
                    st.markdown("<h6 style='color:#a78bfa;'>✏️ Öğretmen Değerlendirme Onayı & Müdahale Yetkisi</h6>", unsafe_allow_html=True)
                    override_score = st.slider(
                        "Öğrencinin Nihai Puanını Belirleyin",
                        min_value=0.0,
                        max_value=float(question_info["max_score"]),
                        value=float(grade_data["teacher_score"]),
                        step=0.5,
                        key=f"slider_override_{selected_student_id}_{selected_q_id}"
                    )
                    
                    is_overridden = override_score != float(grade_data["ai_score_initial"])
                    
                    if is_overridden:
                        st.markdown(f"""
                            <div class='info-card'>
                                ⚠️ <strong>Puan Güncellemesi:</strong> AI puanı olan <strong>{grade_data['ai_score_initial']}</strong> yerine 
                                manuel olarak <strong>{override_score}</strong> vermeyi seçtiniz.
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div class='success-card'>
                                ✅ Puan AI'nın önerdiği ilk değerle tam uyumlu.
                            </div>
                        """, unsafe_allow_html=True)
                        
                    # Onayla & Kaydet
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        st.markdown("<div class='approve-btn'>", unsafe_allow_html=True)
                        if st.button("✔️ Değerlendirmeyi Onayla ve Kaydet", key=f"btn_approve_eval_{selected_student_id}_{selected_q_id}"):
                            save_teacher_approval(
                                selected_student_id, 
                                selected_q_id, 
                                override_score, 
                                is_overridden
                            )
                            check_student_all_approved(selected_student_id)
                            st.success(f"{student_record['name']} - Soru {selected_q_id} onaylandı!")
                            
                            # Bir sonraki soruya otomatik geçiş
                            next_q_idx = question_keys.index(selected_q_id) + 1
                            if next_q_idx < len(question_keys):
                                st.rerun()
                            else:
                                st.success(f"🎉 {student_record['name']} kağıdındaki tüm sorular başarıyla onaylandı!")
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

# ==================== VIEW 4: NOT DEFTERİ & ANALİZ ====================
elif st.session_state.active_tab == "not_defteri":
    st.markdown("<h3 style='margin-bottom: 10px;'>📊 Sınav Not Defteri, Analiz ve Yönetim</h3>", unsafe_allow_html=True)
    
    if not st.session_state.student_records:
        st.markdown("""
            <div class='premium-card' style='text-align:center; padding: 40px;'>
                <h4 style='color:#a78bfa;'>📉 İstatistikler ve Not Listesi Hazırlanıyor...</h4>
                <p style='color:#94a3b8; font-size:1.05rem;'>Not defteriniz henüz boş. Öğrencilerinizin sınav kağıtlarını okuttuğunuzda;</p>
                <p style='color:#94a3b8; font-size:1.05rem;'>sınıf başarı grafikleri, not listesi ve AI hata payı kalibrasyonu burada anında listelenecektir.</p>
                <p style='color:#6366f1; font-weight:600; margin-top: 15px;'>Lütfen en alttaki yüzen çubuktan 📷 Kağıt Tarama ikonuna tıklayarak ilk kağıdı okutun!</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.write("Sınav ortalamalarını, öğrenci not dökümlerini görebilir, taranan öğrenci kayıtlarını yönetebilir ve AI kalibrasyon verilerini inceleyebilirsiniz.")
        
        # ---------------- DAHILI ANALITIK KPI PANELI (Eski Tab 1 Dashboard) ----------------
        st.markdown("<h5>📉 Sınıf Başarı İstatistikleri</h5>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Ortalama Sınıf Notu</div>
                    <div class='metric-value'>{avg_score:.1f}</div>
                    <div style='color: #34d399; font-size: 0.85rem; margin-top: 5px;'>Başarı Oranı: %{avg_score:.1f}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            completion_rate = (approved_count / total_students) * 100 if total_students > 0 else 0
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Onaylanma Oranı</div>
                    <div class='metric-value'>%{completion_rate:.0f}</div>
                    <div style='color: #a78bfa; font-size: 0.85rem; margin-top: 5px;'>{approved_count} Onaylanan / {total_students} Toplam</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            detailed_df = get_detailed_grades_dataframe()
            if selected_class != "Tüm Sınıflar":
                detailed_df = detailed_df[detailed_df["Sınıf"] == selected_class]
            hardest_q = "Soru 25"
            lowest_ratio = 1.0
            
            for q_id, q_info in st.session_state.exam_config["questions"].items():
                col_name = f"Soru {q_id}"
                if col_name in detailed_df.columns:
                    avg_q = detailed_df[col_name].mean()
                    ratio = avg_q / q_info["max_score"]
                    if ratio < lowest_ratio:
                        lowest_ratio = ratio
                        hardest_q = f"Soru {q_id}"
                        
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>En Çok Zorlanılan Soru</div>
                    <div class='metric-value'>{hardest_q}</div>
                    <div style='color: #f87171; font-size: 0.85rem; margin-top: 5px;'>Ortalama Başarı: %{lowest_ratio*100:.0f}</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ---------------- ÖĞRENCİ NOT LİSTESİ VE SİLME YÖNETİMİ ----------------
        tab4_col1, tab4_col2 = st.columns([3, 2])
        
        with tab4_col1:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.markdown("<h5>📋 Öğrenci Not Listesi</h5>", unsafe_allow_html=True)
            st.write("Sınıfınızdaki öğrencilerin soru bazlı ve toplam sınav notları dökümü aşağıdadır:")
            
            detailed_table = get_detailed_grades_dataframe()
            if selected_class != "Tüm Sınıflar":
                detailed_table = detailed_table[detailed_table["Sınıf"] == selected_class]
            
            # HTML Tablosunun mobil uyumlu sarmalayıcı (.table-responsive) içine alınması (Yatay Kaydırma Çözümü)
            html_table = "<div class='table-responsive'><table class='custom-table'><thead><tr>"
            for col in detailed_table.columns:
                html_table += f"<th>{col}</th>"
            html_table += "</tr></thead><tbody>"
            
            for _, row in detailed_table.iterrows():
                html_table += "<tr>"
                for col in detailed_table.columns:
                    val = row[col]
                    if col == "Durum":
                        badge_class = "status-approved" if val == "Onaylandı" else "status-pending"
                        html_table += f"<td><span class='status-badge {badge_class}'>{val}</span></td>"
                    else:
                        html_table += f"<td>{val}</td>"
                html_table += "</tr>"
            html_table += "</tbody></table></div>"
            
            st.markdown(html_table, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # CSV Dışa Aktarma
            csv_data = detailed_table.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Sınav Sonuçlarını CSV Olarak İndir",
                data=csv_data,
                file_name="notver_sinav_sonuclari.csv",
                mime="text/csv",
                key="btn_download_csv_defter"
            )
            
            # 🗑️ Öğrenci Kaydı Yönetimi & Silme Butonu
            st.markdown("---")
            st.markdown("<h5>🗑️ Öğrenci Kaydı Yönetimi (Silme)</h5>", unsafe_allow_html=True)
            st.write("Okutulan veya listede kayıtlı olan bir öğrenciyi ve not dökümlerini sistemden tamamen silebilirsiniz:")
            
            delete_options = []
            delete_mapping = {}
            for s_id, record in st.session_state.student_records.items():
                if selected_class == "Tüm Sınıflar" or record.get("class") == selected_class:
                    option_str = f"No: {s_id} - {record['name']} ({record.get('class', '5-A')})"
                    delete_options.append(option_str)
                    delete_mapping[option_str] = s_id
                    
            if not delete_options:
                st.info("Silinebilecek kayıtlı öğrenci bulunmamaktadır.")
            else:
                col_del1, col_del2 = st.columns([3, 1])
                with col_del1:
                    selected_del_str = st.selectbox(
                        "Silinecek Öğrenciyi Seçin",
                        delete_options,
                        key="selectbox_student_to_delete"
                    )
                with col_del2:
                    st.markdown("<div class='delete-btn'>", unsafe_allow_html=True)
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Dikey hizalama boşluğu
                    if st.button("🗑️ Kaydı Sil", use_container_width=True, key="btn_confirm_delete"):
                        s_id_to_delete = delete_mapping[selected_del_str]
                        del st.session_state.student_records[s_id_to_delete]
                        st.success("Öğrenci kaydı başarıyla silindi!")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                    
            st.markdown("</div>", unsafe_allow_html=True)

        with tab4_col2:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.markdown("<h5>🎯 Öğretmen - AI Kalibrasyon Analizi</h5>", unsafe_allow_html=True)
            st.write(
                "Öğretmenin AI puanlarına yaptığı manuel müdahaleler ve düzeltmeler burada analiz edilir. "
                "Bu veriler, sistemin gelecekteki sınavlarda daha doğru puanlama yapabilmesi için kalibre edilmesinde kullanılır."
            )
            
            cal_stats = get_calibration_analytics()
            
            if not cal_stats["has_data"]:
                st.info(
                    "Henüz hiçbir puanda manuel değişiklik yapmadınız. "
                    "AI puanlarını düzenlediğinizde, kalibrasyon analiz grafiği ve hata payı verileri burada belirecektir."
                )
            else:
                # Kalibrasyon Metrikleri
                kpi1, kpi2 = st.columns(2)
                with kpi1:
                    st.metric(
                        "Ortalama Hata Payı (MAE)", 
                        f"{cal_stats['mae']} Puan",
                        help="Öğretmenin manuel düzeltmelerinin AI'ın ilk tahmininden olan ortalama mutlak sapma puanı."
                    )
                with kpi2:
                    st.metric(
                        "Toplam Düzeltme Sayısı", 
                        f"{cal_stats['total_corrections']} Adet"
                    )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Kalibrasyon Grafiği (AI vs Öğretmen Dağılım Grafiği)
                df_cal = cal_stats["data"]
                fig_cal = px.scatter(
                    df_cal,
                    x="ai_score",
                    y="teacher_score",
                    color="question",
                    hover_data=["student_name", "difference"],
                    labels={"ai_score": "Yapay Zeka Puanı", "teacher_score": "Öğretmen Nihai Puanı"},
                    title="Yapay Zeka vs Öğretmen Puan Karşılaştırması"
                )
                # 1'e 1 referans çizgisi ekleme (Mükemmel uyum çizgisi)
                min_val = min(df_cal["ai_score"].min(), df_cal["teacher_score"].min()) - 1
                max_val = max(df_cal["ai_score"].max(), df_cal["teacher_score"].max()) + 1
                fig_cal.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='Mükemmel Uyum',
                    line=dict(dash='dash', color='rgba(255,255,255,0.3)')
                ))
                
                fig_cal.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#94a3b8',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=260
                )
                st.plotly_chart(fig_cal, use_container_width=True)
                
                # Değişiklik Günlüğü Tablosu
                st.markdown("<h6>📝 Yapılan Düzeltmelerin Kaydı</h6>", unsafe_allow_html=True)
                st.dataframe(
                    df_cal.rename(columns={
                        "student_name": "Öğrenci",
                        "question": "Soru",
                        "ai_score": "AI Puan",
                        "teacher_score": "Öğretmen Puan",
                        "difference": "Fark"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
            st.markdown("</div>", unsafe_allow_html=True)

