import time

from dass.question import (
    DASS_21,
    DASS_choices,
    summaryScore,
    save_dass_result,
    get_level,
    send_notification,
    check_dass_cooldown,
    log_dass_taken,
    can_use_override,
    save_dass_answer,
)
from consent import check_profile, save_profile
from validation import is_valid_fullname, is_valid_phone, is_valid_student_id
from line.line_messaging import reply_message
from line.line_ui import send_dass_consent, send_dass_repeat, reply_dass_question, send_dass_result_flex


def start_dass_flow(user_id, user_states):
    user_states[user_id] = {"awaiting_dass_consent": True}


# ผู้ใช้กด "ยืนยันทำซ้ำ" หลังโดน cooldown กัน
def handle_repeat_confirmation(user_id, reply_token, user_states):
    cooldown, _ = check_dass_cooldown(user_id)

    if not cooldown:
        reply_message(reply_token, "ขณะนี้คุณสามารถทำแบบประเมินได้ตามปกติ สามารถเลือกที่ริชเมนู 'ทำแบบประเมิน' ได้เลย")
        return

    if not can_use_override(user_id):
        reply_message(
            reply_token,
            "คุณได้ใช้สิทธิ์ทำซ้ำไปแล้ว\n"
            "สามารถทำซ้ำได้อีกครั้งใน 24 ชั่วโมง"
        )
        return

    # อนุญาต override
    start_dass_flow(user_id, user_states)
    send_dass_consent(reply_token)


# ผู้ใช้พิมพ์ "ทำแบบประเมิน" / "แบบประเมิน" / "เริ่มแบบประเมิน"
def handle_start_request(user_id, reply_token, user_states):
    cooldown, days_left = check_dass_cooldown(user_id)

    if cooldown:
        send_dass_repeat(
            reply_token,
            f"คุณเพิ่งทำแบบประเมินไป\n"
            f"สามารถทำซ้ำได้อีกครั้งในอีก {days_left} วัน\n"
            "แนะนำให้เว้นระยะอย่างน้อย 1 สัปดาห์\n\n"
            "คุณต้องการทำอย่างไรต่อ?"
        )
        return

    start_dass_flow(user_id, user_states)
    send_dass_consent(reply_token)


# จัดการขอความยินยอมบันทึกผล + กรอกโปรไฟล์ (ชื่อ/รหัสนักศึกษา/เบอร์) ก่อนเริ่มคำถามข้อแรก
# คืนค่า True ถ้าข้อความนี้ถูกจัดการแล้ว (ผู้เรียกควร return ทันที), False ถ้าไม่ใช่ขั้นตอนนี้
def handle_onboarding_and_consent(user_id, user_text, reply_token, user_states, user_info):
    state = user_states.get(user_id)
    if state is None:
        return False

    if state.get("awaiting_dass_consent"):
        if user_text == "ยินยอมบันทึกผล":  # ยินยอมบันทึก DASS
            state.pop("awaiting_dass_consent", None)
            state["dass_consent"] = True

            if not check_profile(user_id):
                state["awaiting_name"] = True
                reply_message(
                    reply_token,
                    "ก่อนเริ่มแบบประเมิน กรุณากรอกข้อมูลเล็กน้อย\n\nพิมพ์ชื่อ-นามสกุลของคุณ:"
                )
                # ต้องกรอกข้อมูลส่วนตัวก่อน
                return True

            # ถ้ามี profile แล้ว → เริ่ม DASS ได้เลย
            state.update({"index": 0, "scores": []})

            #  แสดงคำถามข้อแรกทันที
            q = DASS_21[0]["text"]
            reply_dass_question(reply_token, f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
            return True

        elif user_text == "ไม่ยินยอมบันทึกผล":  # ไม่ยินยอมบันทึก
            state.pop("awaiting_dass_consent", None)
            state["dass_consent"] = False
            state["index"] = 0
            state["scores"] = []

            #  แสดงคำถามข้อแรกทันที
            q = DASS_21[0]["text"]
            reply_dass_question(reply_token, f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
            return True

        else:
            reply_message(reply_token, "กรุณาเลือกจากปุ่มที่แสดงด้านล่างเท่านั้น")
            return True

    # --- อยู่ในสถานะรอชื่อ ---
    if state.get("awaiting_name"):
        if not is_valid_fullname(user_text):
            reply_message(
                reply_token,
                "กรุณากรอกชื่อและนามสกุลให้ถูกต้อง (ตัวอักษรไทย และต้องมีอย่างน้อย 2 คำ ตัวอย่าง: สมชาย ใจดี)"
            )
            return True
        user_info[user_id] = {"name": user_text.strip()}
        state.pop("awaiting_name", None)
        state["awaiting_student_id"] = True
        reply_message(reply_token, "กรุณากรอกรหัสนักศึกษา 8 หลัก: ")
        return True

    # --- อยู่ในสถานะรอรหัสนักศึกษา ---
    if state.get("awaiting_student_id"):
        if not is_valid_student_id(user_text):
            reply_message(reply_token, "กรุณากรอกรหัสนักศึกษาให้ถูกต้อง (ต้องเป็นตัวเลข 8 หลัก)")
            return True

        # บันทึกรหัสนักศึกษา
        user_info[user_id]["student_id"] = user_text.strip()

        # ไปต่อ → ขอเบอร์โทร
        state.pop("awaiting_student_id", None)
        state["awaiting_phone"] = True
        reply_message(reply_token, "กรุณาพิมพ์เบอร์โทรศัพท์ของคุณ (ตัวเลขเท่านั้น):")
        return True

    # --- อยู่ในสถานะรอเบอร์ ---
    if state.get("awaiting_phone"):
        if not is_valid_phone(user_text):
            reply_message(reply_token, "กรุณากรอกเบอร์โทรให้ถูกต้อง (ตัวเลข 10 หลัก และขึ้นต้นด้วย 0 ตัวอย่าง: 0812345678)")
            return True
        if not user_text.isdigit() or len(user_text) < 9:
            reply_message(reply_token, "กรุณากรอกเบอร์โทรให้ถูกต้อง (10 หลัก)")
            return True

        # บันทึกข้อมูล
        user_info[user_id]["phone"] = user_text.strip()
        save_profile(user_id, user_info[user_id]["name"],
                     user_info[user_id]["phone"],
                     user_info[user_id]["student_id"])

        # เคลียร์สถานะรับข้อมูลส่วนตัว
        state["index"] = 0
        state["scores"] = []

        # ลบเฉพาะ flag ที่ไม่ใช้แล้ว
        state.pop("awaiting_phone", None)
        state.pop("awaiting_student_id", None)
        state.pop("awaiting_name", None)

        # เริ่มทำแบบประเมิน
        q = DASS_21[0]["text"]
        reply_dass_question(reply_token, f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
        return True

    return False


# ผู้ใช้กำลังอยู่ระหว่างตอบคำถามทีละข้อ (state มี "index") — เรียกเมื่อแน่ใจแล้วว่า "index" อยู่ใน state
def handle_answer(user_id, user_text, reply_token, user_states):
    state = user_states[user_id]
    index = state["index"]

    if user_text in DASS_choices:
        score = DASS_choices[user_text]
        if index < len(DASS_21):
            q_type = DASS_21[index]["type"]
            state["scores"].append({"score": score, "type": q_type})
            index += 1
            state["index"] = index

        if index < len(DASS_21):
            next_q = DASS_21[index]["text"]
            reply_dass_question(reply_token, f"{next_q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
            return

        summary = summaryScore(state["scores"])
        d, a, s = summary['D'], summary['A'], summary['S']

        # ถ้ามีค่า dass_consent ใน state แสดงว่าผู้ใช้ได้ตอบเรื่องการยินยอมไว้แล้ว → ใช้ค่านั้นในการตัดสินใจว่าจะบันทึกผลหรือไม่
        dass_consent = state.get("dass_consent", False)

        if dass_consent:
            try:
                result_id, d_level, a_level, s_level = save_dass_result(user_id, d, a, s)

                for i, answer in enumerate(state["scores"]):
                    save_dass_answer(
                        result_id=result_id,
                        question_number=i + 1,
                        question_type=answer["type"],
                        score=answer["score"]
                    )
                send_notification(user_id, d_level, a_level, s_level)

            except Exception as e:
                print("Error saving DASS answers:", e)
        else:
            d_level = get_level("D", d)
            a_level = get_level("A", a)
            s_level = get_level("S", s)

            state["assessment_context"] = {
                "D": d,
                "A": a,
                "S": s,
                "D_level": d_level,
                "A_level": a_level,
                "S_level": s_level,
                "timestamp": time.time()
            }

        send_dass_result_flex(reply_token, d, a, s, d_level, a_level, s_level)

        try:
            log_dass_taken(user_id)
        except Exception as e:
            print("Log error:", e)

        #  ล้าง state ให้ครบก่อน
        state.pop("index", None)
        state.pop("scores", None)
        state.pop("dass_consent", None)

    else:
        current_q = DASS_21[state["index"]]["text"]
        reply_dass_question(reply_token, f"กรุณาตอบเป็นตัวเลขที่กำหนดเท่านั้นนะ\n\nคำถาม:\n{current_q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")


# ดึงบริบทผลประเมินล่าสุด (ถ้ายังไม่หมดอายุใน 1 ชม.) สำหรับใช้ประกอบ prompt ของ LLM ทั่วไป
def get_assessment_context_for_prompt(user_id, user_states):
    state = user_states.get(user_id)
    if not state or "assessment_context" not in state:
        return None

    ac = state["assessment_context"]

    # TTL: ล้าง context ถ้าเก่าเกิน 1 ชั่วโมง
    if time.time() - ac["timestamp"] > 3600:
        state.pop("assessment_context", None)
        return None

    return (
        "ผลการประเมิน DASS-21 ล่าสุดของผู้ใช้ (ใช้เพื่อช่วยตอบเท่านั้น):\n"
        f"- ซึมเศร้า: {ac['D_level']}\n"
        f"- วิตกกังวล: {ac['A_level']}\n"
        f"- ความเครียด: {ac['S_level']}\n"
        "ข้อกำหนด:\n"
        "- ห้ามวินิจฉัย\n"
        "- ใช้น้ำเสียงอ่อนโยน ไม่ตีตรา\n"
    )
