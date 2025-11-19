def is_valid_fullname(name):
    name = name.strip()

    # ห้ามว่าง
    if len(name) == 0:
        return False

    # แยกคำ (อย่างน้อยต้องมี 2 คำ เช่น ชื่อ + นามสกุล)
    parts = name.split()

    if len(parts) < 2:
        return False

    # ตรวจสอบทุกคำว่ามีเฉพาะอักษรไทยหรืออังกฤษ
    import re
    for part in parts:
        if not re.match(r'^[ก-๙A-Za-z]+$', part):
            return False

    # ไม่ควรยาวเกินไป
    if len(name) > 60:
        return False

    return True


def is_valid_phone(phone):
    phone = phone.strip()

    # ต้องเป็นตัวเลขล้วน
    if not phone.isdigit():
        return False

    # ต้องยาว 9–10 หลัก (ตามมาตรฐานไทย)
    if len(phone) not in [9, 10]:
        return False
    
    # เบอร์ไทยเริ่มด้วย 0
    if not phone.startswith("0"):
        return False

    return True


# ตรวจสอบขความยาวของข้อความ
def is_valid_message_length(message, max_length=200):
    if len(message) > max_length:
        return False
    return True