# chat.py — คุยกับโมเดล Vex GPT + บันทึกความจำเข้า API ในคำสั่งเดียว (รันใน Colab หลัง finetune.py)
#   ถามครั้งเดียว:     !python chat.py ข้อความที่ต้องการถาม
#   โหมดคุยต่อเนื่อง:   !python chat.py   (พิมพ์ exit เพื่อออก)
#   บันทึกความจำ:       ขึ้นต้นด้วย "จำไว้ว่า ..." หรือ "บันทึก ..."  (เซฟเข้า API ไม่เรียกโมเดล เร็วมาก)
#   ค้นเว็บก่อนตอบ:     ขึ้นต้นด้วย "ค้น " เช่น  ค้น Roblox TweenService วิธีใช้
#   ทุกครั้งที่ถาม จะดึงความจำที่เกี่ยวข้องจาก API มาให้โมเดลอัตโนมัติ
#   ตั้งค่าใน .env (โฟลเดอร์เดียวกัน, ห้ามอัปโหลดขึ้น GitHub):
#       VEX_KEY=รหัส API_KEY      VEX_URL=https://gpt-qc7w.vercel.app
#   ต้องมี search.py อยู่โฟลเดอร์เดียวกัน และ !pip install ddgs

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import warnings
from contextlib import ExitStack, nullcontext, redirect_stderr, redirect_stdout

_here = os.path.dirname(os.path.abspath(__file__))


# ───────────── ตั้งค่า (.env) ─────────────
def load_env():
    """อ่าน .env แบบง่าย ๆ (ไม่ต้องติดตั้งอะไร) ค่าที่ตั้งใน environment อยู่แล้วจะไม่ถูกทับ"""
    for folder in (_here, os.getcwd()):
        path = os.path.join(folder, ".env")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.removeprefix("export ").strip(), v.strip().strip('"').strip("'"))
        return


load_env()
VEX_URL = os.environ.get("VEX_URL", "https://gpt-qc7w.vercel.app").rstrip("/")
VEX_KEY = os.environ.get("VEX_KEY", "")
DEBUG = os.environ.get("CHAT_DEBUG") == "1"  # ดู log เต็ม:  !CHAT_DEBUG=1 python chat.py สวัสดี


# ───────────── ความจำ (API) ─────────────
def _api(path, payload=None, timeout=10):
    req = urllib.request.Request(
        VEX_URL + path,
        data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-api-key": VEX_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


SAVE_KEYS = ("จำไว้ว่า", "จำไว้", "บันทึก", "save")


def try_save(text):
    """ถ้าข้อความขึ้นต้นด้วยคำสั่งบันทึก → เซฟเข้า API แล้วคืนข้อความผลลัพธ์ (ไม่ใช่ → คืน None)"""
    t = text.strip()
    for key in SAVE_KEYS:
        if t.lower().startswith(key):
            fact = t[len(key):].strip(" :,")
            if not fact:
                return "ไม่มีข้อความให้บันทึก"
            if not VEX_KEY:
                return "ไม่พบ VEX_KEY ใส่ในไฟล์ .env เช่น  VEX_KEY=รหัสของคุณ"
            try:
                res = _api("/samples", {"prompt": "", "response": fact, "tag": "taught", "source": "chat"})
            except urllib.error.HTTPError as e:
                return "บันทึกไม่สำเร็จ: " + ("รหัสไม่ถูกต้อง (เช็ก VEX_KEY ใน .env)" if e.code == 401 else f"HTTP {e.code}")
            except Exception as e:
                return f"บันทึกไม่สำเร็จ: {e}"
            return "มีข้อความนี้อยู่แล้ว (ข้าม)" if res.get("duplicate") else f"✅ บันทึกแล้ว (id {res.get('id')})"
    return None


def recall(query):
    """ดึงความจำที่เกี่ยวข้องจาก API (ล้มเหลวเมื่อไหร่ก็ข้าม ไม่ให้การคุยพัง)"""
    if not VEX_KEY or not query.strip():
        return ""
    try:
        rows = _api("/recall?" + urllib.parse.urlencode({"q": query, "k": 5}), timeout=8)
    except Exception:
        return ""
    lines = []
    for r in rows:
        lines.append(f"- {r['prompt']} → {r['response']}" if r.get("prompt") else f"- {r['response']}")
    return "\n".join(lines)


# บันทึกความจำแบบครั้งเดียว: จบก่อนโหลดโมเดล (ไม่ต้องใช้ GPU)
if len(sys.argv) > 1:
    _msg = try_save(" ".join(sys.argv[1:]))
    if _msg is not None:
        print(_msg)
        sys.exit(0)

# ───────────── โมเดล ─────────────
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["UNSLOTH_COMPILE_DISABLE"] = "0"
warnings.filterwarnings("ignore")

ADAPTER = os.path.join(_here, "lora-th-coder")  # โฟลเดอร์ที่ finetune.py สร้างไว้

if not os.path.isdir(ADAPTER):
    sys.exit("ไม่พบโฟลเดอร์ lora-th-coder ต้องรัน  !python finetune.py  ก่อน")

# บุคลิกของ AI อ่านจากไฟล์ persona.txt (แก้ไฟล์นั้นได้เลย)
try:
    with open(os.path.join(_here, "persona.txt"), encoding="utf-8") as _f:
        PERSONA = _f.read().strip()
except OSError:
    PERSONA = "คุณคือผู้ช่วยเขียนโค้ดภาษาไทย พูดสั้น ตรงประเด็น ลงท้ายด้วย 'ครับ'"


def quiet():
    if DEBUG:
        return nullcontext()
    stack = ExitStack()
    null = stack.enter_context(open(os.devnull, "w"))
    stack.enter_context(redirect_stdout(null))
    stack.enter_context(redirect_stderr(null))
    return stack


def _check_gpu():
    import torch

    if not torch.cuda.is_available():
        sys.exit("ไม่พบ GPU ไปที่ Runtime > Change runtime type > T4 GPU แล้วรันใหม่")


_check_gpu()


def show():
    if not DEBUG:
        print("AI is thinking...", end="", flush=True)


def hide():
    if not DEBUG:
        print("\r\033[K", end="", flush=True)


show()

# ซ่อนข้อความของ Unsloth/torch ตอนโหลดโมเดล (ถ้าอยากดู log ให้ลบบรรทัด with ออก)
with quiet():
    from unsloth import FastLanguageModel
    from search import build_prompt

    model, tok = FastLanguageModel.from_pretrained(ADAPTER, load_in_4bit=True)
    FastLanguageModel.for_inference(model)


def prep(text):
    if text.startswith("ค้น "):
        return build_prompt(text[4:].strip())
    return text


def ask(history, query=""):
    system = PERSONA
    mem = recall(query)
    if mem:
        system += "\n\nความรู้ที่เคยถูกสอนไว้ (ใช้ตอบถ้าเกี่ยวข้อง ถ้าไม่เกี่ยวให้ไม่ต้องพูดถึง):\n" + mem
    messages = [{"role": "system", "content": system}] + history
    ids = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    ).to("cuda")
    with quiet():
        out = model.generate(
            ids, max_new_tokens=512, max_length=None, temperature=0.3, do_sample=True,
            repetition_penalty=1.15
        )
    reply = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
    reply = reply.replace("。", " ").strip()
    return reply or "(โมเดลไม่ตอบ ลองถามใหม่ หรือเพิ่มข้อมูลเทรน)"


def query_of(text):
    return text[4:].strip() if text.startswith("ค้น ") else text


if len(sys.argv) > 1:  # ถามครั้งเดียวแล้วจบ
    text = " ".join(sys.argv[1:])
    reply = ask([{"role": "user", "content": prep(text)}], query_of(text))
    hide()
    print(reply)
else:  # โหมดคุยต่อเนื่อง
    hide()
    history = []
    while True:
        text = input("คุณ: ").strip()
        if text.lower() in ("exit", "quit", "ออก"):
            break
        if not text:
            continue
        saved = try_save(text)
        if saved is not None:
            print("AI:", saved)
            continue
        history.append({"role": "user", "content": prep(text)})
        show()
        reply = ask(history, query_of(text))
        hide()
        print("AI:", reply)
        history.append({"role": "assistant", "content": reply})
