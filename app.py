# app.py
import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
import io

from utils import (
    initialize_session_state,
    get_approved_grades_dataframe,
    get_all_students_dataframe,
)
from gemini_integration import (
    read_answer_key,
    read_student_identity,
    evaluate_student_paper,
)

# ═══════════════════════════════════════════════════════
# 1. Sayfa Yapılandırması
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="Sınav AI Notlandırma",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════
# 2. CSS Yükleme
# ═══════════════════════════════════════════════════════
_css_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(_css_path):
    with open(_css_path, encoding="utf-8") as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 3. Session State Başlatma
# ═══════════════════════════════════════════════════════
initialize_session_state()

# ═══════════════════════════════════════════════════════
# 4. API Key Tespiti
# ═══════════════════════════════════════════════════════
api_key = ""
try:
    for _k in ("GEMINI_API_KEY", "gemini_api_key", "api_key"):
        if _k in st.secrets:
            api_key = st.secrets[_k]
            break
except Exception:
    pass
if not api_key:
    api_key = st.session_state.get("user_api_key", "")

# ═══════════════════════════════════════════════════════
# 5. Üst Başlık
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style='text-align:center; padding: 10px 0 18px 0;'>
    <h1 class='gradient-text' style='font-size:2.2rem; margin:0;'>📐 Sınav AI Notlandırma</h1>
    <p style='color:#475569; font-size:0.95rem; margin:4px 0 0 0;'>
        Cevap anahtarı yükle → Öğrenci kağıtlarını tara → Yapay zeka puanlasın
    </p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 6. Sekme Yönetimi (URL query params)
# ═══════════════════════════════════════════════════════
TABS = [
    ("cevap_anahtari",  "📐", "Cevap Anahtarı"),
    ("sinav_kagidi",    "📷", "Sınav Kağıdı"),
    ("ai_degerlendirme","🧠", "AI Değerlendirme"),
    ("not_cizelgesi",   "📋", "Not Çizelgesi"),
]

# Query param'dan sekmeyi oku (sayfa yenileme veya link paylaşımı için)
_qp = st.query_params.get("tab", "")
if _qp and _qp in [t[0] for t in TABS]:
    st.session_state.active_tab = _qp

active = st.session_state.active_tab

# ═══════════════════════════════════════════════════════
# 7. Windows 11 Dock (Saf HTML — target="_self" ile)
# ═══════════════════════════════════════════════════════
def _dock_items():
    items = ""
    for tab_id, emoji, label in TABS:
        cls = "dock-item nav-active" if active == tab_id else "dock-item"
        items += f"""
        <a href="?tab={tab_id}" class="{cls}" target="_self">
            <span class="dock-label">{label}</span>
            {emoji}
        </a>"""
    return items

st.markdown(f"""
<div class="win11-dock">
    {_dock_items()}
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════
GRADES   = ["5", "6", "7", "8"]
BRANCHES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

def _api_warning():
    """API anahtarı yoksa uyarı ve giriş kutusu göster."""
    if not api_key:
        with st.expander("🔑 Google Gemini API Anahtarı Gerekli", expanded=True):
            st.warning("Streamlit Secrets'ta API anahtarı bulunamadı. Lütfen aşağıya giriniz:")
            typed = st.text_input("API Key", type="password",
                                   value=st.session_state.get("user_api_key", ""),
                                   placeholder="AIzaSy...")
            if typed:
                st.session_state.user_api_key = typed
                st.rerun()
        return False
    return True

def _status_badge(status):
    cls_map = {
        "Onaylandı": "status-approved",
        "Değerlendirildi": "status-evaluated",
        "Bekliyor": "status-pending",
    }
    cls = cls_map.get(status, "status-pending")
    return f"<span class='status-badge {cls}'>{status}</span>"

def _pil_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 1 — CEVAP ANAHTARI                              ║
# ╚═══════════════════════════════════════════════════════╝
if active == "cevap_anahtari":
    st.markdown("## 📐 Cevap Anahtarı Yükleme")
    st.markdown("""
    <div class='callout-info'>
        Sınav kağıdının <strong>cevap anahtarını</strong> görsel olarak yükleyin.  
        Yapay zeka soruları, doğru cevapları ve puan değerlerini görselden otomatik okuyacaktır.
    </div>
    """, unsafe_allow_html=True)

    cfg = st.session_state.exam_config

    # ── Sınıf & Şube seçimi ──
    col1, col2 = st.columns(2)
    with col1:
        sel_grade = st.selectbox("Sınıf", GRADES,
                                  index=GRADES.index(cfg["grade"]) if cfg["grade"] in GRADES else 0,
                                  key="ca_grade")
    with col2:
        sel_branch = st.selectbox("Şube", BRANCHES,
                                   index=BRANCHES.index(cfg["branch"]) if cfg["branch"] in BRANCHES else 0,
                                   key="ca_branch")

    st.session_state.exam_config["grade"] = sel_grade
    st.session_state.exam_config["branch"] = sel_branch

    st.markdown("---")

    # ── Dosya Yükleme ──
    st.markdown("### 📤 Cevap Anahtarı Görselleri")
    st.write("Sınavınızın cevap anahtarını yükleyin. Birden fazla sayfa varsa hepsini seçebilirsiniz.")

    uploaded_keys = st.file_uploader(
        "Cevap anahtarı görseli (PNG, JPG) — birden fazla sayfa seçilebilir",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="uploader_answer_key"
    )

    if uploaded_keys:
        st.markdown(f"**{len(uploaded_keys)} sayfa yüklendi.** Önizleme:")
        preview_cols = st.columns(min(len(uploaded_keys), 4))
        pil_images = []
        for i, f in enumerate(uploaded_keys):
            img = Image.open(f).convert("RGB")
            pil_images.append(img)
            with preview_cols[i % 4]:
                st.image(img, use_container_width=True, caption=f"Sayfa {i+1}")

        st.markdown("---")

        col_save, col_ai = st.columns([1, 2])

        with col_save:
            if st.button("💾 Görselleri Kaydet (AI Okuma Olmadan)", use_container_width=True):
                st.session_state.exam_config["answer_key_images"] = pil_images
                st.session_state.exam_config["key_saved"] = True
                st.session_state.exam_config["questions"] = {}
                st.success("Cevap anahtarı görselleri kaydedildi. Öğrenci değerlendirmesinde AI bu görseli kullanacak.")

        with col_ai:
            if st.button("🤖 AI ile Oku ve Soru Yapısını Çıkar (Önerilen)", type="primary", use_container_width=True):
                if not _api_warning():
                    st.stop()
                with st.spinner("Gemini AI cevap anahtarını okuyup soruları çıkartıyor..."):
                    result = read_answer_key(api_key, pil_images)

                if result.get("success"):
                    st.session_state.exam_config["answer_key_images"] = pil_images
                    st.session_state.exam_config["questions"] = result.get("questions", {})
                    st.session_state.exam_config["total_max_score"] = result.get("total_max_score", 0)
                    st.session_state.exam_config["key_saved"] = True
                    st.success("✅ Cevap anahtarı başarıyla okundu!")

                    qs = result.get("questions", {})
                    if qs:
                        st.markdown("**AI'ın Tespit Ettiği Sorular:**")
                        for qid, qinfo in qs.items():
                            st.markdown(f"- **Soru {qid}:** {qinfo.get('title', '')} — **{qinfo.get('max_score', 0)} Puan**")
                        st.markdown(f"**Toplam:** {result.get('total_max_score', 0)} Puan")
                else:
                    st.error(f"Hata: {result.get('error')}")

    # ── Mevcut durumu göster ──
    if cfg.get("key_saved") and cfg.get("answer_key_images"):
        st.markdown("---")
        st.markdown(f"""
        <div class='callout-success'>
            ✅ <strong>Cevap anahtarı yüklü!</strong>
            Sınıf: <strong>{cfg['grade']}</strong> &nbsp;|&nbsp;
            Şube: <strong>{cfg['branch']}</strong> &nbsp;|&nbsp;
            {len(cfg['answer_key_images'])} sayfa &nbsp;|&nbsp;
            {len(cfg.get('questions', {}))} soru tespit edildi
        </div>
        """, unsafe_allow_html=True)

        if cfg.get("questions"):
            with st.expander("📋 Tespit Edilen Soru Yapısı (Düzenle)", expanded=False):
                qs = cfg["questions"]
                for qid in sorted(qs.keys(), key=lambda x: int(x) if x.isdigit() else x):
                    q = qs[qid]
                    with st.expander(f"Soru {qid} — {q.get('max_score', 0)} Puan", expanded=False):
                        new_max = st.number_input(f"Maksimum Puan (Soru {qid})",
                                                   min_value=1, max_value=200,
                                                   value=int(q.get("max_score", 10)),
                                                   key=f"edit_max_{qid}")
                        new_sol = st.text_area(f"Doğru Çözüm / Notlar (Soru {qid})",
                                               value=q.get("correct_solution", ""),
                                               height=80, key=f"edit_sol_{qid}")
                        if new_max != q.get("max_score") or new_sol != q.get("correct_solution"):
                            st.session_state.exam_config["questions"][qid]["max_score"] = new_max
                            st.session_state.exam_config["questions"][qid]["correct_solution"] = new_sol

        if st.button("🗑️ Cevap Anahtarını Sıfırla", key="reset_answer_key"):
            st.session_state.exam_config = {
                "grade": "", "branch": "", "answer_key_images": [],
                "questions": {}, "total_max_score": 0, "key_saved": False,
            }
            st.rerun()
    elif not uploaded_keys:
        st.markdown("""
        <div class='callout-warn'>
            ⚠️ Henüz cevap anahtarı yüklenmedi. Yukarıdan sınav cevap anahtarı görselini yükleyin.
        </div>
        """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 2 — SINAV KAĞIDI YÜKLEME                        ║
# ╚═══════════════════════════════════════════════════════╝
elif active == "sinav_kagidi":
    st.markdown("## 📷 Sınav Kağıdı Yükleme")

    cfg = st.session_state.exam_config
    if not cfg.get("key_saved"):
        st.markdown("""
        <div class='callout-warn'>
            ⚠️ Önce <strong>Cevap Anahtarı</strong> sekmesinden cevap anahtarını yüklemelisiniz!
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    st.markdown(f"""
    <div class='callout-info'>
        Aktif sınıf: <strong>{cfg['grade']}-{cfg['branch']}</strong> &nbsp;|&nbsp;
        Cevap anahtarı: <strong>{len(cfg['answer_key_images'])} sayfa</strong> hazır.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    Öğrenci sınav kağıtlarını **kameradan çekerek** veya **galeriden seçerek** yükleyin.  
    Yapay zeka kağıttaki **Ad Soyad**, **Numara** ve **Sınıf** bilgilerini otomatik okuyacaktır.
    """)

    st.markdown("---")

    # ── Yükleme yöntemi seçimi ──
    method = st.radio("Yükleme yöntemi:", ["📁 Galeriden Seç", "📷 Kameradan Çek"],
                      horizontal=True, key="upload_method")

    student_image = None
    if method == "📁 Galeriden Seç":
        uploaded = st.file_uploader(
            "Öğrenci sınav kağıdı (PNG, JPG)",
            type=["png", "jpg", "jpeg"],
            key="uploader_student_gallery"
        )
        if uploaded:
            student_image = Image.open(uploaded).convert("RGB")
    else:
        cam = st.camera_input("Kağıdı hizalayın ve çekin", key="cam_student")
        if cam:
            student_image = Image.open(cam).convert("RGB")

    if student_image:
        st.markdown("---")
        col_prev, col_action = st.columns([1, 1])
        with col_prev:
            st.markdown("**Yüklenen Görsel:**")
            st.image(student_image, use_container_width=True)

        with col_action:
            st.markdown("**İşlemler:**")
            st.info("Butona basınca AI kağıttaki öğrenci bilgilerini (ad, numara, sınıf) okuyacak ve sisteme kaydedecektir.")

            if not _api_warning():
                st.stop()

            if st.button("🤖 Yapay Zeka ile Yükle ve Tanı", type="primary", use_container_width=True):
                with st.spinner("Gemini AI öğrenci kimliğini kağıttan okuyor..."):
                    id_result = read_student_identity(api_key, student_image)

                if not id_result.get("success"):
                    st.error(f"Hata: {id_result.get('error')}")
                else:
                    name    = id_result.get("name", "Bilinmeyen Öğrenci").strip()
                    no      = id_result.get("no", "0").strip()
                    s_class = id_result.get("class", cfg["grade"]).strip()

                    # Numara çakışmasını önle
                    if not no or no == "0":
                        no = str(len(st.session_state.student_records) + 1001)

                    # Branş'ı sınıf config'den al
                    branch = cfg.get("branch", "")

                    # Kaydet
                    st.session_state.student_records[no] = {
                        "name": name,
                        "no": no,
                        "class": s_class,
                        "branch": branch,
                        "status": "Bekliyor",
                        "grades": {},
                        "total_score": 0,
                    }
                    st.session_state.student_images[no] = student_image

                    st.success(f"""
                    ✅ **Öğrenci başarıyla eklendi!**  
                    👤 Ad Soyad: **{name}**  
                    🔢 Numara: **{no}**  
                    🏫 Sınıf: **{s_class}-{branch}**
                    """)
                    st.rerun()

    # ── Yüklenen öğrenciler listesi ──
    records = st.session_state.student_records
    if records:
        st.markdown("---")
        st.markdown(f"### 📋 Sisteme Yüklenen Öğrenciler ({len(records)} kişi)")

        for no, rec in sorted(records.items(), key=lambda x: (int(x[0]) if x[0].isdigit() else x[0])):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"{_status_badge(rec['status'])} &nbsp; "
                    f"**{rec.get('name', '—')}** &nbsp;|&nbsp; No: `{no}` &nbsp;|&nbsp; "
                    f"{rec.get('class', '')}–{rec.get('branch', '')}",
                    unsafe_allow_html=True
                )
            with col_del:
                st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{no}", help=f"{rec.get('name')} sil"):
                    del st.session_state.student_records[no]
                    st.session_state.student_images.pop(no, None)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='callout-info' style='margin-top:20px;'>
            Henüz hiç öğrenci eklenmedi. Yukarıdan öğrenci kağıtlarını yükleyin.
        </div>
        """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 3 — AI DEĞERLENDİRME                            ║
# ╚═══════════════════════════════════════════════════════╝
elif active == "ai_degerlendirme":
    st.markdown("## 🧠 Yapay Zeka Değerlendirme")

    cfg     = st.session_state.exam_config
    records = st.session_state.student_records

    if not cfg.get("key_saved"):
        st.markdown("<div class='callout-warn'>⚠️ Önce Cevap Anahtarı sekmesinden cevap anahtarı yükleyin!</div>", unsafe_allow_html=True)
        st.stop()

    if not records:
        st.markdown("<div class='callout-warn'>⚠️ Sisteme henüz öğrenci eklenmedi. Sınav Kağıdı sekmesinden öğrencileri ekleyin!</div>", unsafe_allow_html=True)
        st.stop()

    if not _api_warning():
        st.stop()

    # ── Tümünü Değerlendir butonu ──
    bekleyen = [no for no, r in records.items() if r["status"] == "Bekliyor"]
    if bekleyen:
        st.markdown(f"**{len(bekleyen)} öğrenci** değerlendirilmeyi bekliyor.")
        if st.button(f"🤖 Tüm Bekleyen Öğrencileri Değerlendir ({len(bekleyen)} kişi)",
                     type="primary", use_container_width=True):
            progress = st.progress(0, text="Değerlendirme başlıyor...")
            for i, no in enumerate(bekleyen):
                rec = records[no]
                img = st.session_state.student_images.get(no)
                if img is None:
                    continue
                progress.progress((i + 1) / len(bekleyen),
                                   text=f"Değerlendiriliyor: {rec['name']} ({i+1}/{len(bekleyen)})")

                result = evaluate_student_paper(
                    api_key,
                    cfg["answer_key_images"],
                    img,
                    cfg.get("questions", {})
                )

                if result.get("success"):
                    grades_raw = result.get("grades", {})
                    total = result.get("total_score", sum(g.get("score", 0) for g in grades_raw.values()))
                    st.session_state.student_records[no]["grades"] = grades_raw
                    st.session_state.student_records[no]["total_score"] = total
                    st.session_state.student_records[no]["status"] = "Değerlendirildi"

            progress.empty()
            st.success("✅ Tüm öğrenciler değerlendirildi! Şimdi tek tek inceleyip onaylayabilirsiniz.")
            st.rerun()

    st.markdown("---")

    # ── Öğrenci listesi + Detay paneli ──
    sorted_nos = sorted(records.keys(),
                        key=lambda x: (int(x) if x.isdigit() else x))

    # Aktif öğrenci session state
    if "selected_student_no" not in st.session_state:
        st.session_state.selected_student_no = sorted_nos[0] if sorted_nos else None

    col_list, col_detail = st.columns([1, 2])

    # Sol: Öğrenci listesi
    with col_list:
        st.markdown("**Öğrenci Listesi**")
        for no in sorted_nos:
            rec = records[no]
            is_active = (no == st.session_state.selected_student_no)
            card_cls = "student-card active" if is_active else "student-card"

            # HTML kart ama tıklama için buton
            if st.button(
                f"{rec.get('name', '—')} | No: {no}\n{rec['status']}",
                key=f"sel_{no}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.selected_student_no = no
                st.rerun()

    # Sağ: Detay paneli
    with col_detail:
        sel_no = st.session_state.selected_student_no
        if sel_no and sel_no in records:
            rec = records[sel_no]
            img = st.session_state.student_images.get(sel_no)

            st.markdown(f"### 👤 {rec.get('name', '—')}")
            st.markdown(
                f"No: **{sel_no}** &nbsp;|&nbsp; "
                f"Sınıf: **{rec.get('class', '')}–{rec.get('branch', '')}** &nbsp;|&nbsp; "
                f"{_status_badge(rec['status'])}",
                unsafe_allow_html=True
            )

            # Değerlendir butonu (tek öğrenci)
            if rec["status"] == "Bekliyor":
                if img and st.button("🤖 Bu Öğrenciyi Değerlendir", use_container_width=True):
                    with st.spinner(f"{rec['name']} değerlendiriliyor..."):
                        result = evaluate_student_paper(
                            api_key,
                            cfg["answer_key_images"],
                            img,
                            cfg.get("questions", {})
                        )
                    if result.get("success"):
                        grades_raw = result.get("grades", {})
                        total = result.get("total_score", sum(g.get("score", 0) for g in grades_raw.values()))
                        st.session_state.student_records[sel_no]["grades"] = grades_raw
                        st.session_state.student_records[sel_no]["total_score"] = total
                        st.session_state.student_records[sel_no]["status"] = "Değerlendirildi"
                        st.success("✅ Değerlendirme tamamlandı!")
                        st.rerun()
                    else:
                        st.error(f"Hata: {result.get('error')}")
                elif not img:
                    st.warning("Bu öğrenciye ait görsel bulunamadı.")

            # Kağıt görseli
            if img:
                with st.expander("📄 Öğrenci Kağıdı Görseli", expanded=False):
                    st.image(img, use_container_width=True)

            # Puan tablosu
            grades = rec.get("grades", {})
            if grades:
                st.markdown("#### 📊 Soru Bazlı Puanlar")

                total_score = 0
                total_max   = 0

                for qid in sorted(grades.keys(), key=lambda x: int(x) if x.isdigit() else x):
                    g = grades[qid]
                    score     = g.get("score", 0)
                    max_score = g.get("max_score", cfg.get("questions", {}).get(qid, {}).get("max_score", "?"))
                    feedback  = g.get("feedback", "")
                    st_ans    = g.get("student_answer", "")

                    total_score += score
                    if isinstance(max_score, (int, float)):
                        total_max += max_score

                    pct = int(score / max_score * 100) if isinstance(max_score, (int, float)) and max_score > 0 else 0
                    color = "#34d399" if pct >= 75 else ("#fbbf24" if pct >= 40 else "#f87171")

                    st.markdown(f"""
                    <div class='premium-card' style='margin-bottom:10px; padding:14px 18px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <span style='font-weight:700; color:#e8eaf6;'>Soru {qid}</span>
                            <span style='font-size:1.4rem; font-weight:800; color:{color};'>{score} / {max_score}</span>
                        </div>
                        {"<div style='color:#94a3b8; font-size:0.82rem; margin-top:4px;'>📝 Öğrenci: " + st_ans + "</div>" if st_ans else ""}
                        {"<div style='color:#64748b; font-size:0.82rem; margin-top:4px;'>🤖 " + feedback + "</div>" if feedback else ""}
                    </div>
                    """, unsafe_allow_html=True)

                # Toplam
                t_color = "#34d399" if (total_max > 0 and total_score / total_max >= 0.5) else "#f87171"
                st.markdown(f"""
                <div style='background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3);
                            border-radius:12px; padding:14px 20px; text-align:center; margin-top:10px;'>
                    <span style='color:#94a3b8; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.06em;'>TOPLAM PUAN</span><br>
                    <span style='font-size:2.5rem; font-weight:800; color:{t_color};'>{total_score}</span>
                    <span style='font-size:1.1rem; color:#64748b;'> / {total_max}</span>
                </div>
                """, unsafe_allow_html=True)

                # Öğretmen onayı
                if rec["status"] == "Değerlendirildi":
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="approve-btn">', unsafe_allow_html=True)
                    if st.button("✅ Değerlendirmeyi Onayla ve Kaydet",
                                 key=f"approve_{sel_no}", use_container_width=True):
                        st.session_state.student_records[sel_no]["status"] = "Onaylandı"
                        st.session_state.student_records[sel_no]["total_score"] = total_score
                        st.success(f"✅ {rec['name']} onaylandı! Toplam: {total_score}/{total_max}")
                        # Bir sonraki öğrenciye geç
                        idx = sorted_nos.index(sel_no)
                        if idx + 1 < len(sorted_nos):
                            st.session_state.selected_student_no = sorted_nos[idx + 1]
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                elif rec["status"] == "Onaylandı":
                    st.markdown("""
                    <div class='callout-success'>
                        ✅ Bu öğrencinin değerlendirmesi onaylandı ve not çizelgesine eklendi.
                    </div>
                    """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 4 — NOT ÇİZELGESİ                               ║
# ╚═══════════════════════════════════════════════════════╝
elif active == "not_cizelgesi":
    st.markdown("## 📋 Not Çizelgesi")

    records = st.session_state.student_records
    onaylanan = {no: r for no, r in records.items() if r.get("status") == "Onaylandı"}

    if not onaylanan:
        st.markdown("""
        <div class='callout-info'>
            📭 Henüz onaylanmış öğrenci kaydı bulunmamaktadır.<br>
            AI Değerlendirme sekmesinden öğrencileri değerlendirip onaylayın.
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    st.markdown(f"""
    <div class='callout-success'>
        ✅ <strong>{len(onaylanan)} öğrenci</strong> onaylandı. Numara sırasına göre listelenmiştir.
    </div>
    """, unsafe_allow_html=True)

    df = get_approved_grades_dataframe()

    if not df.empty:
        # ── Özet istatistikler ──
        questions = st.session_state.exam_config.get("questions", {})
        total_max = sum(q.get("max_score", 0) for q in questions.values()) if questions else 0
        avg = df["Toplam"].mean() if "Toplam" in df.columns else 0

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>Toplam Öğrenci</div>
                <div class='metric-value'>{len(df)}</div>
            </div>""", unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>Sınıf Ortalaması</div>
                <div class='metric-value'>{avg:.1f}</div>
            </div>""", unsafe_allow_html=True)
        with kpi3:
            pct = (avg / total_max * 100) if total_max > 0 else 0
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>Ortalama Başarı %</div>
                <div class='metric-value'>%{pct:.0f}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── HTML Tablosu (yatay kaydırmalı, mobil uyumlu) ──
        html_table = "<div class='table-responsive'><table class='custom-table'><thead><tr>"
        for col in df.columns:
            html_table += f"<th>{col}</th>"
        html_table += "</tr></thead><tbody>"

        for _, row in df.iterrows():
            html_table += "<tr>"
            for col in df.columns:
                val = row[col]
                if col == "Toplam":
                    pct_s = (val / total_max * 100) if total_max > 0 else 0
                    color = "#34d399" if pct_s >= 50 else "#f87171"
                    html_table += f"<td style='font-weight:700; color:{color};'>{val}</td>"
                else:
                    html_table += f"<td>{val}</td>"
            html_table += "</tr>"

        html_table += "</tbody></table></div>"
        st.markdown(html_table, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── CSV İndir ──
        csv = df.to_csv(index=False).encode("utf-8")
        cfg = st.session_state.exam_config
        st.download_button(
            label="📥 Not Çizelgesini CSV Olarak İndir",
            data=csv,
            file_name=f"notlar_{cfg.get('grade', '')}_{cfg.get('branch', '')}.csv",
            mime="text/csv",
            use_container_width=True
        )
