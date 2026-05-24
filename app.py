# app.py
import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
import io

# PDF desteği (PyMuPDF)
try:
    import fitz  # PyMuPDF
    PDF_SUPPORTED = True
except ImportError:
    PDF_SUPPORTED = False

from utils import (
    initialize_session_state,
    get_approved_grades_dataframe,
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
_css_path = "styles.css"
if os.path.exists(_css_path):
    with open(_css_path, encoding="utf-8") as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 3. Session State & API Key
# ═══════════════════════════════════════════════════════
initialize_session_state()

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
# 4. Üst Başlık
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style='text-align:center; padding: 8px 0 14px 0;'>
    <h1 class='gradient-text' style='font-size:2rem; margin:0; line-height:1.2;'>📐 Sınav AI Notlandırma</h1>
    <p style='color:#475569; font-size:0.88rem; margin:4px 0 0 0;'>
        Cevap anahtarı yükle → Öğrenci kağıtlarını tara → Yapay zeka puanlasın
    </p>
</div>
""", unsafe_allow_html=True)

# ─── PDF sayfalarını PIL Image listesine çevir ───
def _pdf_to_images(file_bytes: bytes) -> list:
    """PDF dosyasının her sayfasını yüksek çözünürlüklü PIL Image'a çevirir."""
    if not PDF_SUPPORTED:
        st.error("⚠️ PDF desteği yüklü değil. Lütfen PNG/JPG kullanın.")
        return []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat  = fitz.Matrix(2.0, 2.0)  # 2× zoom → daha net AI okuması
        pix  = page.get_pixmap(matrix=mat)
        img  = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        images.append(img)
    doc.close()
    return images

def _load_uploaded_files(files) -> list:
    """
    Dosya listesini (görsel veya PDF) PIL Image listesine çevirir.
    Her PDF dosyası sayfa sayfa açılır.
    """
    images = []
    for f in files:
        name = f.name.lower()
        if name.endswith(".pdf"):
            pages = _pdf_to_images(f.read())
            images.extend(pages)
        else:
            images.append(Image.open(f).convert("RGB"))
    return images

# ─── API Key uyarısı (Secrets'ta yoksa) ───
def _api_warning():
    if not api_key:
        with st.expander("🔑 Google Gemini API Anahtarı Gerekli", expanded=True):
            st.warning("Streamlit Secrets'ta API anahtarı bulunamadı.")
            typed = st.text_input("API Key", type="password",
                                   value=st.session_state.get("user_api_key",""),
                                   placeholder="AIzaSy...")
            if typed:
                st.session_state.user_api_key = typed
                st.rerun()
        return False
    return True

# ─── Status badge ───
def _badge(status):
    cls = {"Onaylandı": "status-approved",
           "Değerlendirildi": "status-evaluated",
           "Bekliyor": "status-pending"}.get(status, "status-pending")
    return f"<span class='status-badge {cls}'>{status}</span>"

GRADES   = ["5", "6", "7", "8"]
BRANCHES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

# ═══════════════════════════════════════════════════════
# 5. Native st.tabs() — CSS ile altta görev çubuğuna dönüştürülecek
# ═══════════════════════════════════════════════════════
tab_ca, tab_sk, tab_ai, tab_nc = st.tabs([
    "📐  Cevap Anahtarı",
    "📷  Sınav Kağıdı",
    "🧠  AI Değerlendirme",
    "📋  Not Çizelgesi",
])

# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 1 — CEVAP ANAHTARI                              ║
# ╚═══════════════════════════════════════════════════════╝
with tab_ca:
    st.markdown("### 📐 Cevap Anahtarı Yükleme")

    cfg = st.session_state.exam_config

    st.markdown("""
    <div class='callout-info'>
        Sınav kağıdının <strong>cevap anahtarını</strong> görsel olarak yükleyin.
        Yapay zeka soruları, doğru cevapları ve puan değerlerini görselden otomatik okur.
    </div>
    """, unsafe_allow_html=True)

    # ── Sınıf & Şube seçimi ──
    col1, col2 = st.columns(2)
    with col1:
        idx_g = GRADES.index(cfg["grade"]) if cfg["grade"] in GRADES else 0
        sel_grade = st.selectbox("Sınıf", GRADES, index=idx_g, key="ca_grade")
    with col2:
        idx_b = BRANCHES.index(cfg["branch"]) if cfg["branch"] in BRANCHES else 0
        sel_branch = st.selectbox("Şube", BRANCHES, index=idx_b, key="ca_branch")

    st.session_state.exam_config["grade"] = sel_grade
    st.session_state.exam_config["branch"] = sel_branch

    st.markdown("---")

    # ── Dosya yükleme ──
    accept_types = ["png","jpg","jpeg","pdf"] if PDF_SUPPORTED else ["png","jpg","jpeg"]
    type_label   = "PNG, JPG veya PDF" if PDF_SUPPORTED else "PNG, JPG"

    uploaded_keys = st.file_uploader(
        f"Cevap anahtarı ({type_label}) — birden fazla dosya/sayfa seçilebilir",
        type=accept_types,
        accept_multiple_files=True,
        key="uploader_answer_key"
    )

    if uploaded_keys:
        # PDF'leri sayfalara böl, görselleri doğrudan yükle
        pil_images = []
        for f in uploaded_keys:
            if f.name.lower().endswith(".pdf"):
                pages = _pdf_to_images(f.read())
                pil_images.extend(pages)
                st.info(f"📄 **{f.name}** → {len(pages)} sayfa PDF okundu")
            else:
                pil_images.append(Image.open(f).convert("RGB"))

        st.markdown(f"**Toplam {len(pil_images)} sayfa yüklendi.** Önizleme:")
        prev_cols = st.columns(min(len(pil_images), 4))
        for i, img in enumerate(pil_images):
            with prev_cols[i % 4]:
                st.image(img, use_container_width=True, caption=f"Sayfa {i+1}")

        st.markdown("---")
        col_sv, col_ai_btn = st.columns([1, 2])

        with col_sv:
            if st.button("💾 Görselleri Kaydet (AI Okuma Olmadan)", use_container_width=True,
                         key="btn_save_key_only"):
                st.session_state.exam_config["answer_key_images"] = pil_images
                st.session_state.exam_config["key_saved"] = True
                st.session_state.exam_config["questions"] = {}
                st.success("Cevap anahtarı görselleri kaydedildi.")

        with col_ai_btn:
            if st.button("🤖 AI ile Oku — Soruları ve Puanları Çıkar (Önerilen)",
                         type="primary", use_container_width=True, key="btn_ai_read_key"):
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
                    for qid, qinfo in result.get("questions", {}).items():
                        st.markdown(f"- **Soru {qid}:** {qinfo.get('title','')} — **{qinfo.get('max_score',0)} Puan**")
                    st.markdown(f"**Toplam:** {result.get('total_max_score',0)} Puan")
                else:
                    st.error(f"Hata: {result.get('error')}")

    # ── Mevcut durum ──
    if cfg.get("key_saved") and cfg.get("answer_key_images"):
        st.markdown("---")
        n_img = len(cfg["answer_key_images"])
        n_q   = len(cfg.get("questions", {}))
        st.markdown(f"""
        <div class='callout-success'>
            ✅ <strong>Cevap anahtarı yüklü</strong> —
            Sınıf <strong>{cfg['grade']}-{cfg['branch']}</strong> |
            {n_img} sayfa | {n_q} soru tespit edildi
        </div>
        """, unsafe_allow_html=True)

        if cfg.get("questions"):
            with st.expander("📋 Tespit Edilen Soru Yapısını Görüntüle / Düzenle"):
                for qid in sorted(cfg["questions"].keys(),
                                   key=lambda x: int(x) if x.isdigit() else x):
                    q = cfg["questions"][qid]
                    with st.expander(f"Soru {qid} — {q.get('max_score', 0)} Puan"):
                        nm = st.number_input(f"Maksimum Puan", min_value=1, max_value=200,
                                              value=int(q.get("max_score", 10)),
                                              key=f"em_{qid}")
                        ns = st.text_area("Doğru Çözüm Notu", value=q.get("correct_solution",""),
                                           height=70, key=f"es_{qid}")
                        if nm != q.get("max_score") or ns != q.get("correct_solution"):
                            st.session_state.exam_config["questions"][qid]["max_score"] = nm
                            st.session_state.exam_config["questions"][qid]["correct_solution"] = ns

        if st.button("🗑️ Cevap Anahtarını Sıfırla", key="btn_reset_ca"):
            st.session_state.exam_config = {
                "grade":"","branch":"","answer_key_images":[],
                "questions":{},"total_max_score":0,"key_saved":False,
            }
            st.rerun()
    elif not uploaded_keys:
        st.markdown("""
        <div class='callout-warn'>
            ⚠️ Henüz cevap anahtarı yüklenmedi.
        </div>
        """, unsafe_allow_html=True)

    # Secrets'ta API yoksa giriş alanı göster
    if not api_key:
        st.markdown("---")
        _api_warning()


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 2 — SINAV KAĞIDI YÜKLEME                        ║
# ╚═══════════════════════════════════════════════════════╝
with tab_sk:
    st.markdown("### 📷 Sınav Kağıdı Yükleme")
    cfg = st.session_state.exam_config

    if not cfg.get("key_saved"):
        st.markdown("""
        <div class='callout-warn'>
            ⚠️ Önce <strong>Cevap Anahtarı</strong> sekmesinden cevap anahtarını yükleyin!
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='callout-info'>
            Aktif sınıf: <strong>{cfg['grade']}-{cfg['branch']}</strong> |
            Cevap anahtarı: <strong>{len(cfg['answer_key_images'])} sayfa</strong> hazır.
        </div>
        """, unsafe_allow_html=True)

        st.write("Öğrenci kağıtlarını **kameradan** veya **galeriden** yükleyin. AI adı, numarayı, sınıfı otomatik okur.")

        method = st.radio("Yükleme yöntemi:",
                          ["📁 Galeriden Seç (Görsel veya PDF)", "📷 Kameradan Çek"],
                          horizontal=True, key="sk_method")

        student_image = None
        student_extra_pages = []  # Çok sayfalı PDF için ek sayfalar

        if "Galeri" in method:
            sk_types = ["png","jpg","jpeg","pdf"] if PDF_SUPPORTED else ["png","jpg","jpeg"]
            uf = st.file_uploader(
                "Öğrenci sınav kağıdı (PNG, JPG veya PDF — tek öğrenci)",
                type=sk_types, key="sk_gallery"
            )
            if uf:
                if uf.name.lower().endswith(".pdf"):
                    pages = _pdf_to_images(uf.read())
                    if pages:
                        student_image = pages[0]
                        student_extra_pages = pages[1:]  # Geri kalan sayfalar
                        if len(pages) > 1:
                            st.info(f"PDF {len(pages)} sayfa → İlk sayfa kimlik okuma için, tüm sayfalar değerlendirme için kullanılacak.")
                else:
                    student_image = Image.open(uf).convert("RGB")
        else:
            cam = st.camera_input("Kağıdı hizalayın ve çekin", key="sk_cam")
            if cam:
                student_image = Image.open(cam).convert("RGB")

        if student_image:
            st.markdown("---")
            c1, c2 = st.columns([1, 1])
            with c1:
                st.image(student_image, use_container_width=True, caption="Yüklenen görsel")
            with c2:
                st.info("🤖 Butona basınca AI kağıttaki öğrenci bilgilerini okuyacak ve sisteme kaydedecektir.")
                if not api_key:
                    _api_warning()
                else:
                    if st.button("🤖 Yükle ve Tanı", type="primary",
                                  use_container_width=True, key="btn_sk_upload"):
                        with st.spinner("Gemini AI kimliği okuyor..."):
                            id_r = read_student_identity(api_key, student_image)

                        if not id_r.get("success"):
                            st.error(f"Hata: {id_r.get('error')}")
                        else:
                            name   = id_r.get("name","Bilinmeyen Öğrenci").strip()
                            no     = id_r.get("no","0").strip()
                            scls   = id_r.get("class", cfg["grade"]).strip()
                            branch = cfg.get("branch","")

                            if not no or no == "0":
                                no = str(len(st.session_state.student_records) + 1001)

                            # Çok sayfalı öğrenci kağıdı → tüm sayfaları birleştir
                            all_pages = [student_image] + student_extra_pages

                            st.session_state.student_records[no] = {
                                "name": name, "no": no,
                                "class": scls, "branch": branch,
                                "status": "Bekliyor",
                                "grades": {}, "total_score": 0,
                                "page_count": len(all_pages),
                            }
                            # İlk sayfa önizleme için, tüm sayfalar değerlendirme için
                            st.session_state.student_images[no]        = student_image
                            st.session_state.student_all_pages[no]     = all_pages
                            st.success(f"✅ **{name}** — No: {no} — {scls}-{branch} ({len(all_pages)} sayfa)")

        # ── Yüklenen öğrenci listesi ──
        records = st.session_state.student_records
        if records:
            st.markdown("---")
            st.markdown(f"#### 📋 Yüklenen Öğrenciler ({len(records)})")
            for no in sorted(records.keys(),
                              key=lambda x: (int(x) if x.isdigit() else x)):
                rec = records[no]
                rc1, rc2 = st.columns([6, 1])
                with rc1:
                    st.markdown(
                        f"{_badge(rec['status'])} &nbsp; **{rec.get('name','—')}** &nbsp;|&nbsp;"
                        f" No: `{no}` &nbsp;|&nbsp; {rec.get('class','')}–{rec.get('branch','')}",
                        unsafe_allow_html=True)
                with rc2:
                    st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{no}",
                                  help=f"{rec.get('name')} kaydını sil"):
                        del st.session_state.student_records[no]
                        st.session_state.student_images.pop(no, None)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='callout-info' style='margin-top:20px;'>
                Henüz öğrenci eklenmedi.
            </div>
            """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 3 — AI DEĞERLENDİRME                            ║
# ╚═══════════════════════════════════════════════════════╝
with tab_ai:
    st.markdown("### 🧠 Yapay Zeka Değerlendirme")
    cfg     = st.session_state.exam_config
    records = st.session_state.student_records

    if not cfg.get("key_saved"):
        st.markdown("<div class='callout-warn'>⚠️ Önce Cevap Anahtarı sekmesinden cevap anahtarı yükleyin!</div>",
                    unsafe_allow_html=True)
    elif not records:
        st.markdown("<div class='callout-warn'>⚠️ Öğrenci eklenmedi. Sınav Kağıdı sekmesinden ekleyin!</div>",
                    unsafe_allow_html=True)
    elif not _api_warning():
        pass
    else:
        # ── Tümünü değerlendir ──
        bekleyen = [n for n,r in records.items() if r["status"]=="Bekliyor"]
        if bekleyen:
            st.markdown(f"**{len(bekleyen)} öğrenci** değerlendirilmeyi bekliyor.")
            if st.button(f"🤖 Tüm Bekleyen Öğrencileri Değerlendir ({len(bekleyen)})",
                          type="primary", use_container_width=True, key="btn_eval_all"):
                prog = st.progress(0, text="Başlıyor...")
                for i, no in enumerate(bekleyen):
                    rec = records[no]
                    img = st.session_state.student_images.get(no)
                    if not img:
                        continue
                    prog.progress((i+1)/len(bekleyen),
                                   text=f"Değerlendiriliyor: {rec['name']} ({i+1}/{len(bekleyen)})")
                    # Tüm sayfaları kullan (PDF için çok sayfa olabilir)
                    all_pages = st.session_state.student_all_pages.get(no)
                    if not all_pages:
                        all_pages = [img] if img else []
                    if not all_pages:
                        continue
                    res = evaluate_student_paper(api_key, cfg["answer_key_images"],
                                                  all_pages,
                                                  cfg.get("questions",{}))
                    if res.get("success"):
                        grd  = res.get("grades",{})
                        tot  = res.get("total_score",
                                        sum(g.get("score",0) for g in grd.values()))
                        st.session_state.student_records[no]["grades"]      = grd
                        st.session_state.student_records[no]["total_score"] = tot
                        st.session_state.student_records[no]["status"]      = "Değerlendirildi"
                prog.empty()
                st.success("✅ Tüm öğrenciler değerlendirildi!")
                st.rerun()

        st.markdown("---")

        sorted_nos = sorted(records.keys(),
                            key=lambda x: (int(x) if x.isdigit() else x))

        if "selected_no" not in st.session_state:
            st.session_state.selected_no = sorted_nos[0] if sorted_nos else None

        col_list, col_det = st.columns([1, 2])

        # ── Sol: Öğrenci listesi ──
        with col_list:
            st.markdown("**Öğrenciler**")
            for no in sorted_nos:
                rec = records[no]
                is_sel = (no == st.session_state.selected_no)
                btn_t  = "primary" if is_sel else "secondary"
                status_icon = {"Onaylandı":"✅","Değerlendirildi":"🔵","Bekliyor":"⏳"}.get(rec["status"],"⏳")
                if st.button(
                    f"{status_icon} {rec.get('name','—')}\nNo: {no}",
                    key=f"sel_{no}", type=btn_t, use_container_width=True
                ):
                    st.session_state.selected_no = no
                    st.rerun()

        # ── Sağ: Detay ──
        with col_det:
            sel = st.session_state.selected_no
            if sel and sel in records:
                rec = records[sel]
                img = st.session_state.student_images.get(sel)

                st.markdown(f"#### 👤 {rec.get('name','—')}")
                st.markdown(
                    f"No: **{sel}** | Sınıf: **{rec.get('class','')}–{rec.get('branch','')}** | "
                    f"{_badge(rec['status'])}",
                    unsafe_allow_html=True)

                # Değerlendir butonu
                if rec["status"] == "Bekliyor":
                    if img:
                        if st.button("🤖 Bu Öğrenciyi Değerlendir",
                                      use_container_width=True, key=f"eval_{sel}"):
                            with st.spinner(f"{rec['name']} değerlendiriliyor..."):
                                all_pages = st.session_state.student_all_pages.get(sel, [img])
                                res = evaluate_student_paper(
                                    api_key, cfg["answer_key_images"],
                                    all_pages, cfg.get("questions",{}))
                            if res.get("success"):
                                grd = res.get("grades",{})
                                tot = res.get("total_score",
                                               sum(g.get("score",0) for g in grd.values()))
                                st.session_state.student_records[sel]["grades"]      = grd
                                st.session_state.student_records[sel]["total_score"] = tot
                                st.session_state.student_records[sel]["status"]      = "Değerlendirildi"
                                st.success("✅ Değerlendirme tamamlandı!")
                                st.rerun()
                            else:
                                st.error(f"Hata: {res.get('error')}")
                    else:
                        st.warning("Bu öğrenciye ait görsel bulunamadı.")

                # Kağıt görseli
                if img:
                    with st.expander("📄 Öğrenci Kağıdı"):
                        st.image(img, use_container_width=True)

                # Puan tablosu
                grades = rec.get("grades",{})
                if grades:
                    st.markdown("#### 📊 Soru Bazlı Puanlar")
                    total_s, total_m = 0, 0

                    for qid in sorted(grades.keys(), key=lambda x: int(x) if x.isdigit() else x):
                        g      = grades[qid]
                        score  = g.get("score", 0)
                        max_sc = g.get("max_score",
                                        cfg.get("questions",{}).get(qid,{}).get("max_score","?"))
                        fb     = g.get("feedback","")
                        st_ans = g.get("student_answer","")
                        total_s += score
                        if isinstance(max_sc,(int,float)):
                            total_m += max_sc

                        pct   = int(score/max_sc*100) if isinstance(max_sc,(int,float)) and max_sc else 0
                        color = "#34d399" if pct>=75 else ("#fbbf24" if pct>=40 else "#f87171")

                        st.markdown(f"""
                        <div class='premium-card' style='padding:12px 16px; margin-bottom:8px;'>
                            <div style='display:flex;justify-content:space-between;align-items:center;'>
                                <span style='font-weight:700;'>Soru {qid}</span>
                                <span style='font-size:1.3rem;font-weight:800;color:{color};'>{score} / {max_sc}</span>
                            </div>
                            {"<div style='color:#94a3b8;font-size:0.82rem;margin-top:4px;'>📝 " + st_ans + "</div>" if st_ans else ""}
                            {"<div style='color:#64748b;font-size:0.82rem;margin-top:4px;'>🤖 " + fb + "</div>" if fb else ""}
                        </div>
                        """, unsafe_allow_html=True)

                    # Toplam
                    tc = "#34d399" if total_m>0 and total_s/total_m>=0.5 else "#f87171"
                    st.markdown(f"""
                    <div style='background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.3);
                                border-radius:12px;padding:14px 20px;text-align:center;margin-top:8px;'>
                        <div style='color:#94a3b8;font-size:0.8rem;text-transform:uppercase;letter-spacing:.06em;'>
                            TOPLAM PUAN</div>
                        <span style='font-size:2.4rem;font-weight:800;color:{tc};'>{total_s}</span>
                        <span style='color:#64748b;'> / {total_m}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    if rec["status"] == "Değerlendirildi":
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown('<div class="approve-btn">', unsafe_allow_html=True)
                        if st.button("✅ Değerlendirmeyi Onayla ve Kaydet",
                                      key=f"appr_{sel}", use_container_width=True):
                            st.session_state.student_records[sel]["status"]      = "Onaylandı"
                            st.session_state.student_records[sel]["total_score"] = total_s
                            st.success(f"✅ {rec['name']} onaylandı! Toplam: {total_s}/{total_m}")
                            idx = sorted_nos.index(sel)
                            if idx+1 < len(sorted_nos):
                                st.session_state.selected_no = sorted_nos[idx+1]
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    elif rec["status"] == "Onaylandı":
                        st.markdown("<div class='callout-success'>✅ Bu öğrenci onaylandı.</div>",
                                    unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════╗
# ║  TAB 4 — NOT ÇİZELGESİ                               ║
# ╚═══════════════════════════════════════════════════════╝
with tab_nc:
    st.markdown("### 📋 Not Çizelgesi")
    records = st.session_state.student_records
    onaylanan = {n:r for n,r in records.items() if r.get("status")=="Onaylandı"}

    if not onaylanan:
        st.markdown("""
        <div class='callout-info'>
            📭 Henüz onaylanmış öğrenci kaydı yok.<br>
            AI Değerlendirme sekmesinden öğrencileri onaylayın.
        </div>
        """, unsafe_allow_html=True)
    else:
        cfg = st.session_state.exam_config
        questions = cfg.get("questions",{})
        total_max = sum(q.get("max_score",0) for q in questions.values()) if questions else 0

        df = get_approved_grades_dataframe()
        avg = df["Toplam"].mean() if not df.empty and "Toplam" in df.columns else 0

        st.markdown(f"""
        <div class='callout-success'>
            ✅ <strong>{len(onaylanan)} öğrenci</strong> onaylandı — numara sırasıyla listeleniyor.
        </div>
        """, unsafe_allow_html=True)

        k1, k2, k3 = st.columns(3)
        with k1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Öğrenci Sayısı</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
        with k2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Sınıf Ortalaması</div><div class='metric-value'>{avg:.1f}</div></div>", unsafe_allow_html=True)
        with k3:
            pct = (avg/total_max*100) if total_max>0 else 0
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Ortalama Başarı</div><div class='metric-value'>%{pct:.0f}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if not df.empty:
            html = "<div class='table-responsive'><table class='custom-table'><thead><tr>"
            for c in df.columns:
                html += f"<th>{c}</th>"
            html += "</tr></thead><tbody>"
            for _, row in df.iterrows():
                html += "<tr>"
                for c in df.columns:
                    v = row[c]
                    if c == "Toplam":
                        p = (v/total_max*100) if total_max>0 else 0
                        clr = "#34d399" if p>=50 else "#f87171"
                        html += f"<td style='font-weight:700;color:{clr};'>{v}</td>"
                    else:
                        html += f"<td>{v}</td>"
                html += "</tr>"
            html += "</tbody></table></div>"
            st.markdown(html, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            csv = df.to_csv(index=False).encode("utf-8")
            fn  = f"notlar_{cfg.get('grade','')}_{cfg.get('branch','')}.csv"
            st.download_button("📥 Not Çizelgesini CSV Olarak İndir",
                                data=csv, file_name=fn, mime="text/csv",
                                use_container_width=True)
