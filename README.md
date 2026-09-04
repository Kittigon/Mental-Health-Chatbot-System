# Conn-Line Python — LINE Chatbot สำหรับให้คำปรึกษาสุขภาพจิต

แชทบอทบน LINE ที่ใช้ LLM (ผ่าน OpenRouter) ร่วมกับ RAG (PostgreSQL + pgvector) เพื่อให้คำปรึกษา
รองรับแบบประเมิน DASS-21, ระบบขอความยินยอม (consent), การทักทายอัตโนมัติตามช่วงเวลา, การแจ้งเตือนให้ทำแบบประเมินซ้ำ,
และการตรวจจับความเสี่ยงด้านความปลอดภัย (เช่น ข้อความที่บ่งชี้ความเสี่ยงต่อการทำร้ายตนเอง)

## โครงสร้างโปรเจกต์

```
connline_python/
├── main.py               # Flask entry point, webhook, orchestration หลักของบทสนทนา
├── consent.py            # ขอ/บันทึกความยินยอม, ข้อมูลโปรไฟล์ผู้ใช้ (user_consent)
├── greeting.py           # ทักทายอัตโนมัติตามช่วงเวลา + ตัวตั้งเวลา (APScheduler)
├── tone.py               # บันทึก/ดึงสไตล์โทนเสียงการตอบของบอทต่อผู้ใช้
├── tone_config.py        # คำอธิบาย/พรอมต์ของแต่ละโทนเสียง
├── history.py            # บันทึก/โหลดประวัติการสนทนา (chat_history)
├── safety.py             # ตรวจจับความเสี่ยงในข้อความผู้ใช้ (เช่น ความคิดทำร้ายตนเอง)
├── validation.py         # ตรวจสอบความถูกต้องของ input (ชื่อ, เบอร์โทร, รหัสนักศึกษา ฯลฯ)
├── insertdoc.py          # สคริปต์ one-off สำหรับแปลงไฟล์ CSV เป็น embedding แล้ว insert ลงตาราง documents
│
├── core/                 # โครงสร้างพื้นฐานที่ใช้ร่วมกันทั้งโปรเจกต์
│   ├── db.py             #   connection pool กลาง (psycopg2) + context manager get_cursor()
│   ├── llm_client.py     #   เรียก LLM ผ่าน OpenRouter พร้อม multi-model fallback + retry/backoff
│   ├── prompt_builder.py #   ประกอบ prompt (system role, กติกา, โทน, context) ที่ส่งให้ LLM
│   └── query_postgresql.py  # ค้นหาเอกสาร (RAG) ด้วย vector similarity ใน PostgreSQL (pgvector)
│
├── line/                 # การสื่อสารกับ LINE Messaging API
│   ├── line_messaging.py #   client กลาง: reply/push message, ดึงโปรไฟล์, loading animation
│   └── line_ui.py        #   Flex message / quick-reply builder ทั้งหมด (เมนู, ผลประเมิน DASS ฯลฯ)
│
├── dass/                 # แบบประเมิน DASS-21
│   ├── question.py       #   คำถาม 21 ข้อ, คำนวณคะแนน/ระดับ, บันทึกผล/log ลง DB
│   └── dass_reminder.py  #   ตรวจสอบและส่งแจ้งเตือนให้ทำ DASS-21 ซ้ำ
│
├── flows/                # ตัว dispatch ข้อความของแต่ละ conversation flow (เรียกจาก main.py)
│   ├── dass_flow.py      #   ขั้นตอนขอความยินยอม/กรอกโปรไฟล์/ตอบคำถามทีละข้อของ DASS-21
│   └── settings_flow.py  #   เมนูตั้งค่า, toggle consent/greeting, เลือกสไตล์, คู่มือการใช้งาน
│
├── public/               # ไฟล์ข้อมูลตั้งต้น (Data.csv) สำหรับสร้างฐานความรู้ RAG
├── requirements.txt      # รายการไลบรารีหลักที่ต้องติดตั้ง
├── .env                  # ตัวแปรสภาพแวดล้อม (ไม่ควร commit ค่าจริงขึ้น git)
└── .github/workflows/    # GitHub Actions (cron ping เพื่อกัน service บน Render sleep)
```

โมดูลที่อยู่ root (`consent.py`, `greeting.py`, `tone.py`, `history.py`, `safety.py`, `validation.py`,
`tone_config.py`) เป็นโดเมนโลจิกที่ยังไม่มีเพื่อนบ้านมากพอจะแยกโฟลเดอร์ ส่วน `core/`, `line/`, `dass/`, `flows/`
คือกลุ่มที่แยกออกมาเพราะมีไฟล์ที่เกี่ยวข้องกันมากกว่า 1 ไฟล์

## สิ่งที่ต้องมีก่อนติดตั้ง (Prerequisites)

- Python 3.10+ และ `pip`
- ฐานข้อมูล PostgreSQL ที่ติดตั้ง extension `pgvector` (ใช้เก็บ embedding สำหรับ RAG)
- LINE Official Account + LINE Messaging API channel (Channel Access Token, Channel Secret)
- OpenRouter API key (ใช้เรียก LLM หลัก)
- Cloudflare Workers AI account (ใช้สร้าง embedding ผ่านโมเดล `@cf/baai/bge-m3`)

## การติดตั้ง (Installation)

1. Clone โปรเจกต์และเข้าไปยังโฟลเดอร์:
   ```bash
   git clone <repo-url>
   cd connline_python
   ```

2. สร้างและเปิดใช้งาน virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. ติดตั้งไลบรารีที่จำเป็น:
   ```bash
   pip install -r requirements.txt
   ```

   > หมายเหตุ: `insertdoc.py` (สคริปต์นำเข้าเอกสารครั้งแรก) ใช้ไลบรารีเพิ่มเติมที่ไม่ได้อยู่ใน
   > `requirements.txt` ได้แก่ `langchain`, `langchain-community` — ให้ติดตั้งแยกเฉพาะเมื่อจะรันสคริปต์นี้:
   > ```bash
   > pip install langchain langchain-community
   > ```
   >
   > `requirements.txt` ปัจจุบันยังมี `google-generativeai` ค้างอยู่จากตอนที่เคยเรียก Gemini โดยตรง —
   > โค้ดปัจจุบันย้ายไปเรียก LLM ผ่าน OpenRouter ทั้งหมดแล้ว (`core/llm_client.py`) จึง**ไม่ได้ใช้ไลบรารีนี้จริง**
   > พิจารณาลบออกจาก `requirements.txt` ได้หากต้องการลด dependency

4. ตั้งค่าไฟล์ `.env` ที่ root ของโปรเจกต์ (ดูรายละเอียดตัวแปรด้านล่าง)

5. เตรียมตารางในฐานข้อมูล (ดูหัวข้อ "การตั้งค่าฐานข้อมูล")

## ตัวแปรสภาพแวดล้อม (Environment Variables)

สร้างไฟล์ `.env` โดยอ้างอิงตัวแปรต่อไปนี้:

| ตัวแปร | คำอธิบาย |
|---|---|
| `LINE_ACCESS_TOKEN` | Channel access token ของ LINE Messaging API (ใช้ reply/push message) |
| `LINE_CHANNEL_SECRET` | Channel secret สำหรับตรวจสอบลายเซ็น webhook (`X-Line-Signature`) — **บังคับต้องตั้งถูกต้อง** มิฉะนั้น LINE จะยิง webhook เข้ามาไม่ได้เลย |
| `DATABASE_URL` | Connection string แบบเต็มของ PostgreSQL (ใช้โดย `insertdoc.py`) |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | ค่าการเชื่อมต่อ PostgreSQL แยกฟิลด์ (ใช้โดย `core/db.py` connection pool กลาง) |
| `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` | สำหรับเรียก Cloudflare Workers AI เพื่อสร้าง embedding |
| `OPEN_ROUTER_API_KEY` / `OPEN_ROUTER_API_URL` | สำหรับเรียก LLM ผ่าน OpenRouter (`core/llm_client.py`) |

⚠️ ห้าม commit ค่า `.env` จริงขึ้น git — ให้ตรวจสอบว่ามีอยู่ใน `.gitignore` แล้ว

## การตั้งค่าฐานข้อมูล (Database Setup)

ตารางหลักที่ต้องมี (สร้างด้วยตนเองผ่าน `psql`/GUI — SQL อ้างอิงตามด้านล่าง):

```sql
-- โปรไฟล์และความยินยอมของผู้ใช้
CREATE TABLE user_consent (
    line_user_id      VARCHAR(100) PRIMARY KEY,
    name              TEXT,
    phone             TEXT,
    student_id        VARCHAR(20),
    consent           BOOLEAN,
    granted_at        TIMESTAMP,
    allow_greeting    BOOLEAN DEFAULT FALSE,
    last_greeted      TIMESTAMP,
    tone_style        VARCHAR(20) DEFAULT 'friendly',
    last_dass_reminder TIMESTAMPTZ
);

-- ประวัติการสนทนา
CREATE TABLE chat_history (
    id            SERIAL PRIMARY KEY,
    line_user_id  VARCHAR(100) NOT NULL,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL,
    timestamp     TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (line_user_id) REFERENCES user_consent(line_user_id) ON DELETE CASCADE
);

-- ผลคะแนนแบบประเมิน DASS-21 ต่อครั้ง
CREATE TABLE dass_21_result (
    id                 SERIAL PRIMARY KEY,
    user_id            TEXT,
    depression_score   INT,
    anxiety_score      INT,
    stress_score       INT,
    depression_level   TEXT,
    anxiety_level      TEXT,
    stress_level       TEXT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- บันทึกเวลาที่ผู้ใช้ทำแบบประเมิน (ใช้คุม cooldown)
CREATE TABLE dass_21_log (
    id         SERIAL PRIMARY KEY,
    user_id    VARCHAR(100) NOT NULL,
    taken_at   TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_consent(line_user_id) ON DELETE CASCADE
);

-- คำตอบรายข้อของแต่ละครั้งที่ทำแบบประเมิน
CREATE TABLE dass_21_answer (
    id              SERIAL PRIMARY KEY,
    result_id       INT NOT NULL,
    question_number INT NOT NULL,
    question_type   VARCHAR(1) NOT NULL, -- D / A / S
    score           INT NOT NULL,
    FOREIGN KEY (result_id) REFERENCES dass_21_result(id) ON DELETE CASCADE
);

-- เนื้อหาความรู้ + เวกเตอร์ embedding สำหรับ RAG (ต้องเปิด extension pgvector ก่อน)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id        SERIAL PRIMARY KEY,
    content   TEXT,
    embedding vector(1024)
);
```

> หมายเหตุ: ก่อนหน้านี้ SQL ชุดนี้เคยอยู่เป็นคอมเมนต์กระจายอยู่ในซอร์สโค้ด (`consent.py`, `history.py`,
> `dass/question.py`, `insertdoc.py`) แต่ถูกลบออกระหว่างการทำความสะอาดโค้ด (dead code cleanup) แล้ว
> ตอนนี้ README นี้คือแหล่งอ้างอิง schema เดียวของโปรเจกต์

ขั้นตอน:
1. เปิด extension `pgvector` ในฐานข้อมูล PostgreSQL
2. รันคำสั่ง `CREATE TABLE` ด้านบนทั้งหมด
3. นำเข้าข้อมูลความรู้เริ่มต้นจาก `public/Data.csv` เข้าตาราง `documents`:
   ```bash
   python insertdoc.py
   ```
   สคริปต์นี้จะ chunk ข้อความ, เรียก Cloudflare Workers AI เพื่อสร้าง embedding และ insert ลงตาราง
   `documents` โดยอัตโนมัติ

## การรันแอปพลิเคชัน (Running the App)

### รันแบบ Development (local)

```bash
python main.py
```

แอปจะรันที่ `http://0.0.0.0:5000` (Flask dev server) พร้อมเปิด background scheduler
(`greeting.start_scheduler`) สำหรับทักทายอัตโนมัติและแจ้งเตือน DASS-21

### รันแบบ Production

ใช้ Gunicorn (มีอยู่ใน `requirements.txt` แล้ว):

```bash
gunicorn main:app --bind 0.0.0.0:5000
```

โปรเจกต์นี้ deploy อยู่บน Render (`https://conn-line-python.onrender.com`) และมี GitHub Actions
(`.github/workflows/main.yml`) ที่ ping endpoint ทุก 15 นาทีเพื่อป้องกัน service sleep บน Render free tier

> ⚠️ ถ้ารันด้วย Gunicorn หลาย worker (`-w` มากกว่า 1) ควรทราบว่า state ระหว่างทำแบบประเมิน DASS-21
> (`user_states` ใน `main.py`) เก็บเป็น in-memory dict ต่อ process — ผู้ใช้ที่ทำแบบประเมินค้างอยู่อาจเจอ
> worker คนละตัวในแต่ละ request ทำให้ flow ขาดตอนได้ แนะนำให้รันด้วย 1 worker จนกว่าจะย้าย state ไปเก็บใน
> Redis/DB ร่วมกัน

### เชื่อมต่อกับ LINE

1. ตั้งค่า Webhook URL ใน LINE Developers Console ให้ชี้ไปที่ `https://<your-domain>/webhook`
2. เปิดใช้งาน "Use webhook" และปิด auto-reply ของ LINE Official Account
3. ระหว่างพัฒนา local สามารถใช้ ngrok หรือเครื่องมือ tunnel อื่นเพื่อ expose พอร์ต 5000 ออกสู่อินเทอร์เน็ต

> ความปลอดภัย: `main.py` ตรวจสอบลายเซ็น (`X-Line-Signature`) ของทุก request ที่เข้ามาที่ `/webhook`
> ด้วย HMAC-SHA256 (`LINE_CHANNEL_SECRET`) แล้ว — request ที่ไม่มี signature หรือ signature ไม่ตรงจะถูก
> ปฏิเสธด้วย HTTP 400 ทันที **ตรวจสอบให้แน่ใจว่า `LINE_CHANNEL_SECRET` ใน production ตรงกับ Channel secret
> ใน LINE Developers Console ก่อน deploy** ไม่เช่นนั้นบอทจะไม่ตอบสนอง request ใดๆ จาก LINE เลย

## Endpoints หลัก

| Method | Path | คำอธิบาย |
|---|---|---|
| `POST` | `/webhook` | รับ event จาก LINE Messaging API (ข้อความ, follow, postback ฯลฯ) — ตรวจสอบ signature ก่อนประมวลผลทุกครั้ง |
| `GET` | `/ping` | Health check endpoint สำหรับ uptime monitoring |

## ขั้นตอนการใช้งาน (User Flow บน LINE)

1. ผู้ใช้เพิ่มบอทเป็นเพื่อน (`follow` event) → บอทขอความยินยอมในการสนทนา (`line/line_ui.py`)
2. เมื่อยินยอมแล้ว หากทำแบบประเมิน DASS-21 โดยยังไม่มีโปรไฟล์ บอทจะขอข้อมูลเบื้องต้น (ชื่อ, เบอร์โทร,
   รหัสนักศึกษา) ผ่าน `flows/dass_flow.py` + `consent.py`
3. ผู้ใช้สามารถพูดคุยได้อิสระ — บอทประกอบ prompt (`core/prompt_builder.py`) โดยใช้ประวัติแชท + เอกสารที่เกี่ยวข้อง
   (ค้นด้วย `core/query_postgresql.py`) แล้วส่งให้ LLM ผ่าน OpenRouter (`core/llm_client.py`) ตอบกลับ
   (ไล่ลองหลายโมเดลพร้อม retry หากโมเดลใดล้มเหลว)
4. ระหว่างสนทนา `safety.py` จะตรวจจับข้อความที่มีความเสี่ยง (เช่น แนวโน้มทำร้ายตนเอง) และปรับการตอบสนอง/แนะนำ
   ให้พบผู้เชี่ยวชาญ
5. ผู้ใช้สามารถขอทำแบบประเมิน DASS-21 ได้ (`dass/question.py` + `flows/dass_flow.py`) — ระบบขอความยินยอมแยก
   ก่อนบันทึกผล, คำนวณคะแนน, ระดับความเสี่ยง และแจ้งเตือนให้ทำซ้ำเมื่อครบกำหนด (`dass/dass_reminder.py`)
6. ผู้ใช้สามารถเลือกโทนเสียงการตอบของบอทและเปิด/ปิดการทักทายอัตโนมัติรายวันผ่านเมนูการตั้งค่า
   (`flows/settings_flow.py` → `tone.py` / `greeting.py`)

## การแก้ปัญหาเบื้องต้น (Troubleshooting)

- **เชื่อมต่อฐานข้อมูลไม่ได้**: ตรวจสอบค่า `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` ใน `.env`
  และตรวจสอบว่า PostgreSQL อนุญาต connection จาก IP ของเครื่องที่รัน
- **บอทไม่ตอบใน LINE เลย (ทุก event)**: ตรวจสอบก่อนว่า `LINE_CHANNEL_SECRET` ใน `.env` ตรงกับ Channel secret
  ใน LINE Developers Console หรือไม่ — ถ้าไม่ตรง ทุก request จะถูกปฏิเสธด้วย 400 ที่ signature check
  (ดู log ว่ามีข้อความ "Invalid Signature" ขึ้นถี่ๆ หรือไม่)
- **บอทไม่ตอบใน LINE**: ตรวจสอบว่า Webhook URL ตั้งค่าถูกต้องและ endpoint `/webhook` เข้าถึงได้จาก
  อินเทอร์เน็ต (ไม่ใช่แค่ localhost), ตรวจ log ของ Flask/Gunicorn
- **RAG ไม่คืนผลลัพธ์ที่เกี่ยวข้อง**: ตรวจสอบว่าตาราง `documents` มีข้อมูล และ extension `pgvector` เปิดใช้งานแล้ว
- **Error จาก Cloudflare Workers AI**: ตรวจสอบ `CLOUDFLARE_ACCOUNT_ID` และ `CLOUDFLARE_API_TOKEN` ว่ายังใช้งานได้
- **LLM ไม่ตอบ / ตอบข้อความ fallback ตลอด**: ตรวจสอบ `OPEN_ROUTER_API_KEY`/`OPEN_ROUTER_API_URL` และดู log
  `model ... ล้มเหลว → เปลี่ยนตัว` เพื่อดูว่าโมเดลไหนล้มเหลวในลิสต์ (`core/llm_client.py`)
