import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request , render_template,redirect
import logging
import requests
from bs4 import BeautifulSoup
import os

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

Token = os.getenv("TOKEN")
URL = "https://sp-today.com/en/"
bot = telebot.TeleBot(Token)
app = Flask(__name__)


# -------------------------------------------- توابع مساعدة
# ------ ارسال القائمة
def fetch_usd_buy_sale():
  
    try:
        resp = requests.get(URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table.table-hover.local-cur tbody tr")
        for row in rows:
            th = row.find("th")
            if not th:
                continue
            strong = th.find("strong")
            if not strong:
                continue
            code = strong.get_text(strip=True).strip("()")
            if code.upper() == "USD":
                tds = row.find_all("td")
                # حسب HTML: tds[0] فارغ، tds[1]=Buy، tds[2]=Sale
                if len(tds) >= 3:
                    buy = tds[1].get_text(strip=True)
                    sale = tds[2].get_text(strip=True)
                    return buy, sale
                else:
                    raise ValueError("بنية الجدول غير متوقعة")
        raise ValueError("USD غير موجود في الجدول")
    except Exception:
        logging.exception("خطأ أثناء جلب سعر الدولار")
        raise
    
def send_usd_rate(user_id):
    try:
        buy, sale = fetch_usd_buy_sale()
        text = f"سعر الدولار اليوم (SP-Today):\nشراء: {buy}\nبيع: {sale}"
        bot.send_message(user_id, text)
    except Exception as e:
        logging.exception("فشل إرسال سعر الدولار")
        # خيار: ترسل رسالة خطأ للمشرف أو تطبع
        print("خطأ:", e)

def start_command(message):

        user_id = message.from_user.id
        send_usd_rate(user_id)

def handle_command(message):

    if message.text.startswith("/start"):
        start_command(message)
    else:
        user_id = message.from_user.id
        bot.send_message(user_id, "test")
    


# -------------------------------------------- منطق الويب

@app.route("/", methods=["GET"])
def main_pag():
    return 'Hello from Flask!'


@app.route(f"/{Token}", methods=["POST"])
def webhook():

    try:
        if request.headers.get('content-type') == 'application/json':
            json_str = request.get_data().decode("utf-8")
            update = telebot.types.Update.de_json(json_str)

            if update.message:

                if update.message.chat.type != "private":
                    return "ok", 200

                if update.message.text:
                    handle_command(update.message)
        

    except:
        logging.exception("خطأ في استقبال التلغرام الاساسي")
    finally:
        return "ok", 200

