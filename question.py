import psycopg2
from dotenv import load_dotenv
import os   
import requests

# โหลดตัวแปรสภาพแวดล้อมจากไฟล์ .env
load_dotenv()   

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN") 
# ## สร้างตาราง 
# conn = psycopg2.connect(Supabase_URL)

# cur = conn.cursor()
# cur.execute("""
#     CREATE TABLE Dass_21_result(
#         id SERIAL PRIMARY KEY,
#         user_id TEXT,
#         name TEXT,
#         depression_score INT,
#         anxiety_score INT,
#         stress_score INT,
#         depression_level TEXT,
#         anxiety_level TEXT,
#         stress_level TEXT,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     )
# """)
# conn.commit()
# cur.close()
# conn.close()

# print("ตาราง Dass_21_result ถูกสร้างเรียบร้อยแล้ว")



## คำถาม DASS-21
DASS_21 = [
    {
        "text": "1. ฉันรู้สึกว่าการทำใจให้สงบเป็นเรื่องยาก แม้ในสถานการณ์ที่ควรจะผ่อนคลายแล้ว",
        "type": "S"
    },
    {
        "text": "2. ฉันมีอาการปากแห้งหรือคอแห้งบ่อย ๆ โดยเฉพาะในช่วงที่รู้สึกกังวลหรือตึงเครียด",
        "type": "A"
    },
    {
        "text": "3. ฉันแทบไม่รู้สึกดีหรือรู้สึกมีความสุขกับสิ่งต่าง ๆ เหมือนที่เคยเป็น",
        "type": "D"
    },
    {
        "text": "4. ฉันมีอาการหายใจผิดปกติ เช่น หายใจเร็ว หายใจไม่ทัน หรือรู้สึกอึดอัด ทั้งที่ไม่ได้ออกแรง",
        "type": "A"
    },
    {
        "text": "5. ฉันรู้สึกว่าการเริ่มต้นทำสิ่งต่าง ๆ หรือการลงมือทำอะไรใหม่ ๆ เป็นเรื่องยากกว่าปกติ",
        "type": "D"
    },
    {
        "text": "6. ฉันมักตอบสนองต่อสถานการณ์ต่าง ๆ รุนแรงหรือไวเกินไปกว่าที่ควรจะเป็น",
        "type": "S"
    },
    {
        "text": "7. ฉันรู้สึกว่าร่างกายบางส่วนมีอาการสั่น เช่น มือสั่น หรือขาสั่น แม้ไม่ได้ตั้งใจ",
        "type": "A"
    },
    {
        "text": "8. ฉันรู้สึกว่าการวิตกกังวลหรือความเครียดใช้พลังใจและพลังร่างกายของฉันไปมาก",
        "type": "S"
    },
    {
        "text": "9. ฉันมักกังวลกับเหตุการณ์ที่อาจเกิดขึ้น และกลัวว่าจะทำให้ตัวเองรู้สึกอับอายหรือตื่นกลัว",
        "type": "A"
    },
    {
        "text": "10. ฉันรู้สึกว่าชีวิตของตัวเองขาดเป้าหมาย หรือไม่ค่อยเห็นทิศทางในอนาคต",
        "type": "D"
    },
    {
        "text": "11. ฉันรู้สึกกระวนกระวาย ใจไม่ค่อยนิ่ง หรือรู้สึกเหมือนต้องขยับตัวตลอดเวลา",
        "type": "S"
    },
    {
        "text": "12. ฉันรู้สึกว่าการผ่อนคลายร่างกายหรือจิตใจของตัวเองเป็นเรื่องที่ทำได้ยาก",
        "type": "S"
    },
    {
        "text": "13. ฉันรู้สึกเศร้า เหงา หรือหดหู่ใจ โดยไม่ค่อยรู้สาเหตุที่ชัดเจน",
        "type": "D"
    },
    {
        "text": "14. ฉันรู้สึกหงุดหงิดหรือทนไม่ได้ เมื่อมีอะไรมาขัดจังหวะสิ่งที่ฉันกำลังทำอยู่",
        "type": "S"
    },
    {
        "text": "15. ฉันมีความรู้สึกเหมือนจะตื่นตระหนก หรือควบคุมอาการของตัวเองได้ยาก",
        "type": "A"
    },
    {
        "text": "16. ฉันรู้สึกไม่ค่อยมีแรง ไม่มีความกระตือรือร้น หรือไม่ค่อยอยากทำสิ่งต่าง ๆ เหมือนเดิม",
        "type": "D"
    },
    {
        "text": "17. ฉันรู้สึกว่าตัวเองไม่มีคุณค่า หรือมองไม่เห็นคุณค่าของตัวเอง",
        "type": "D"
    },
    {
        "text": "18. ฉันรู้สึกฉุนเฉียว หงุดหงิด หรือโมโหได้ง่ายกว่าปกติ",
        "type": "S"
    },
    {
        "text": "19. ฉันรับรู้ถึงการเต้นของหัวใจ แม้ในตอนที่ไม่ได้ออกแรง เช่น รู้สึกว่าหัวใจเต้นเร็ว หรือเต้นไม่เป็นจังหวะ",
        "type": "A"
    },
    {
        "text": "20. ฉันรู้สึกกลัวหรือหวาดระแวง ทั้งที่ไม่สามารถระบุเหตุผลได้ชัดเจน",
        "type": "A"
    },
    {
        "text": "21. ฉันรู้สึกว่าชีวิตของตัวเองไม่มีความหมาย หรือไม่เห็นคุณค่าของการมีชีวิตอยู่",
        "type": "D"
    },
]


DASS_choices = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3
}

##รวมผลคะแนน
def summaryScore(score_list):
    result = {"D":0 , "S":0 , "A":0} 
    for item in score_list:
        result[item["type"]] += item["score"]
    return result

## คำนวณระดับความเสี่ยง
def get_level(category, score):
    s = score 
    if category == "D":
        if s <= 4: return "ปกติ"
        elif s <= 6: return "เล็กน้อย"
        elif s <= 10: return "ปานกลาง"
        elif s <= 13: return "รุนแรง"
        else: return "รุนแรงมาก"
    elif category == "A":
        if s <= 3: return "ปกติ"
        elif s <= 5: return "เล็กน้อย"
        elif s <= 7: return "ปานกลาง"
        elif s <= 9: return "รุนแรง"
        else: return "รุนแรงมาก"
    elif category == "S":
        if s <= 7: return "ปกติ"
        elif s <= 9: return "เล็กน้อย"
        elif s <= 12: return "ปานกลาง"
        elif s <= 16: return "รุนแรง"
        else: return "รุนแรงมาก"



def save_dass_result(user_id, d, a, s):
    d_level = get_level("D", d)
    a_level = get_level("A", a)
    s_level = get_level("S", s)
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT    
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Dass_21_result (
            user_id, depression_score, anxiety_score, stress_score,
            depression_level, anxiety_level, stress_level
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, d, a, s, d_level, a_level, s_level))
    conn.commit()
    cur.close()
    conn.close()
    return d_level, a_level, s_level

def get_overall_risk(d_level, a_level, s_level):
    levels = [d_level, a_level, s_level]

    if "รุนแรงมาก" in levels or "รุนแรง" in levels:
        return "สูง"
    elif "ปานกลาง" in levels:
        return "ปานกลาง"
    else:
        return "ต่ำ"


def send_notification( user_id, d_level, a_level, s_level):
    overall = get_overall_risk(d_level, a_level, s_level)

    title = f"ผลประเมิน DASS-21 ({overall})"
    message = f"ระดับความเสี่ยงรวมของคุณ: {overall}\n"
    message += f"- ซึมเศร้า (D): {d_level}\n"
    message += f"- วิตกกังวล (A): {a_level}\n"
    message += f"- ความเครียด (S): {s_level}"

    payload = {
        "line_user_id": user_id,  
        "type": "DASS_RESULT",
        "title": title,
        "message": message
    }

    requests.post("https://appointment-website-nine.vercel.app/api/system/notifications/dass-21", json=payload)
