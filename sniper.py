from curl_cffi import requests
import time
import json
import os

# =========================
# TELEGRAM BOT
# =========================
BOT_TOKEN = "8796972310:AAHI760o1EJiU9I-Zaqdq6ajwy7BNdlaaxo"
ADMINS = [6119063099]   # сюда ставь свой chat_id админа

USERS_DB_FILE = "users_db.json"
STATE_FILE = "state.json"

# =========================
# MARKET TOKENS
# =========================
QUANT_AUTH = "Bearer query_id=AAE7frlsAgAAADt-uWyt3-7B&user=%7B%22id%22%3A6119063099%2C%22first_name%22%3A%22Kotik%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22Kotikloz%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FvO-gnodRBXbNi0NVTwMsTAcorM6QCYoy1FXF48Fp9HwBtWOVl_LT8_KJUmM0zJiG.svg%22%7D&auth_date=1773332552&signature=iAlM7t9-4VKaylYdlaBnPCsYhsR907RU0ZTRa535dPm-a-xIFqYNSLqiGGi4waZS4J6qRP0OOXOSUSzWxQM2Bg&hash=5089e019edf4e3d6a2ba8f78b4c02a304d30787ac327be6bf5af8de89006f0cb"
TGMRKT_TOKEN = "3ef9d9f8-9d20-4b46-a7a4-9a2cf530390f"

# =========================
# URLS
# =========================
QUANT_URL = "https://quant-marketplace.com/api/channels?page=1&limit=1"
TGMRKT_URL = "https://api.tgmrkt.io/api/v1/channels/saling"

# =========================
# HEADERS
# =========================
QUANT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "referer": "https://quant-marketplace.com/",
    "origin": "https://quant-marketplace.com",
    "authorization": QUANT_AUTH
}

TGMRKT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://cdn.tgmrkt.io",
    "referer": "https://cdn.tgmrkt.io/",
    "authorization": TGMRKT_TOKEN,
    "cookie": f"access_token={TGMRKT_TOKEN}",
    "user-agent": "Mozilla/5.0"
}

TGMRKT_PAYLOAD = {
    "count": 20,
    "cursor": "",
    "isListed": False,
    "filterGiftIds": [],
    "minPrice": None,
    "maxPrice": None,
    "lowToHigh": False,
    "ordering": "None",
    "query": None
}

# =========================
# GIFTS
# =========================
GIFT_NAMES = {
    "5999277561060787166": "Torch of freedom",
    "5999298447486747746": "Statue of Liberty",
    "5832371318007268701": "Coconut",
    "5832644211639321671": "Pink Flamingo",
    "5834918435477259676": "Sandcastle",
    "5832497899283415733": "Surfboard",
    "5834651202612102354": "Durov’s Sunglasses",
    "5832279504491381684": "Resistance Dog",
    "5832325860073407546": "Peace dove",
    "5898012527257715797": "Ice cream cone",
}

# =========================
# STATE
# =========================
last_quant_id = 0
last_tgmrkt_id = 0
update_offset = None


# =========================
# FILE HELPERS
# =========================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users_db():
    default = {
        "approved": [],
        "pending": [],
        "banned": []
    }
    db = load_json(USERS_DB_FILE, default)
    for key in default:
        if key not in db or not isinstance(db[key], list):
            db[key] = []
    return db


def save_users_db(db):
    save_json(USERS_DB_FILE, db)


def load_state():
    default = {
        "last_quant_id": 0,
        "last_tgmrkt_id": 0,
        "update_offset": None
    }
    return load_json(STATE_FILE, default)


def save_state():
    data = {
        "last_quant_id": last_quant_id,
        "last_tgmrkt_id": last_tgmrkt_id,
        "update_offset": update_offset
    }
    save_json(STATE_FILE, data)


# =========================
# TELEGRAM API
# =========================
def tg_post(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.post(url, json=payload, timeout=20)


def tg_get(method: str, params: dict | None = None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.get(url, params=params or {}, timeout=20)


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    r = tg_post("sendMessage", payload)
    print(f"[TG] sendMessage -> {chat_id}: {r.status_code}")
    if r.status_code != 200:
        print("[TG] ERROR:", r.text[:500])


def answer_callback(callback_query_id, text):
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": False
    }
    tg_post("answerCallbackQuery", payload)


def edit_message_reply_markup(chat_id, message_id, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": reply_markup
    }
    tg_post("editMessageReplyMarkup", payload)


# =========================
# ACCESS CONTROL
# =========================
def is_admin(chat_id: int) -> bool:
    return chat_id in ADMINS


def add_approved(chat_id: int) -> bool:
    db = load_users_db()

    if chat_id in db["banned"]:
        return False

    changed = False

    if chat_id in db["pending"]:
        db["pending"].remove(chat_id)
        changed = True

    if chat_id not in db["approved"]:
        db["approved"].append(chat_id)
        changed = True

    save_users_db(db)
    return changed


def remove_approved(chat_id: int) -> bool:
    db = load_users_db()
    if chat_id in db["approved"]:
        db["approved"].remove(chat_id)
        save_users_db(db)
        return True
    return False


def add_pending(chat_id: int) -> str:
    db = load_users_db()

    if chat_id in db["banned"]:
        return "banned"

    if chat_id in db["approved"]:
        return "approved"

    if chat_id in db["pending"]:
        return "pending"

    db["pending"].append(chat_id)
    save_users_db(db)
    return "added"


def remove_pending(chat_id: int) -> bool:
    db = load_users_db()
    if chat_id in db["pending"]:
        db["pending"].remove(chat_id)
        save_users_db(db)
        return True
    return False


def ban_user(chat_id: int) -> bool:
    db = load_users_db()

    changed = False

    if chat_id in db["approved"]:
        db["approved"].remove(chat_id)
        changed = True

    if chat_id in db["pending"]:
        db["pending"].remove(chat_id)
        changed = True

    if chat_id not in db["banned"]:
        db["banned"].append(chat_id)
        changed = True

    save_users_db(db)
    return changed


def unban_user(chat_id: int) -> bool:
    db = load_users_db()
    if chat_id in db["banned"]:
        db["banned"].remove(chat_id)
        save_users_db(db)
        return True
    return False


def send_access_request_to_admin(user: dict):
    user_id = user.get("id")
    username = user.get("username") or "без username"
    first_name = user.get("first_name") or "Unknown"

    text = (
        "🆕 Новая заявка на доступ\n\n"
        f"ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Имя: {first_name}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Одобрить", "callback_data": f"approve:{user_id}"},
                {"text": "❌ Отклонить", "callback_data": f"decline:{user_id}"}
            ],
            [
                {"text": "⛔ Бан", "callback_data": f"ban:{user_id}"}
            ]
        ]
    }

    for admin_id in ADMINS:
        send_message(admin_id, text, reply_markup=keyboard)


def broadcast_message(text: str):
    db = load_users_db()
    approved_users = db["approved"]

    if not approved_users:
        print("[TG] Нет одобренных пользователей")
        return

    for chat_id in approved_users[:]:
        try:
            send_message(chat_id, text)
            time.sleep(0.15)
        except Exception as e:
            print(f"[TG] Broadcast error for {chat_id}: {e}")


# =========================
# BOT COMMANDS
# =========================
def handle_start(msg: dict):
    chat_id = msg["chat"]["id"]
    user = msg.get("from", {})

    status = add_pending(chat_id)

    if status == "banned":
        send_message(chat_id, "⛔ Тебе отказано в доступе.")
        return

    if status == "approved":
        send_message(chat_id, "✅ У тебя уже есть доступ. Новые лоты будут приходить сюда.")
        return

    if status == "pending":
        send_message(chat_id, "⏳ Твоя заявка уже отправлена админу. Жди ответа.")
        return

    send_message(chat_id, "⏳ Заявка отправлена админу. После одобрения начнешь получать новые лоты.")
    send_access_request_to_admin(user)


def handle_stop(msg: dict):
    chat_id = msg["chat"]["id"]

    removed1 = remove_approved(chat_id)
    removed2 = remove_pending(chat_id)

    if removed1 or removed2:
        send_message(chat_id, "✅ Ты отключен от рассылки.")
    else:
        send_message(chat_id, "Ты и так не был подключен.")


def handle_help(chat_id: int, admin: bool):
    text = (
        "/start — запросить доступ\n"
        "/stop — отключиться\n"
        "/help — помощь"
    )

    if admin:
        text += (
            "\n\nАдмин команды:\n"
            "/users — список одобренных\n"
            "/pending — список заявок\n"
            "/add ID — выдать доступ\n"
            "/remove ID — убрать доступ\n"
            "/ban ID — забанить\n"
            "/unban ID — разбанить"
        )

    send_message(chat_id, text)


def handle_admin_command(msg: dict, text: str):
    chat_id = msg["chat"]["id"]

    if not is_admin(chat_id):
        return

    db = load_users_db()
    parts = text.split()

    if text == "/users":
        approved = db["approved"]
        if not approved:
            send_message(chat_id, "Одобренных пользователей нет.")
            return
        send_message(chat_id, "✅ Approved:\n" + "\n".join(map(str, approved)))
        return

    if text == "/pending":
        pending = db["pending"]
        if not pending:
            send_message(chat_id, "Заявок нет.")
            return
        send_message(chat_id, "⏳ Pending:\n" + "\n".join(map(str, pending)))
        return

    if len(parts) == 2 and parts[0] in ["/add", "/remove", "/ban", "/unban"]:
        try:
            target_id = int(parts[1])
        except ValueError:
            send_message(chat_id, "ID должен быть числом.")
            return

        if parts[0] == "/add":
            add_approved(target_id)
            send_message(chat_id, f"✅ Выдан доступ: {target_id}")
            try:
                send_message(target_id, "✅ Админ выдал тебе доступ. Теперь ты будешь получать новые лоты.")
            except Exception:
                pass
            return

        if parts[0] == "/remove":
            ok = remove_approved(target_id)
            remove_pending(target_id)
            send_message(chat_id, f"🗑 Удаление {target_id}: {'ok' if ok else 'нет в approved'}")
            return

        if parts[0] == "/ban":
            ban_user(target_id)
            send_message(chat_id, f"⛔ Забанен: {target_id}")
            try:
                send_message(target_id, "⛔ Тебе закрыт доступ.")
            except Exception:
                pass
            return

        if parts[0] == "/unban":
            ok = unban_user(target_id)
            send_message(chat_id, f"♻️ Разбан {target_id}: {'ok' if ok else 'не был в бане'}")
            return


def handle_callback(callback: dict):
    callback_id = callback.get("id")
    from_user = callback.get("from", {})
    from_id = from_user.get("id")
    data = callback.get("data", "")

    message = callback.get("message", {})
    msg_chat_id = message.get("chat", {}).get("id")
    msg_id = message.get("message_id")

    if not is_admin(from_id):
        answer_callback(callback_id, "Ты не админ")
        return

    try:
        action, raw_user_id = data.split(":")
        user_id = int(raw_user_id)
    except Exception:
        answer_callback(callback_id, "Некорректный callback")
        return

    if action == "approve":
        add_approved(user_id)
        answer_callback(callback_id, "Пользователь одобрен")
        send_message(user_id, "✅ Админ одобрил доступ. Теперь ты будешь получать новые лоты.")

        if msg_chat_id and msg_id:
            edit_message_reply_markup(msg_chat_id, msg_id, {"inline_keyboard": []})
        return

    if action == "decline":
        remove_pending(user_id)
        answer_callback(callback_id, "Заявка отклонена")
        send_message(user_id, "❌ Админ отклонил заявку.")

        if msg_chat_id and msg_id:
            edit_message_reply_markup(msg_chat_id, msg_id, {"inline_keyboard": []})
        return

    if action == "ban":
        ban_user(user_id)
        answer_callback(callback_id, "Пользователь забанен")
        try:
            send_message(user_id, "⛔ Тебе закрыт доступ.")
        except Exception:
            pass

        if msg_chat_id and msg_id:
            edit_message_reply_markup(msg_chat_id, msg_id, {"inline_keyboard": []})
        return


def process_updates():
    global update_offset

    params = {"timeout": 0}
    if update_offset is not None:
        params["offset"] = update_offset

    r = tg_get("getUpdates", params=params)
    data = r.json()

    if not data.get("ok"):
        print("[TG] getUpdates error:", data)
        return

    for upd in data.get("result", []):
        update_id = upd.get("update_id")
        if update_id is not None:
            update_offset = update_id + 1

        if "message" in upd:
            msg = upd["message"]
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            text = (msg.get("text") or "").strip()

            if not chat_id:
                continue

            if text == "/start":
                handle_start(msg)
            elif text == "/stop":
                handle_stop(msg)
            elif text == "/help":
                handle_help(chat_id, is_admin(chat_id))
            elif is_admin(chat_id):
                handle_admin_command(msg, text)

        elif "callback_query" in upd:
            handle_callback(upd["callback_query"])

    save_state()


# =========================
# FORMATTERS
# =========================
def format_quant(item):
    channel_id = item.get("id")
    gifts = item.get("gifts", {})
    price = item.get("price")

    total = 0
    lines = []

    for gift_id, data in gifts.items():
        if gift_id == "upgraded":
            continue

        qty = 0
        if isinstance(data, dict):
            qty = data.get("count", 0)
        elif isinstance(data, int):
            qty = data

        total += qty
        name = GIFT_NAMES.get(str(gift_id), f"Unknown ({gift_id})")
        lines.append(f"{name} — {qty} шт")

    gifts_text = "\n".join(lines) if lines else "Нет данных"
    link = f"https://t.me/QuantMarketRobot/market?startapp=channel{channel_id}"

    return (
        f"[QUANT]\n"
        f"Всего подарков: {total}\n"
        f"{gifts_text}\n"
        f"Цена: {price} TON\n"
        f"Купить: {link}"
    )


def format_tgmrkt(item):
    name = item.get("name")
    gifts_count = item.get("giftsCount")
    sale_price = item.get("salePrice", 0)
    price_ton = sale_price / 1_000_000_000 if sale_price else 0

    preview = item.get("previewGift", {})
    gift_name = preview.get("title", "Unknown")

    sale_id = (item.get("id") or "").replace("-", "")
    link = f"https://t.me/mrkt/app?startapp=channelshare{sale_id}"

    return (
        f"[TGMRKT]\n"
        f"Канал: @{name}\n"
        f"Гифтов: {gifts_count}\n"
        f"Превью: {gift_name}\n"
        f"Цена: {price_ton} TON\n"
        f"Купить: {link}"
    )


# =========================
# MARKET CHECKERS
# =========================
def check_quant():
    global last_quant_id

    r = requests.get(
        QUANT_URL,
        impersonate="chrome124",
        headers=QUANT_HEADERS,
        timeout=5
    )

    data = r.json()
    channels = data.get("channels", [])

    if not channels:
        return None

    newest = channels[0]
    newest_id = newest.get("id")

    if newest_id != last_quant_id:
        last_quant_id = newest_id
        save_state()
        return format_quant(newest)

    return None


def check_tgmrkt():
    global last_tgmrkt_id

    r = requests.post(
        TGMRKT_URL,
        impersonate="chrome124",
        headers=TGMRKT_HEADERS,
        json=TGMRKT_PAYLOAD,
        timeout=5
    )

    data = r.json()
    channels = data.get("channels", [])

    if not channels:
        return None

    newest = channels[0]
    newest_id = newest.get("id")

    if newest_id != last_tgmrkt_id:
        last_tgmrkt_id = newest_id
        save_state()
        return format_tgmrkt(newest)

    return None


# =========================
# FIRST INIT
# =========================
state = load_state()
last_quant_id = state.get("last_quant_id", 0)
last_tgmrkt_id = state.get("last_tgmrkt_id", 0)
update_offset = state.get("update_offset", None)

print("Снайпер с админ-панелью запущен")
for admin_id in ADMINS:
    try:
        send_message(admin_id, "✅ Бот с админ-панелью запущен")
    except Exception as e:
        print("[TG] Admin start message error:", e)


# =========================
# MAIN LOOP
# =========================
while True:
    try:
        process_updates()

        q = check_quant()
        if q:
            print(q)
            print("-" * 70)
            broadcast_message(q)

        t = check_tgmrkt()
        if t:
            print(t)
            print("-" * 70)
            broadcast_message(t)

    except Exception as e:
        err = f"Ошибка: {e}"
        print(err)
        for admin_id in ADMINS:
            try:
                send_message(admin_id, err)
            except Exception:
                pass

    time.sleep(3)
