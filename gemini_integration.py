# gemini_integration.py
import json
import google.generativeai as genai
from PIL import Image

# ─────────────────────────────────────────────────────────────────────────────
# Cevap anahtarından soru bilgilerini okuyan prompt
# ─────────────────────────────────────────────────────────────────────────────
ANSWER_KEY_PROMPT = """
Sen bir matematik sınavı cevap anahtarı okuma uzmanısın.
Sana bir öğretmenin hazırladığı cevap anahtarı görseli gönderilecek.
Bu görselde sorular, doğru çözümler ve her soruya ait puanlar bulunmaktadır.

Görevin:
1. Görseldeki tüm soruları tespit et (soru numarası veya sıra numarası).
2. Her sorunun maksimum puanını bul (örn: "9p", "7P", "10 puan" gibi yazılmış olabilir).
3. Her sorunun doğru çözümünü/cevabını oku.
4. Toplam puanı hesapla.

KESİNLİKLE aşağıdaki JSON formatında yanıt ver, başka metin ekleme:
{
  "questions": {
    "1": {
      "title": "Soru 1",
      "max_score": <puan_sayisi_integer>,
      "correct_solution": "<dogru_cozum_metni>"
    },
    "2": {
      "title": "Soru 2", 
      "max_score": <puan_sayisi_integer>,
      "correct_solution": "<dogru_cozum_metni>"
    }
  },
  "total_max_score": <toplam_puan_integer>
}

Soru numarası görüntüde belirtilmemişse 1, 2, 3... olarak sırala.
Puanlar görüntüde "9p", "7P", "7 puan", daire içinde sayı vb. şekillerde olabilir.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Öğrenci kağıdı kimlik bilgisi okuma promptu
# ─────────────────────────────────────────────────────────────────────────────
IDENTITY_PROMPT = """
Sen bir sınav kağıdı kimlik bilgisi okuma uzmanısın.
Sana bir öğrencinin sınav kağıdının görseli gönderilecek.
Kağıdın üst kısmında genellikle AD-SOYAD, NUMARA, SINIF alanları bulunur.

Görevin: Bu üç bilgiyi kağıttan oku.

Eğer bir bilgi okunamazsa varsayılan değerleri kullan.

KESİNLİKLE aşağıdaki JSON formatında yanıt ver:
{
  "name": "<ad_soyad>",
  "no": "<okul_numarasi>",
  "class": "<sinif_orn_5_veya_5A>"
}

Eğer isim okunamazsa: "Bilinmeyen Öğrenci"
Eğer numara okunamazsa: "0"
Eğer sınıf okunamazsa: "Bilinmiyor"
"""

# ─────────────────────────────────────────────────────────────────────────────
# Öğrenci kağıdını cevap anahtarıyla karşılaştıran değerlendirme promptu
# ─────────────────────────────────────────────────────────────────────────────
EVALUATION_SYSTEM_PROMPT = """
Sen açık uçlu matematik ve geometri sınavlarını puanlayan deneyimli bir yapay zeka öğretmenisin.
Sana bir CEVAP ANAHTARI görseli ve bir ÖĞRENCİ KAĞIDI görseli gönderilecek.

Görevin:
1. Cevap anahtarındaki her soruyu ve doğru çözümü tespit et.
2. Öğrencinin her soruya verdiği cevabı/çözümü oku (OCR).
3. Her soruyu karşılaştırarak puanla.

PUANLAMA KURALLARI:
- Cevap anahtarındaki maksimum puanı baz al.
- Tam doğru çözüm → tam puan
- Mantık doğru ama küçük hesap hatası → puanın %70-90'ı
- Kısmen doğru yaklaşım → puanın %30-60'ı  
- Yanlış veya boş → 0 puan
- Geometri çizimlerini ve şekillerin üzerindeki el yazısı notları dikkate al.
- Dağınık ama doğru çözüm → tam puan (yazı güzelliği etkilemez).

KESİNLİKLE aşağıdaki JSON formatında yanıt ver, başka metin ekleme:
{
  "grades": {
    "1": {
      "score": <verilen_puan_integer>,
      "max_score": <maksimum_puan_integer>,
      "student_answer": "<okunan_ogrenci_cevabi>",
      "feedback": "<Turkce_kisa_degerlendirme_1_2_cumle>"
    },
    "2": {
      "score": <verilen_puan_integer>,
      "max_score": <maksimum_puan_integer>,
      "student_answer": "<okunan_ogrenci_cevabi>",
      "feedback": "<Turkce_kisa_degerlendirme>"
    }
  },
  "total_score": <toplam_verilen_puan>,
  "total_max_score": <toplam_maksimum_puan>
}
"""


def read_answer_key(api_key, answer_key_images):
    """
    Cevap anahtarı görsellerini okuyup soru yapısını çıkarır.
    answer_key_images: list of PIL Image
    """
    if not api_key:
        return {"success": False, "error": "API anahtarı bulunamadı."}
    if not answer_key_images:
        return {"success": False, "error": "Cevap anahtarı görseli yüklenmedi."}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")

        contents = [ANSWER_KEY_PROMPT] + answer_key_images
        response = model.generate_content(
            contents=contents,
            generation_config={"response_mime_type": "application/json"}
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[-2] if "```" in raw else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["success"] = True
        return result

    except json.JSONDecodeError:
        return {"success": False, "error": f"AI JSON formatında yanıt vermedi: {response.text[:300]}"}
    except Exception as e:
        return {"success": False, "error": f"Gemini API hatası: {str(e)}"}


def read_student_identity(api_key, student_image):
    """
    Öğrenci kağıdındaki kimlik bilgilerini okur.
    student_image: PIL Image
    """
    if not api_key:
        return {"success": False, "error": "API anahtarı bulunamadı."}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")

        response = model.generate_content(
            contents=[IDENTITY_PROMPT, student_image],
            generation_config={"response_mime_type": "application/json"}
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["success"] = True
        return result

    except json.JSONDecodeError:
        return {
            "success": True,
            "name": "Bilinmeyen Öğrenci",
            "no": "0",
            "class": "Bilinmiyor"
        }
    except Exception as e:
        return {"success": False, "error": f"Gemini API hatası: {str(e)}"}


def evaluate_student_paper(api_key, answer_key_images, student_image, questions_dict):
    """
    Öğrencinin kağıdını cevap anahtarıyla karşılaştırarak puanlar.
    answer_key_images: list of PIL Image (cevap anahtarı sayfaları)
    student_image: PIL Image (öğrenci kağıdı)
    questions_dict: dict (soru yapısı - soru no → {title, max_score, correct_solution})
    """
    if not api_key:
        return {"success": False, "error": "API anahtarı bulunamadı."}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=EVALUATION_SYSTEM_PROMPT
        )

        # Soru yapısını metne dök
        questions_text = "SINAV SORU YAPISI (Cevap anahtarından okunacak):\n"
        for q_id, q_info in questions_dict.items():
            questions_text += f"- Soru {q_id}: Maksimum {q_info['max_score']} puan\n"

        prompt = f"""
Sana {len(answer_key_images)} sayfalık CEVAP ANAHTARI ve 1 ÖĞRENCI KAĞIDI gönderiyorum.

{questions_text}

Lütfen:
1. Cevap anahtarındaki her soruyu ve doğru çözümü analiz et.
2. Öğrenci kağıdındaki her sorunun çözümünü oku.
3. Her soruyu karşılaştırarak adil bir puan ver.
4. JSON formatında döndür.

GÖRSELLER SIRASI: Önce cevap anahtarı sayfaları, en son öğrenci kağıdı.
"""

        contents = [prompt] + answer_key_images + [student_image]
        response = model.generate_content(
            contents=contents,
            generation_config={"response_mime_type": "application/json"}
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["success"] = True
        return result

    except json.JSONDecodeError:
        return {"success": False, "error": f"AI JSON formatında yanıt vermedi: {response.text[:300]}"}
    except Exception as e:
        return {"success": False, "error": f"Gemini API hatası: {str(e)}"}


# Legacy fallback - eski kodla uyumluluk
def evaluate_entire_exam_page(api_key, paper_image, questions_dict):
    return evaluate_student_paper(api_key, [], paper_image, questions_dict)

def evaluate_math_paper(api_key, paper_image, question_text, correct_answer, max_score):
    mock_dict = {"1": {"title": "Soru", "max_score": max_score, "correct_solution": correct_answer}}
    return evaluate_student_paper(api_key, [], paper_image, mock_dict)
