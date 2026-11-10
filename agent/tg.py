import requests
from .config import TG_TOKEN, TG_CHAT

API = f"https://api.telegram.org/bot{TG_TOKEN}"


def send(text, buttons=None):
    body = {"chat_id": TG_CHAT, "text": text[:4000], "disable_web_page_preview": True}
    if buttons:
        body["reply_markup"] = {"inline_keyboard": buttons}
    try:
        r = requests.post(f"{API}/sendMessage", json=body, timeout=20)
        if not r.ok:
            print("Telegram send failed", r.status_code, r.text[:200])
    except requests.RequestException as e:
        print("Telegram error", e)


def updates(offset):
    try:
        r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=20)
        return r.json().get("result", []) if r.ok else []
    except requests.RequestException:
        return []


def answer(cb_id, text):
    try:
        requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cb_id, "text": text}, timeout=10)
    except requests.RequestException:
        pass


def clear_buttons(chat_id, message_id):
    try:
        requests.post(f"{API}/editMessageReplyMarkup",
                      json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
                      timeout=10)
    except requests.RequestException:
        pass
