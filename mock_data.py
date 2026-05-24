# mock_data.py
import os
import math
from PIL import Image, ImageDraw, ImageFont

# 1. Gerçek Sınav Tanımları ve Cevap Anahtarları (Kullanıcının Geometri Kağıdından)
MOCK_EXAM = {
    "title": "Geometri ve Düzgün Çokgenler Sınavı",
    "topic": "Çokgen Çevre, Köşegen ve Açı Hesaplamaları",
    "total_score": 100,
    "questions": {
        "21": {
            "title": "Soru 21: Dış Açı ve Kenar Sayısı",
            "desc": "Bir dış açısının ölçüsü 15° olan düzgün çokgen kaç kenarlıdır?",
            "max_score": 20,
            "correct_solution": "Dış açı formülü: Dış Açı = 360 / n\n15 = 360 / n  =>  n = 360 / 15  =>  n = 24.\nBu düzgün çokgen 24 kenarlıdır.",
            "rubric": {
                "concept": 8,  # Kavramsal Yaklaşım (%40)
                "steps": 8,    # İşlem Adımları (%40)
                "result": 4    # Sonuç (%20)
            }
        },
        "22": {
            "title": "Soru 22: Köşegen ve İç Açı İlişkisi",
            "desc": "Bir düzgün çokgenin bir köşesinden çizilen tüm köşegenlerle oluşan üçgen sayısı 3'tür. Buna göre bu düzgün çokgenin bir iç açısının ölçüsü kaç derecedir?",
            "max_score": 25,
            "correct_solution": "1. Bir köşeden çizilen köşegenlerin oluşturduğu üçgen sayısı formülü: n - 2\nn - 2 = 3  =>  n = 5 (Düzgün Beşgen).\n2. Bir iç açının ölçüsü formülü: (n - 2) * 180 / n\n3 * 180 / 5 = 540 / 5 = 108°.\nBu çokgenin bir iç açısı 108 derecedir.",
            "rubric": {
                "concept": 10,
                "steps": 10,
                "result": 5
            }
        },
        "24": {
            "title": "Soru 24: Şekilli Dış Açı ve Köşegen Sayısı",
            "desc": "Şekilde bir dış açısının ölçüsü 45° olan düzgün çokgen verilmiştir. Buna göre, bu çokgenin A köşesinden çizilen köşegen sayısı kaçtır?",
            "max_score": 25,
            "correct_solution": "1. Dış açısı 45° olan çokgenin kenar sayısı (n): n = 360 / 45 = 8 (Sekizgen).\n2. Bir köşeden çizilen köşegen sayısı formülü: n - 3\n8 - 3 = 5.\nBu çokgenin A köşesinden çizilen köşegen sayısı 5'tir.",
            "rubric": {
                "concept": 10,
                "steps": 10,
                "result": 5
            }
        },
        "25": {
            "title": "Soru 25: Çokgen ve Eşkenar Üçgen Karışık Açı Sorusu",
            "desc": "Şekilde ABCDE düzgün beşgen ve AFB eşkenar üçgendir. Buna göre m(DEF) açısının ölçüsü kaç derecedir?",
            "max_score": 30,
            "correct_solution": "1. AFB eşkenar üçgen olduğundan m(FAB) = 60° ve |AB| = |AF| = |FB|.\n2. ABCDE düzgün beşgen olduğundan m(EAB) = 108° ve |AB| = |AE| = |BC| = |CD| = |DE|.\n3. |AE| = |AB| ve |AF| = |AB| olduğundan |AE| = |AF|'dir. Dolayısıyla AEF üçgeni ikizkenar üçgendir.\n4. m(EAF) = m(EAB) - m(FAB) = 108° - 60° = 48°.\n5. İkizkenar AEF üçgeninde tepe açısı m(EAF) = 48° ise taban açıları: m(AEF) = m(AFE) = (180° - 48°) / 2 = 66°.\n6. Beşgenin iç açısı m(AED) = 108°'dir. Buradan: m(DEF) = m(AED) - m(AEF) = 108° - 66° = 42° bulunur.",
            "rubric": {
                "concept": 12,
                "steps": 12,
                "result": 6
            }
        }
    }
}

# 2. Gerçekçi Öğrenci Çözüm Verileri
MOCK_STUDENTS = {
    "101": {
        "id": "101",
        "name": "Ahmet Yılmaz",
        "writing_style": "clear",
        "class": "5-A",
        "grades": {
            "21": {
                "score_concept": 8,
                "score_steps": 8,
                "score_result": 4,
                "score_total": 20,
                "ai_feedback": (
                    "**1. Kavramsal Yaklaşım (8/8):**\n"
                    "Düzgün çokgenlerde dış açı ile kenar sayısı ilişkisi formülü (360 / n = Dış Açı) eksiksiz kurulmuş.\n\n"
                    "**2. İşlem Adımları (8/8):**\n"
                    "360'ın 15'e bölünmesi işlemi ve sadeleştirme adımları matematiksel olarak tamamen doğrudur.\n\n"
                    "**3. Sonuç (4/4):**\n"
                    "Nihai kenar sayısı 24 olarak doğru bulunmuştur."
                ),
                "student_solution": "360 / 15 = 24 kenarlıdır.",
                "writing_style": "clear"
            },
            "22": {
                "score_concept": 10,
                "score_steps": 10,
                "score_result": 5,
                "score_total": 25,
                "ai_feedback": (
                    "**1. Kavramsal Yaklaşım (10/10):**\n"
                    "Bir köşeden çizilen köşegenlerin oluşturduğu üçgen sayısı (n-2) formülü doğru uygulanarak çokgenin beşgen olduğu tespit edilmiş.\n\n"
                    "**2. İşlem Adımları (10/10):**\n"
                    "Beşgenin iç açılar toplamı (3 * 180 = 540) hesaplanmış ve 5'e bölünerek tek bir iç açı adımı başarıyla tamamlanmıştır.\n\n"
                    "**3. Sonuç (5/5):**\n"
                    "İç açı değeri 108° olarak tam doğru bulunmuştur."
                ),
                "student_solution": "n - 2 = 3 => n = 5 (Beşgen)\nİç açılar toplamı = 3 * 180 = 540°\nBir iç açı = 540 / 5 = 108°",
                "writing_style": "clear"
            },
            "24": {
                "score_concept": 10,
                "score_steps": 10,
                "score_result": 5,
                "score_total": 25,
                "ai_feedback": (
                    "**[GEOMETRİ ŞEKİL ANALİZİ]**\n"
                    "AI, çokgen şekli üzerindeki 45° dış açı bilgisini başarıyla okudu.\n"
                    "**1. Kavramsal Yaklaşım (10/10):**\n"
                    "Dış açıdan kenar sayısı (n=8) ve bir köşeden çizilen köşegen sayısı (n-3) formülü tam olarak kavranmış.\n\n"
                    "**2. İşlem Adımları (10/10):**\n"
                    "Sekizgen bulma bölme adımları ve köşegen çıkarma adımları hatasız yazılmıştır.\n\n"
                    "**3. Sonuç (5/5):**\n"
                    "Köşegen sayısı 5 olarak doğru bulunmuştur."
                ),
                "student_solution": "360 / 45 = 8 kenarlı (Sekizgen)\nBir köşeden köşegen sayısı = n - 3 => 8 - 3 = 5.",
                "writing_style": "clear"
            },
            "25": {
                "score_concept": 12,
                "score_steps": 12,
                "score_result": 6,
                "score_total": 30,
                "ai_feedback": (
                    "**[GEOMETRİ ŞEKİL & ÇİZİM ANALİZİ]**\n"
                    "Öğrenci kağıdı taranarak düzgün beşgen ve eşkenar üçgen üzerindeki tüm geometrik eşitlikler başarıyla algılanmıştır:\n"
                    "- **İkizkenarlık Keşfi (12/12):** |AE| = |AF| eşitliğini yakalamak için |AB| kenarı üzerinden ikizkenar üçgen kurulumunu doğru yapmış.\n"
                    "- **Açı Çıkarma Adımları (12/12):** EAF açısını 108 - 60 = 48° bularak ikizkenar üçgenden taban açılarını (180-48)/2 = 66° olarak hatasız ilerletmiş. Beşgenin 108° iç açısından 66° düşerek nihai açıyı (108 - 66 = 42°) hesaplamıştır.\n"
                    "- **Sonuç (6/6):** m(DEF) = 42° sonucu mükemmel ve hatasızdır."
                ),
                "student_solution": "AE = AF ikizkenar.\nm(EAF) = 108 - 60 = 48°\nm(AEF) = (180 - 48) / 2 = 66°\nm(DEF) = 108 - 66 = 42°",
                "writing_style": "clear"
            }
        }
    },
    "103": {
        "id": "103",
        "name": "Burak Öztürk (Dağınık Yazım Sınavı)",
        "writing_style": "messy_math",
        "class": "6-B",
        "grades": {
            "21": {
                "score_concept": 8,
                "score_steps": 8,
                "score_result": 4,
                "score_total": 20,
                "ai_feedback": (
                    "**[DETAYLI KARIŞIK YAZIM ANALİZİ]**\n"
                    "Öğrencinin çözümü kağıt üzerinde dağınıktır. Bölme işlemini bakkal bölmesi şeklinde elle karalamış ve yan tarafa '24' yazmıştır.\n"
                    "**Analiz:** Karalamalara rağmen işlem adımları takip edilerek mantık tamamen doğru bulunmuş ve tam puan verilmiştir."
                ),
                "student_solution": "360 / 15 ... bölme karalaması ... sonuç 24 buldum.",
                "writing_style": "messy_math"
            },
            "22": {
                "score_concept": 10,
                "score_steps": 10,
                "score_result": 5,
                "score_total": 25,
                "ai_feedback": "Dağınık yazıma rağmen n=5 bulup iç açıyı 108° olarak hesaplama mantığı tamdır.",
                "student_solution": "n-2=3 ise beşgen. iç açı 108.",
                "writing_style": "messy_math"
            },
            "24": {
                "score_concept": 10,
                "score_steps": 10,
                "score_result": 5,
                "score_total": 25,
                "ai_feedback": "Arayüzdeki çokgen resmi üzerinde öğrencinin karalamaları başarıyla okunmuş, n=8 ve köşegen sayısı 5 bulunmuştur.",
                "student_solution": "360/45=8. sekizgen ise 8-3=5.",
                "writing_style": "messy_math"
            },
            "25": {
                "score_concept": 12,
                "score_steps": 12,
                "score_result": 6,
                "score_total": 30,
                "ai_feedback": (
                    "**[GEOMETRİ KARIŞIK ÇİZİM ANALİZİ - TAM PUAN]**\n"
                    "Öğrenci geometrik şekil üzerine elle `60`, `48` ve `66` dereceleri dağınık şekilde yazmış ve oklarla işaretlemiştir.\n"
                    "**İnceleme:** Çözüm kağıt üzerinde çok dağınık ve karalama doludur. Ancak öğrenci ikizkenarlığı doğru kavramış, şekil üzerindeki karalamalarında taban açılarını 66° göstererek en dipte `108 - 66 = 42°` sonucuna ulaşmıştır. Sırf yazı ve çizim dağınıklığı nedeniyle puan kırılmamış, tam puan verilmiştir."
                ),
                "student_solution": "Şekil üzerinde: EAF=48°, AEF=66°. Alt tarafta: 108 - 66 = 42 buldum.",
                "writing_style": "messy_math"
            }
        }
    }
}

# 3. İleri Düzey Geometri ve Çokgen Sınav Kağıdı Çizim Motoru (PIL Canvas)
def draw_geometry_exam_page(student_name, active_q_id=None, show_all=True):
    """
    Renders an extremely premium, high-fidelity canvas simulation of the actual exam page
    containing four geometry questions (21, 22, 24, 25) with exact geometric shapes,
    sides, angles, parallel ticks and red handwritten mathematical calculations.
    """
    width, height = 1000, 900
    bg_color = (252, 251, 247) # warm cream paper
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Subtle blue grid lines
    grid_size = 30
    grid_color = (235, 242, 248)
    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
    # Red left margin
    draw.line([(85, 0), (85, height)], fill=(244, 160, 160), width=2)
    
    # Black/Grey dashed separator in the middle of double page
    mid_x = width // 2
    for y in range(0, height, 15):
        if y % 10 == 0:
            draw.line([(mid_x, y), (mid_x, y+8)], fill=(180, 185, 195), width=2)

    # Header
    draw.text((100, 15), "GEOMETRİ VE DÜZGÜN ÇOKGENLER SINAVI", fill=(99, 102, 241))
    draw.text((600, 15), f"Öğrenci: {student_name} | Sınıf: 12-A", fill=(60, 64, 70))
    draw.line([(100, 35), (900, 35)], fill=(210, 215, 220), width=1)

    # ------------------ Soru 21: Sol Üst ------------------
    if active_q_id is None or active_q_id == "21":
        draw.rectangle([(100, 50), (125, 75)], fill=(251, 191, 36)) # Orange badge
        draw.text((107, 55), "21", fill=(255, 255, 255))
        draw.text((135, 55), "Bir dış açısının ölçüsü 15 derece olan\ndüzgün çokgen kaç kenarlıdır?", fill=(20, 20, 20))
        
        # Student handwritten solution in red (#b32d2d)
        red_ink = (179, 45, 45)
        # Division box
        draw.text((140, 120), "360 | 15", fill=red_ink)
        draw.line([(175, 115), (175, 150)], fill=red_ink, width=2)
        draw.line([(175, 132), (200, 132)], fill=red_ink, width=2)
        draw.text((180, 135), "24", fill=red_ink)
        
        draw.text((220, 125), "24 kenarlıdır.", fill=red_ink)
        draw.line([(220, 142), (320, 142)], fill=red_ink, width=2) # underline

    # ------------------ Soru 22: Sol Alt ------------------
    if active_q_id is None or active_q_id == "22":
        draw.rectangle([(100, 420), (125, 445)], fill=(251, 191, 36))
        draw.text((107, 425), "22", fill=(255, 255, 255))
        draw.text((135, 425), "Bir düzgün çokgenin bir köşesinden çizilen tüm\nköşegenlerle oluşan üçgen sayısı 3'tür.\nBuna göre bu düzgün çokgenin bir iç açısının\nölçüsü kaç derecedir?", fill=(20, 20, 20))
        
        red_ink = (179, 45, 45)
        draw.text((140, 520), "n - 2 = 3  =>  n = 5 (Beşgen)", fill=red_ink)
        draw.text((140, 560), "İç açılar toplamı = 3 * 180 = 540 derece", fill=red_ink)
        
        draw.text((140, 600), "540 / 5 = 108", fill=red_ink)
        draw.line([(185, 595), (185, 625)], fill=red_ink, width=1)
        draw.line([(185, 610), (220, 610)], fill=red_ink, width=1)
        draw.text((190, 612), "108", fill=red_ink)
        
        draw.text((260, 600), "Cevap: 108", fill=red_ink)

    # ------------------ Soru 24: Sağ Üst (Şekilli) ------------------
    if active_q_id is None or active_q_id == "24":
        draw.rectangle([(530, 50), (555, 75)], fill=(251, 191, 36))
        draw.text((537, 55), "24", fill=(255, 255, 255))
        draw.text((565, 55), "Aşağıda bir dış açısının ölçüsü 45 derece olan\ndüzgün çokgen verilmiştir. Buna göre bu çokgenin\nA köşesinden çizilen köşegen sayısı kaçtır?", fill=(20, 20, 20))
        
        # Draw Octagon Section (A segment of it)
        # Center (700, 220)
        poly_color = (60, 65, 75)
        # Points of an octagon segment
        pts = [(620, 140), (620, 190), (660, 230), (720, 230), (760, 190), (760, 140)]
        draw.line([(620, 130), (620, 140)], fill=poly_color, width=2, joint="round")
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=poly_color, width=3)
        draw.line([(760, 140), (760, 130)], fill=poly_color, width=2)
        
        # Label A
        draw.text((720, 240), "A", fill=(20, 20, 20))
        
        # Exterior angle line at A
        draw.line([(720, 230), (790, 230)], fill=poly_color, width=1)
        # Curved line for angle
        draw.arc([(740, 205), (765, 230)], start=0, end=45, fill=poly_color, width=1)
        draw.text((770, 210), "45°", fill=(20, 20, 20))
        
        # Student red solution
        red_ink = (179, 45, 45)
        draw.text((565, 280), "360 / 45 = 8  =>  n = 8 (Sekizgen)", fill=red_ink)
        draw.text((565, 315), "Köşegen Sayısı = n - 3", fill=red_ink)
        draw.text((565, 345), "8 - 3 = 5 tanedir.", fill=red_ink)
        draw.line([(565, 362), (680, 362)], fill=red_ink, width=2)

    # ------------------ Soru 25: Sağ Alt (Çokgen & Üçgen Şekilli) ------------------
    if active_q_id is None or active_q_id == "25":
        draw.rectangle([(530, 420), (555, 445)], fill=(251, 191, 36))
        draw.text((537, 425), "25", fill=(255, 255, 255))
        draw.text((565, 425), "Şekilde ABCDE düzgün beşgen ve AFB eşkenar\nüçgendir. Buna göre m(DEF) açısı kaç derecedir?", fill=(20, 20, 20))
        
        # Draw Pentagon ABCDE and Equilateral AFB
        # Center (720, 580)
        cx, cy = 720, 580
        r_pent = 90
        # Compute pentagon points
        pent_pts = []
        for i in range(5):
            angle = -math.pi/2 + i * 2 * math.pi/5
            px = cx + r_pent * math.cos(angle)
            py = cy + r_pent * math.sin(angle)
            pent_pts.append((px, py))
            
        # Draw pentagon lines
        poly_color = (60, 65, 75)
        for i in range(5):
            draw.line([pent_pts[i], pent_pts[(i+1)%5]], fill=poly_color, width=3)
            
        # Points labels
        # 0: Top D, 1: Right C, 2: Bottom-Right B, 3: Bottom-Left A, 4: Left E
        draw.text((pent_pts[0][0], pent_pts[0][1]-18), "D", fill=poly_color)
        draw.text((pent_pts[1][0]+8, pent_pts[1][1]), "C", fill=poly_color)
        draw.text((pent_pts[2][0]+8, pent_pts[2][1]+8), "B", fill=poly_color)
        draw.text((pent_pts[3][0]-15, pent_pts[3][1]+8), "A", fill=poly_color)
        draw.text((pent_pts[4][0]-15, pent_pts[4][1]-10), "E", fill=poly_color)
        
        # AFB Equilateral Triangle (A is pent_pts[3], B is pent_pts[2])
        # Find F point inside pentagon
        # Since AFB is equilateral and on AB segment, F point is located above segment AB
        ax, ay = pent_pts[3]
        bx, by = pent_pts[2]
        mx, my = (ax + bx)/2, (ay + by)/2
        dx_ab, dy_ab = bx - ax, by - ay
        dist_ab = math.sqrt(dx_ab**2 + dy_ab**2)
        h_tri = dist_ab * math.sqrt(3)/2
        # Normal vector pointing inside
        nx, ny = -dy_ab/dist_ab, dx_ab/dist_ab
        fx, fy = mx + h_tri * nx, my + h_tri * ny
        
        # Draw AFB lines
        draw.line([pent_pts[3], (fx, fy)], fill=poly_color, width=3)
        draw.line([pent_pts[2], (fx, fy)], fill=poly_color, width=3)
        draw.text((fx-5, fy-18), "F", fill=poly_color)
        
        # Draw student red angles and marks on shapes (Simulating Shape OCR Reading!)
        red_ink = (179, 45, 45)
        # Equilateral marks inside AFB
        draw.text((fx-5, fy+20), "60°", fill=red_ink)
        # Pentagon angle markings
        draw.text((pent_pts[3][0]+15, pent_pts[3][1]-20), "48°", fill=red_ink)
        draw.text((pent_pts[4][0]+25, pent_pts[4][1]+10), "66°", fill=red_ink)
        draw.text((fx-20, fy-5), "66°", fill=red_ink)
        
        # Ticks on AE and AF to represent isosceles |AE| = |AF|
        # Tick on AE
        pt_ae_1 = ((pent_pts[4][0]+pent_pts[3][0])/2 - 3, (pent_pts[4][1]+pent_pts[3][1])/2 - 3)
        pt_ae_2 = ((pent_pts[4][0]+pent_pts[3][0])/2 + 3, (pent_pts[4][1]+pent_pts[3][1])/2 + 3)
        draw.line([pt_ae_1, pt_ae_2], fill=red_ink, width=2)
        # Tick on AF
        pt_af_1 = ((fx+pent_pts[3][0])/2 - 3, (fy+pent_pts[3][1])/2 - 3)
        pt_af_2 = ((fx+pent_pts[3][0])/2 + 3, (fy+pent_pts[3][1])/2 + 3)
        draw.line([pt_af_1, pt_af_2], fill=red_ink, width=2)

        # Student red calculations
        draw.text((550, 710), "AE = AF ikizkenar üçgendir.", fill=red_ink)
        draw.text((550, 740), "Tepe açısı m(EAF) = 108 - 60 = 48°", fill=red_ink)
        draw.text((550, 770), "Taban açısı m(AEF) = (180 - 48) / 2 = 66°", fill=red_ink)
        draw.text((550, 800), "Cevap m(DEF) = 108 - 66 = 42° buldum.", fill=red_ink)
        draw.line([(550, 822), (780, 822)], fill=red_ink, width=2)
        
    return img

def get_student_solution_image(student_id, question_no):
    """
    Fetches the dynamically created PIL Image for a student solution.
    Supports individual question crops or the entire exam page ("global").
    """
    student = MOCK_STUDENTS.get(student_id)
    if not student:
        return None
        
    if question_no == "global":
        # Return the entire simulated multi-question page!
        return draw_geometry_exam_page(student["name"], active_q_id=None, show_all=True)
    else:
        # Return a crop of the specific question
        full_page = draw_geometry_exam_page(student["name"], active_q_id=question_no, show_all=False)
        if question_no == "21":
            return full_page.crop((85, 40, 500, 390))
        elif question_no == "22":
            return full_page.crop((85, 410, 500, 860))
        elif question_no == "24":
            return full_page.crop((500, 40, 950, 390))
        elif question_no == "25":
            return full_page.crop((500, 410, 950, 860))
            
    return None
