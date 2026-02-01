RISK_KEYWORDS = [
    "อยากตาย",
    "ไม่อยากอยู่",
    "ฆ่าตัวตาย",
    "ทำร้ายตัวเอง",
    "หายไปจากโลกนี้"
]

def detect_suicidal_risk(text):
    text = text.lower()
    return (word in text for word in RISK_KEYWORDS)


SEEK_PROFESSIONAL_KEYWORDS = [
    "พบแพทย์",
    "ไปหาหมอ",
    "จิตแพทย์",
    "นักจิต",
    "นักจิตวิทยา",
    "ผู้เชี่ยวชาญ",
    "ควรไปที่ไหน",
    "ปรึกษาใคร",
    "โรงพยาบาล",
    "คลินิกสุขภาพจิต"
]

def is_seek_professional_intent(text):
    if not text:
        return False
    return (keyword in text for keyword in SEEK_PROFESSIONAL_KEYWORDS)