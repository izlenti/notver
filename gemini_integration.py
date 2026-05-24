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


import time

def generate_with_retry(api_key, contents, generation_config=None, system_instruction=None):
    """
    Tries multiple Gemini models and handles 429/quota errors with backoff.
    """
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    models_to_try = [
        "gemini-3.5-flash",
        "gemini-3.1-pro-preview",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash"
    ]
    
    tried_errors = []
    
    for model_name in models_to_try:
        max_retries = 3
        backoff_sec = 2
        
        for attempt in range(max_retries):
            try:
                if system_instruction:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )
                else:
                    model = genai.GenerativeModel(model_name=model_name)
                
                response = model.generate_content(
                    contents=contents,
                    generation_config=generation_config
                )
                return response, model_name
            except Exception as e:
                err_msg = str(e)
                err_msg_lower = err_msg.lower()
                
                is_429 = "429" in err_msg_lower or "resourceexhausted" in err_msg_lower or "quota" in err_msg_lower or "rate limit" in err_msg_lower
                is_not_found = "404" in err_msg_lower or "not found" in err_msg_lower or "not supported" in err_msg_lower
                
                if is_not_found:
                    tried_errors.append((model_name, "Desteklenmiyor / Bulunamadı (404)"))
                    break
                
                if is_429:
                    if "limit: 0" in err_msg_lower or "limit: 0.0" in err_msg_lower:
                        tried_errors.append((model_name, "Kota Limiti Sıfır (limit: 0)"))
                        break
                    
                    if attempt < max_retries - 1:
                        time.sleep(backoff_sec)
                        backoff_sec *= 2
                        continue
                    else:
                        tried_errors.append((model_name, "Rate Limit Aşıldı (429)"))
                        break
                else:
                    tried_errors.append((model_name, err_msg))
                    break
                    
    if tried_errors:
        err_details = []
        for m_name, err in tried_errors:
            err_details.append(f"• {m_name}: {err}")
        err_msg = "Tüm modeller başarısız oldu:\n" + "\n".join(err_details)
        raise Exception(err_msg)
        
    raise Exception("Model listesi boş veya çalıştırılamadı.")


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
        contents = [ANSWER_KEY_PROMPT] + answer_key_images
        response, used_model = generate_with_retry(
            api_key=api_key,
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
        result["used_model"] = used_model
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
        response, used_model = generate_with_retry(
            api_key=api_key,
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
        result["used_model"] = used_model
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


def evaluate_student_paper(api_key, answer_key_images, student_paper, questions_dict):
    """
    Öğrencinin kağıdını cevap anahtarıyla karşılaştırarak puanlar.
    answer_key_images: list of PIL Image (cevap anahtarı sayfaları)
    student_paper: PIL Image VEYA list of PIL Image (öğrenci kağıdı — tek veya çok sayfalı)
    questions_dict: dict (soru yapısı)
    """
    if not api_key:
        return {"success": False, "error": "API anahtarı bulunamadı."}

    if isinstance(student_paper, list):
        student_images = student_paper
    else:
        student_images = [student_paper]

    try:
        questions_text = "SINAV SORU YAPISI:\n"
        for q_id, q_info in questions_dict.items():
            questions_text += f"- Soru {q_id}: Maksimum {q_info['max_score']} puan\n"

        prompt = f"""
Sana {len(answer_key_images)} sayfalık CEVAP ANAHTARI ve {len(student_images)} sayfalık ÖĞRENCI KAĞIDI gönderiyorum.

{questions_text}

Lütfen:
1. Cevap anahtarındaki her soruyu ve doğru çözümü analiz et.
2. Öğrenci kağıdındaki her sorunun çözümünü oku (OCR — el yazısını dahil).
3. Her soruyu karşılaştırarak adil bir puan ver.
4. JSON formatında döndür.

GÖRSELLER SIRASI: Önce cevap anahtarı sayfaları ({len(answer_key_images)} sayfa), 
sonra öğrenci kağıdı sayfaları ({len(student_images)} sayfa).
"""

        contents = [prompt] + answer_key_images + student_images
        response, used_model = generate_with_retry(
            api_key=api_key,
            contents=contents,
            generation_config={"response_mime_type": "application/json"},
            system_instruction=EVALUATION_SYSTEM_PROMPT
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["success"] = True
        result["used_model"] = used_model
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
