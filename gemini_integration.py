# gemini_integration.py
import json
import google.generativeai as genai
from PIL import Image

SYSTEM_PROMPT = """
Sen açık uçlu matematik ve geometri sınavlarını puanlayan son derece hassas ve deneyimli bir yapay zeka öğretmenisin.
Görevin, sana gönderilen öğrenci el yazısı sınav sayfalarını okumak (OCR), geometri şekilleri ve üzerindeki el yazısı açıları analiz etmek ve adil bir notlandırma yapmaktır.

Senden şu kurallara kesinlikle uymanı bekliyoruz:
1. GEOMETRİ ŞEKİL & ÇİZİM ANALİZİ:
   - Sorularda yer alan geometri şekillerini (çokgenler, üçgenler vb.) ve bunların üzerindeki el yazısı işaretlemeleri (açılar, kenar eşitlik çizgileri/tikleri, oklar, ek çizgiler) dikkatle analiz et.
   - Öğrencinin şekillerin üzerine yerleştirdiği açı değerlerini ve ikizkenarlık çıkarımlarını çözüm mantığının bir parçası olarak değerlendir.

2. TOPLU/BÜTÜNSEL SAYFA OKUMA (ÇOKLU SORU ANALİZİ):
   - Sana gönderilen görsel tek bir sayfada birden fazla soru (örneğin Soru 21, 22, 24, 25) içeriyor olabilir.
   - Görseldeki tüm soruları teker teker tespit et, her sorunun çözümünü kendi içinde ayrı ayrı değerlendir.

3. HASSAS VE KADEMELİ PUANLAMA STRATEJİSİ:
   - Her soru için öğretmen tarafından belirtilen maksimum puan (max_score) değerini baz al ve aşağıdaki oransal dağılıma göre puanla:
     a) Kavramsal Yaklaşım ve Formül Kurulumu (%40): Doğru teoremi/formülü kurmuş mu? Geometride ikizkenarlık veya kenar eşitliğini yakalamış mı?
     b) İşlem Adımları ve Matematiksel İlerleme (%40): Matematiksel adımları doğru ilerletmiş mi, adımlar arasında işlem veya mantık hatası var mı?
     c) Sonuç ve Hesaplama Doğruluğu (%20): Nihai sonuç tam doğru mu?

4. BASİT HATA VS KAVRAM HATASI AYRIMI:
   - Ufak aritmetik/işlem hataları (örneğin basit bir bölme veya toplama hatası): Eğer tüm geometrik mantık ve teorem kurulumları doğruysa, sadece Sonuç Puanını (%20) sıfırla ve adımlardan çok küçük bir puan kır (örn. toplam 25 puanlık sorudan sadece 1 ya da 2 puan kır).
   - Temel Kavram Hatası: Eğer yöntem tamamen yanlışsa, fakat tesadüfen sonuç doğru çıktıysa (Tesadüfi Doğru), bu adıma puan verme veya sembolik 1 puan ver.

5. ÖĞRENCİ KİMLİK BİLGİLERİNİN OTOMATİK TESPİTİ (AUTO-IDENTITY EXTRACTION):
   - Sınav kağıdının en üstünde yer alan öğrencinin Adı-Soyadı (name), Okul Numarası (no) ve Sınıf/Şube (class) bilgilerini görselden bulup oku (OCR).
   - Eğer kağıt üzerinde bu bilgiler bulunmuyorsa veya okunamıyorsa, şu varsayılan değerleri ata:
     * "name": "Bilinmeyen Öğrenci"
     * "no": "Bilinmeyen No"
     * "class": "5-A" (Veya kağıt üzerinde örneğin 6-B yazıyorsa tam olarak "6-B" olarak çıkar.)

Senden cevabını KESİNLİKLE aşağıdaki JSON formatında vermeni rica ediyoruz. Başka hiçbir açıklama metni ekleme, doğrudan geçerli bir JSON döndür:
{
  "student_info": {
    "name": "<ogrenci_adi_soyadi>",
    "class": "<sinif_sube_orn_5-A>",
    "no": "<okul_numarasi_orn_101>"
  },
  "grades": {
    "<soru_numarasi_1>": {
      "score_concept": <kavramsal_yaklasim_puani_tamsayi>,
      "score_steps": <islem_adimlari_puani_tamsayi>,
      "score_result": <sonuc_dogrulugu_puani_tamsayi>,
      "score_total": <toplam_puan_tamsayi>,
      "detected_text": "<AI_tarafindan_okunan_cozum_metni>",
      "ai_feedback": "<Türkçe dilinde, Kavramsal, İşlem ve Sonuç alt başlıklarıyla yapılan detaylı analiz ve puanlama gerekçesi.>"
    },
    "<soru_numarasi_2>": {
      ...
    }
  }
}
"""

def evaluate_entire_exam_page(api_key, paper_image, questions_dict):
    """
    Evaluates an entire exam page containing multiple questions and geometry figures
    using Gemini 1.5 Flash in a single API call.
    """
    if not api_key:
        return {
            "success": False,
            "error": "API anahtarı girilmedi. Lütfen ayarlar kısmından API anahtarınızı giriniz veya Simülasyon modunu kullanınız."
        }

    try:
        # API'yi Yapılandır
        genai.configure(api_key=api_key)
        
        # Gemini 1.5 Flash Modelini Yükle
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        
        # Soruların tanımlarını ve cevap anahtarlarını prompta ekle
        questions_prompt = ""
        for q_id, q_info in questions_dict.items():
            questions_prompt += f"""
            ---
            Soru Numarası: {q_id}
            Soru Başlığı: {q_info['title']}
            Soru Açıklaması: {q_info['desc']}
            Doğru Çözüm / Cevap Anahtarı: {q_info['correct_solution']}
            Maksimum Puan: {q_info['max_score']} Puan
            Rubrik Dağılımı: Kavramsal (Max: {q_info['max_score']*0.4}), İşlem Adımı (Max: {q_info['max_score']*0.4}), Sonuç (Max: {q_info['max_score']*0.2})
            """

        prompt = f"""
        Aşağıda sınavda yer alan tüm soruların orijinal metinleri ve doğru çözüm cevap anahtarı yer almaktadır:
        {questions_prompt}
        
        Lütfen ekteki öğrenci sınav kağıdı görselinin tamamını tara. 
        Yukarıda belirtilen soru numaralarına göre (örneğin 21, 22, 24, 25) öğrencinin çözümlerini ve varsa geometri şekilleri üzerindeki el yazısı karalamaları/açıları analiz et.
        Her soruyu ayrı ayrı puanlayıp Türkçe gerekçeleriyle birlikte sistem yönergesinde belirtilen JSON formatında yanıt döndür.
        """
        
        # Görseli ve metni birlikte gönder
        response = model.generate_content(
            contents=[prompt, paper_image],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # JSON çıktısını çözümle
        result_json = json.loads(response.text)
        result_json["success"] = True
        return result_json
        
    except json.JSONDecodeError as je:
        try:
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            result_json = json.loads(raw_text.strip())
            result_json["success"] = True
            return result_json
        except Exception as e:
            return {
                "success": False,
                "error": f"API JSON formatında yanıt döndürmedi. Alınan yanıt: {response.text[:200]}..."
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Gemini API hatası oluştu: {str(e)}"
        }

def evaluate_math_paper(api_key, paper_image, question_text, correct_answer, max_score):
    """
    Fallback function for single question evaluation.
    Converts inputs to a single question dictionary and calls evaluate_entire_exam_page.
    """
    mock_dict = {
        "1": {
            "title": "Soru",
            "desc": question_text,
            "correct_solution": correct_answer,
            "max_score": max_score
        }
    }
    result = evaluate_entire_exam_page(api_key, paper_image, mock_dict)
    if result.get("success") and "grades" in result:
        # Tek soruluk sonuca indirge
        q_result = result["grades"].get("1")
        if q_result:
            q_result["success"] = True
            return q_result
    return result
