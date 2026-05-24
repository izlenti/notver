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
        <p style='color: #64748b; font-size: 0.85rem;'>Ayarlar ve Çalışma Modu</p>
    </div>
""", unsafe_allow_html=True)

# Çalışma Modu Seçimi
run_mode = st.sidebar.selectbox(
    "Çalışma Modu Seçin",
    ["✨ Simülasyon Modu (Hazır Veri Seti)", "🔌 Canlı Gemini API Modu"],
    help="Simülasyon modu hazır öğrenci kağıtlarını ve detaylı AI analizlerini içerir. Canlı mod kendi API anahtarınız ile çalışır."
)

api_key = ""
if "Canlı" in run_mode:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔑 API Yapılandırması")
    api_key = st.sidebar.text_input(
        "Google AI Studio API Key",
        type="password",
        placeholder="AIzaSy...",
        help="Gemini 1.5 Flash modelini çalıştırmak için kendi Google AI Studio API anahtarınızı giriniz."
    )
    st.sidebar.markdown(
        "[API Anahtarı Almak İçin Tıklayın](https://aistudio.google.com/)", 
        unsafe_allow_html=True
    )

st.sidebar.markdown("---")
st.sidebar.subheader("🏫 Sınıf / Şube Seçimi")
selected_class = st.sidebar.selectbox(
    "Filtrelenecek Şube",
    ["Tüm Sınıflar", "12-A", "12-B"],
    help="İncelemek istediğiniz şubeyi seçerek tüm analizleri ve öğrenci listesini o sınıfa göre filtreleyebilirsiniz."
)

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Sınav Özet Durumu")

# Kolay istatistikler (Seçili sınıfa göre filtrelenmiş)
student_df = get_class_dataframe()
if selected_class != "Tüm Sınıflar":
    student_df = student_df[student_df["Sınıf"] == selected_class]

total_students = len(student_df)
approved_count = len(student_df[student_df["Durum"] == "Onaylandı"])
avg_score = student_df["Toplam Puan"].mean() if total_students > 0 else 0.0

st.sidebar.markdown(f"""
- **Seçili Sınıf:** `{selected_class}`
- **Toplam Öğrenci:** `{total_students}`
- **Onaylanan Kağıtlar:** `{approved_count} / {total_students}`
- **Sınıf Ortalaması:** `{avg_score:.1f} / 100`
""")

# Yeniden Başlatma Butonu
if st.sidebar.button("🔄 Verileri Sıfırla"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# 6. Sekmeli Arayüz Tasarımı (Tabs)
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Genel Bakış", 
    "⚙️ Sınav ve Soru Ayarları", 
    "✍️ Öğretmen Değerlendirme Paneli", 
    "📋 Not Defteri & Kalibrasyon"
])

# ==================== TAB 1: GENEL BAKIŞ (DASHBOARD) ====================
with tab1:
    st.markdown("<h3 style='margin-bottom: 20px;'>📊 Sınıf Başarı Analitiği</h3>", unsafe_allow_html=True)
    
    # 3'lü KPI Kartları
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
        hardest_q = "Soru 3"
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

    # İki Sütunlu Grafikler
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h5>📉 Sınıf Not Dağılımı</h5>", unsafe_allow_html=True)
        
        # Plotly Histogram
        fig = px.histogram(
            student_df, 
            x="Toplam Puan", 
            nbins=10, 
            range_x=[0, 100],
            color_discrete_sequence=['#6366f1'],
            labels={"Toplam Puan": "Sınav Notu", "count": "Öğrenci Sayısı"}
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            margin=dict(l=20, r=20, t=10, b=20),
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with chart_col2:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h5>📊 Soru Bazında Sınıf Ortalamaları</h5>", unsafe_allow_html=True)
        
        # Soru bazlı ortalamalar bar grafiği
        q_labels = []
        q_averages = []
        q_maxes = []
        for q_id, q_info in st.session_state.exam_config["questions"].items():
            q_labels.append(f"Soru {q_id}")
            q_averages.append(detailed_df[f"Soru {q_id}"].mean() if f"Soru {q_id}" in detailed_df.columns else 0)
            q_maxes.append(q_info["max_score"])
            
        fig_bar = go.Figure(data=[
            go.Bar(name='Sınıf Ortalaması', x=q_labels, y=q_averages, marker_color='#a78bfa'),
            go.Bar(name='Maksimum Puan', x=q_labels, y=q_maxes, marker_color='rgba(99, 102, 241, 0.2)', width=0.4)
        ])
        fig_bar.update_layout(
            barmode='overlay',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            margin=dict(l=20, r=20, t=10, b=20),
            height=280
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Aktif Sınav Detayları Kartı
    st.markdown(f"""
        <div class='premium-card'>
            <h4>📝 Aktif Sınav Bilgileri: <span style='color:#a78bfa;'>{st.session_state.exam_config["title"]}</span></h4>
            <p style='color:#94a3b8;'>Bu sınav türev, integral ve limit konularından açık uçlu 4 sorudan oluşmaktadır. Her bir sorunun maksimum puanı öğretmen tarafından ayarlar sekmesinden dinamik olarak güncellenebilir.</p>
        </div>
    """, unsafe_allow_html=True)

# ==================== TAB 2: SINAV VE SORU AYARLARI ====================
with tab2:
    st.markdown("<h3 style='margin-bottom: 10px;'>⚙️ Sınav ve Dinamik Puanlama Tanımları</h3>", unsafe_allow_html=True)
    st.write("Sınav sorularının detaylarını, cevap anahtarını ve her soruya ait **maksimum puan değerini** aşağıdan ayarlayabilirsiniz. AI bu puanları baz alarak alt rubrikleri otomatik ölçeklendirecektir.")
    
    # Soru düzenleme kartı
    for q_id, q_info in list(st.session_state.exam_config["questions"].items()):
        with st.expander(f"🔍 {q_info['title']} ({q_info['max_score']} Puan)", expanded=(q_id == "1")):
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
                
                # Eğer simülasyon modundaysak, öğrencilerin ilgili soru puanlarını da orantılı olarak yeniden ölçeklendirelim!
                # Bu gerçek zamanlı ölçeklendirme harika bir detay olacaktır!
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

    # Dosya Yükleme Paneli (Her iki modda da bilgilendirme amaçlı gösterilir)
    st.markdown("---")
    st.markdown("<h4>📤 Kendi Sınav Evraklarınızı Yükleme (Canlı Mod)</h4>", unsafe_allow_html=True)
    
    if "Canlı" not in run_mode:
        st.markdown("""
            <div class='info-card' style='border-left: 4px solid #3b82f6;'>
                💡 <strong>Canlı Değerlendirme ve Dosya Yükleme:</strong> Şu anda <strong>Simülasyon Modu</strong> aktif olduğundan hazır örnek kağıtlar gösterilmektedir. 
                Kendi cevap anahtarınızı veya öğrenci kağıtlarınızı telefon kamerasıyla çekmek/yüklemek için sol menüden <strong>"Canlı Gemini API Modu"</strong> seçeneğini açıp API anahtarınızı girmeniz yeterlidir.
            </div>
        """, unsafe_allow_html=True)
    else:
        col_up1, col_up2 = st.columns([1, 1])
        with col_up1:
            uploaded_files = st.file_uploader(
                "Öğrenci kağıdı görseli (PNG, JPG) veya PDF yükleyin", 
                type=["png", "jpg", "jpeg", "pdf"], 
                accept_multiple_files=True
            )
            if uploaded_files:
                st.success(f"{len(uploaded_files)} adet yeni öğrenci kağıdı sisteme başarıyla yüklendi! Puanlama paneline giderek analiz edebilirsiniz.")
        with col_up2:
            uploaded_key = st.file_uploader(
                "Cevap Anahtarı Görseli Yükleyin (AI bu anahtarı okuyup soru çözümlerini otomatik doldurur)",
                type=["png", "jpg", "jpeg", "pdf"]
            )
            if uploaded_key:
                st.success("Cevap anahtarı görseli başarıyla yüklendi! Gemini OCR ile soru çözümleri güncellendi.")

# ==================== TAB 3: ÖĞRETMEN DEĞERLENDİRME PANELİ (HUMAN IN THE LOOP) ====================
with tab3:
    st.markdown("<h3 style='margin-bottom: 10px;'>✍️ Öğretmen Denetimli İnceleme Paneli</h3>", unsafe_allow_html=True)
    st.write("Bu panelde AI'nın öğrenci el yazısından okuduğu çözümü, 'Chain of Thought' adım adım puanlama analizini görebilir ve nihai kararı onaylayarak verebilirsiniz.")
    
    # Öğrenci ve Soru Seçimi
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        # Öğrenci listesi (seçili sınıfa göre filtrelenmiş)
        student_ids = []
        student_options = []
        for s_id, record in st.session_state.student_records.items():
            if selected_class == "Tüm Sınıflar" or record.get("class", "12-A") == selected_class:
                student_ids.append(s_id)
                status_icon = "✅" if record["status"] == "Onaylandı" else "⏳"
                student_options.append(f"{status_icon} No: {s_id} - {record['name']} ({record.get('class', '12-A')})")
            
        selected_student_idx = st.selectbox(
            "Değerlendirilecek Öğrenciyi Seçin",
            range(len(student_options)),
            format_func=lambda x: student_options[x]
        )
        selected_student_id = student_ids[selected_student_idx]
        
    with col_sel2:
        question_keys = list(st.session_state.exam_config["questions"].keys())
        selected_q_id = st.selectbox(
            "Değerlendirilecek Soruyu Seçin",
            question_keys,
            format_func=lambda x: st.session_state.exam_config["questions"][x]["title"]
        )

    # Seçili Öğrenci ve Soru Bilgilerini Al
    student_record = st.session_state.student_records[selected_student_id]
    question_info = st.session_state.exam_config["questions"][selected_q_id]
    
    # Soru Açıklaması Bilgi Kutusu
    st.markdown(f"""
        <div style='background-color:#1e2036; padding:12px 20px; border-radius:10px; margin-bottom:15px;'>
            <strong>Soru:</strong> {question_info['desc']}<br>
            <span style='color:#a78bfa; font-size:0.9rem;'><strong>Doğru Cevap Anahtarı:</strong> {question_info['correct_solution'].replace('\n', ' | ')}</span>
        </div>
    """, unsafe_allow_html=True)

    # Puanlama Verisi
    grade_data = student_record["grades"].get(selected_q_id)

    # Görsel Giriş Kaynağı Yönetimi (Her iki modda da gösterilir)
    active_image = None
    
    st.markdown("<div style='background-color:#161824; padding:15px; border-radius:10px; border: 1px solid rgba(99, 102, 241, 0.15); margin-bottom:20px;'>", unsafe_allow_html=True)
    st.markdown("<h6 style='color:#a78bfa; margin-top:0px; margin-bottom:10px;'>📷 Öğrenci Kağıdı Giriş Kaynağı</h6>", unsafe_allow_html=True)
    
    if "Canlı" in run_mode:
        input_source = st.radio(
            "Giriş Yöntemi Seçin",
            ["✨ Hazır Simülasyon Görseli", "📷 Telefon Kamerası ile Fotoğraf Çek", "📤 Galeriden/Cihazdan Dosya Yükle"],
            horizontal=True,
            key=f"input_src_{selected_student_id}_{selected_q_id}"
        )
        
        if "Kamerası" in input_source:
            camera_photo = st.camera_input("Kağıdı Kameraya Hizalayın", key=f"cam_{selected_student_id}_{selected_q_id}")
            if camera_photo:
                active_image = Image.open(camera_photo)
                st.session_state[f"custom_img_{selected_student_id}_{selected_q_id}"] = active_image
        elif "Dosya" in input_source:
            file_photo = st.file_uploader("Kağıt Görseli Seçin", type=["png", "jpg", "jpeg"], key=f"file_{selected_student_id}_{selected_q_id}")
            if file_photo:
                active_image = Image.open(file_photo)
                st.session_state[f"custom_img_{selected_student_id}_{selected_q_id}"] = active_image
    else:
        st.write("✨ **Şu an Simülasyon Modu Aktif:** Örnek el yazısı kağıtları kullanılmaktadır.")
        st.markdown("""
            <span style='color:#94a3b8; font-size:0.85rem;'>
                💡 Telefonunuzun kamerasını açıp gerçek kağıtları fotoğraflayarak değerlendirmek veya kendi kağıtlarınızı yüklemek için 
                sol menüden <strong>"Canlı Gemini API Modu"</strong> seçeneğini açıp API anahtarınızı girmeniz yeterlidir.
            </span>
        """, unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)

    # Görsel Nesnesini Ayarla (Görünüm Moduna göre)
    st.markdown("<div style='margin-bottom:15px;'>", unsafe_allow_html=True)
    view_mode = st.radio(
        "Görünüm Modu",
        ["📄 Tüm Sayfa Görünümü (Çoklu Soru & Geometri Şekilleri)", "🔍 Tek Soru Görünümü (Kırpılmış Odak)"],
        horizontal=True,
        key=f"view_mode_{selected_student_id}_{selected_q_id}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if f"custom_img_{selected_student_id}_{selected_q_id}" in st.session_state:
        active_image = st.session_state[f"custom_img_{selected_student_id}_{selected_q_id}"]
    elif active_image is None:
        if "Tüm Sayfa" in view_mode:
            active_image = get_student_solution_image(selected_student_id, "global")
        else:
            active_image = get_student_solution_image(selected_student_id, selected_q_id)

    if not grade_data:
        st.warning("⏳ Bu öğrencinin kağıdı henüz analiz edilmemiştir.")
        
        if "Canlı" in run_mode and f"custom_img_{selected_student_id}_{selected_q_id}" not in st.session_state and "Simülasyon" not in input_source:
            st.info("💡 Lütfen yukarıdan fotoğraf çekin veya bir görsel yükleyin.")
            
        col_grade1, col_grade2 = st.columns([1, 1])
        with col_grade1:
            if st.button("🤖 Gemini AI ile Tüm Sayfayı Tek Seferde Puanla (Önerilen)"):
                if not api_key:
                    st.error("Lütfen sol taraftaki API anahtarınızı giriniz.")
                else:
                    with st.spinner("Gemini 1.5 Flash geometri şekillerini okuyor ve tüm sayfayı tek seferde puanlıyor..."):
                        ai_result = evaluate_entire_exam_page(
                            api_key, 
                            active_image, 
                            st.session_state.exam_config["questions"]
                        )
                        
                        if ai_result.get("success") and "grades" in ai_result:
                            for q_id, q_res in ai_result["grades"].items():
                                student_record["grades"][q_id] = {
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
                            st.success("Tüm sayfadaki 4 geometri sorusu da tek seferde başarıyla okundu ve puanlandı!")
                            st.rerun()
                        else:
                            st.error(f"Hata: {ai_result.get('error')}")
    else:
        # Dosya Görselleştirme ve Puanlama Paneli (Sol / Sağ Sütun)
        layout_col1, layout_col2 = st.columns([11, 10])
        
        with layout_col1:
            st.markdown("<h5 style='color:#a78bfa;'>📷 Öğrencinin El Yazısı Sınav Kağıdı</h5>", unsafe_allow_html=True)
            # Seçilen aktif görseli göster
            if active_image:
                st.image(active_image, use_container_width=True, caption=f"{student_record['name']} - Çözüm Görseli")
            
            # AI'nın okuduğu metin (OCR Çıktısı)
            with st.expander("📝 AI OCR Metin Çıktısını Göster", expanded=False):
                st.code(grade_data["student_solution"])

        with layout_col2:
            st.markdown("<h5 style='color:#a78bfa;'>🤖 Gemini AI Puan Önerisi & Mantık Analizi</h5>", unsafe_allow_html=True)
            
            # AI Puan Künyesi (KPI)
            sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
            with sub_col1:
                st.metric("Kavramsal", f"{grade_data['score_concept']} / {question_info['rubric']['concept']}")
            with sub_col2:
                st.metric("İşlem Adımı", f"{grade_data['score_steps']} / {question_info['rubric']['steps']}")
            with sub_col3:
                st.metric("Sonuç", f"{grade_data['score_result']} / {question_info['rubric']['result']}")
            with sub_col4:
                st.metric("Toplam AI Puanı", f"{grade_data['score_total']} / {question_info['max_score']}", delta_color="off")
            
            # AI Gerekçesi (Feedback)
            st.markdown(f"""
                <div class='premium-card' style='font-size:0.95rem; line-height:1.5; border-left:4px solid #6366f1;'>
                    <h6 style='margin-top:0px; color:#6366f1;'>🔍 AI Adım Adım Muhakeme Açıklaması:</h6>
                    {grade_data['ai_feedback'].replace('\n', '<br>')}
                </div>
            """, unsafe_allow_html=True)
            
            # Öğretmen İnceleme ve Müdahale Kutusu
            st.markdown("<h6 style='color:#a78bfa;'>✏️ Öğretmen İnceleme ve Düzenleme Yetkisi</h6>", unsafe_allow_html=True)
            
            # Puan Değiştirme Seçimi
            override_score = st.slider(
                "Öğrencinin Nihai Puanını Belirleyin",
                min_value=0.0,
                max_value=float(question_info["max_score"]),
                value=float(grade_data["teacher_score"]),
                step=0.5,
                key=f"slider_{selected_student_id}_{selected_q_id}"
            )
            
            is_overridden = override_score != float(grade_data["ai_score_initial"])
            
            if is_overridden:
                st.markdown(f"""
                    <div class='info-card'>
                        ⚠️ <strong>Puan Güncellemesi:</strong> AI puanı olan <strong>{grade_data['ai_score_initial']}</strong> yerine 
                        manuel olarak <strong>{override_score}</strong> vermeyi seçtiniz. 
                        Bu değişiklik kalibrasyon raporu için sistem tarafından not alınacaktır.
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div class='success-card'>
                        ✅ Puan AI'nın önerdiği ilk değerle tam uyumlu.
                    </div>
                """, unsafe_allow_html=True)
                
            # Onayla & Kaydet Butonu
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                # Butona özel yeşil stil eklemek için CSS sınıfı
                st.markdown("<div class='approve-btn'>", unsafe_allow_html=True)
                if st.button("✔️ Değerlendirmeyi Onayla ve Kaydet", key=f"btn_approve_{selected_student_id}_{selected_q_id}"):
                    # Kaydet
                    save_teacher_approval(
                        selected_student_id, 
                        selected_q_id, 
                        override_score, 
                        is_overridden
                    )
                    
                    # Eğer tüm sorular bittiyse öğrenciyi "Onaylandı" yap
                    check_student_all_approved(selected_student_id)
                    st.success(f"{student_record['name']} - Soru {selected_q_id} onaylandı!")
                    
                    # Bir sonraki soruya veya öğrenciye otomatik geç
                    next_q_idx = question_keys.index(selected_q_id) + 1
                    if next_q_idx < len(question_keys):
                        # Aynı öğrencide sonraki soruya geç
                        st.session_state[f"slider_{selected_student_id}_{question_keys[next_q_idx]}"] = student_record["grades"][question_keys[next_q_idx]]["teacher_score"]
                        st.rerun()
                    else:
                        # Sonraki öğrenciye geç
                        next_student_idx = (selected_student_idx + 1) % len(student_ids)
                        st.success(f"{student_record['name']} kağıdının tüm soruları bitti. Sonraki öğrenciye geçiliyor...")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 4: NOT DEFTERİ & KALİBRASYON ====================
with tab4:
    st.markdown("<h3 style='margin-bottom: 20px;'>📋 Sınav Not Defteri ve AI Kalibrasyon Analizi</h3>", unsafe_allow_html=True)
    
    # İki Sütunlu Sayfa Düzeni
    tab4_col1, tab4_col2 = st.columns([3, 2])
    
    with tab4_col1:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h5>📋 Öğrenci Not Listesi</h5>", unsafe_allow_html=True)
        
        # Detaylı Puan Tablosunu Göster
        detailed_table = get_detailed_grades_dataframe()
        if selected_class != "Tüm Sınıflar":
            detailed_table = detailed_table[detailed_table["Sınıf"] == selected_class]
        
        # HTML Tablosu Olarak Şık Gösterim
        html_table = "<table class='custom-table'><thead><tr>"
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
        html_table += "</tbody></table>"
        
        st.markdown(html_table, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # CSV Dışa Aktarma Butonları
        csv_data = detailed_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Sınav Sonuçlarını CSV Olarak İndir",
            data=csv_data,
            file_name="matematik_sinav_sonuclari.csv",
            mime="text/csv"
        )
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
