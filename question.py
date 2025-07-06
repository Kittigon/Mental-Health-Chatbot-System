import psycopg2

# ## สร้างตาราง 
# conn = psycopg2.connect(
#     dbname = "mydb",
#     user = "admin",
#     password = "1234" ,
#     host = "localhost" ,
#     port  = "5432"
# )

# cur = conn.cursor()
# cur.execute("""
#     CREATE TABLE Dass_21_result(
#         id SERIAL PRIMARY KEY,
#         user_id TEXT,
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



## คำถาม DASS-21
DASS_21 = [
    {"text": "1. ฉันรู้สึกยากที่จะสงบจิตใจ", "type": "S"},
    {"text": "2. ฉันรู้สึกปากแห้งคอแห้ง", "type": "A"},
    {"text": "3. ฉันแทบไม่รู้สึกดี ๆ อะไรบ้างเลย", "type": "D"},
    {"text": "4. ฉันมีอาการหายใจผิดปกติ (เช่นหายใจเร็วเกินเหตุ หายใจไม่ทันแม้ว่าจะไม่ได้ออกแรง)", "type": "A"},
    {"text": "5. ฉันพบว่ามันยากที่จะคิดริเริ่มสิ่งใดสิ่งหนึ่ง", "type": "D"},
    {"text": "6. ฉันมีแนวโน้มที่จะตอบสนองเกินเหตุต่อสถานการณ์", "type": "S"},
    {"text": "7. ฉันรู้สึกว่าร่างกายบางส่วนสั่นผิดปกติ (เช่น มือสั่น)", "type": "A"},
    {"text": "8. ฉันรู้สึกเสียพลังไปมากกับการวิตกกังวล", "type": "S"},
    {"text": "9. ฉันรู้สึกกังวลกับเหตุการณ์ที่อาจทำให้ฉันรู้สึกตื่นกลัวและกระทำบางสิ่งที่น่าอับอาย", "type": "A"},
    {"text": "10. ฉันไม่มีเป้าหมายในชีวิต", "type": "D"},
    {"text": "11. ฉันรู้สึกกระวนกระวายใจ", "type": "S"},
    {"text": "12. ฉันยากที่จะผ่อนคลายตัวเอง", "type": "S"},
    {"text": "13. ฉันรู้สึกจิตใจเหงาหงอยเศร้าซึม", "type": "D"},
    {"text": "14. ฉันรู้สึกทนไม่ได้เวลามีอะไรมาขัดขวางสิ่งที่ฉันกำลังทำอยู่", "type": "S"},
    {"text": "15. ฉันรู้สึกคล้ายจะมีอาการตื่นตระหนก", "type": "A"},
    {"text": "16. ฉันรู้สึกไม่มีความกระตือรือร้นต่อสิ่งใด", "type": "D"},
    {"text": "17. ฉันรู้สึกเป็นคนไม่มีคุณค่า", "type": "D"},
    {"text": "18. ฉันรู้สึกค่อนข้างฉุนฉียวง่าย", "type": "S"},
    {"text": "19. ฉันรับรู้ถึงการทำงานของหัวใจแม้ในตอนที่ฉันไม่ได้ออกแรง (เช่น รู้สึกว่าหัวใจเต้นเร็วขึ้น หรือเต้นไม่เป็นจังหวะ)", "type": "A"},
    {"text": "20. ฉันรู้สึกกลัวโดยไม่มีเหตุผล", "type": "A"},
    {"text": "21. ฉันรู้สึกว่าชีวิตไม่มีความหมาย", "type": "D"},

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
        dbname = "mydb",
        user = "admin",
        password = "1234" ,
        host = "localhost" ,
        port  = "5432"
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



