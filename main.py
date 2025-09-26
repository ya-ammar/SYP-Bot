from email import message
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request , render_template,redirect
import logging
import requests
from bs4 import BeautifulSoup
import os
import psycopg2
import time
import Db;

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
Token = os.getenv("TOKEN")
bot_name = os.getenv("bot_name")
CHANNEL_name = os.getenv("CHANNEL_name")
Admin_Id = os.getenv("Admin")
URL = os.getenv("URL")


Db.initialize_db()
bot = telebot.TeleBot(Token,parse_mode="HTML")
app = Flask(__name__)

# ----- ارسال للادمن 
def Send_to_Admin(text):
    try:
        bot.send_message(Admin_Id, text)
    except:
        logging.exception("خطأ في ارسال تنبيه الادمن")



def check_and_send():
   
    t = time.localtime()
    current_hour = t.tm_hour
    day = t.tm_wday

    if day == 4:
        return False
    if current_hour < 11 or current_hour > 20:
        return False

    last_hour = time.localtime(Db.get_latest_price("USD")[3]).tm_hour

    if last_hour == current_hour:
        return False

    return True

def Get_Soup():
    try:
        resp = requests.get(URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup
    except Exception:
        logging.error("خطأ في فحص الموقع")
        Send_to_Admin("خطأ في فحص الموقع")


codes=("USD", "EUR", "TRY")

def fetch_currencies(soup):
   
    try:
        results = {}
        rows = soup.select("table.table-hover.local-cur tbody tr")
        
        for row in rows:
            th = row.find("th")
            if not th:
                continue

            strong = th.find("strong")
            if not strong:
                continue

            code = strong.get_text(strip=True).strip("()").upper()
            if code not in codes:
                continue

            tds = row.find_all("td")
            if len(tds) < 3:
                logging.warning(f"بنية الجدول غير متوقعة للعملة {code}")
                continue

            # إزالة الفواصل وتحويل النص إلى float
            try:
                buy = float(tds[1].get_text(strip=True).replace(",", ""))
                sell = float(tds[2].get_text(strip=True).replace(",", ""))
            except ValueError:
                logging.warning(f"خطأ في تحويل سعر العملة {code}")
                continue

            results[code] = (buy, sell)

        if not results:
            raise ValueError("لم يتم العثور على العملات المطلوبة")

        return results

    except Exception:
        logging.exception("خطأ أثناء جلب أسعار العملات")
        raise

def fetch_gold_prices(soup):
    try:
        
        table = soup.select_one("table.table-hover.gold tbody")
        if not table:
            raise ValueError("جدول الذهب غير موجود")

        gold_prices = {}
        rows = table.find_all("tr")
        for row in rows:
            th = row.find("th")
            if not th:
                continue
            span = th.find("span")
            strong = row.find("strong")
            if not span or not strong:
                continue
            text = span.get_text(strip=True)
            price_text = strong.get_text(strip=True).replace(",", "")
            try:
                price = float(price_text)
            except:
                continue

            if "18" in text:
                gold_prices["18K"] = price
            elif "21" in text:
                gold_prices["21K"] = price
            elif "24" in text:
                gold_prices["24K"] = price

        if not gold_prices:
            raise ValueError("لم يتم العثور على أي أسعار ذهب")

        return gold_prices

    except Exception:
        logging.exception("خطأ أثناء جلب أسعار الذهب")
        raise

def Go_Work():
    try:
        t = time.localtime()
        current_hour = t.tm_hour
        soup = Get_Soup()

        if current_hour == 3:
            currencies = fetch_gold_prices(soup)
            send_gold(currencies)
            return
        elif current_hour == 11 or current_hour == 8 or current_hour == 1 or current_hour == 5:
            currencies = fetch_currencies(soup)
            if not currencies:
                Send_to_Admin("لا يوجد معاملات")
                return
            
            if current_hour == 11:
                send_all(currencies , False)
            elif current_hour == 5:
                send_all(currencies , True)
            elif current_hour == 1 or current_hour == 5:
                send_dollar(currencies)

        currencies = fetch_currencies(soup)
        usd = currencies.get("USD", ("0", "0"))
        Db.add_currency_record("USD",usd[0],usd[1])
    
    except Exception:
        logging.error("خطأ في فحص الموقع")
        Send_to_Admin("خطأ في فحص الموقع")

def testwork():
    currencies = fetch_gold_prices()
    send_gold(currencies)
    currencies = fetch_currencies()
    send_all(currencies , False)
    send_dollar(currencies)


def get_day(num):

    if num == 4:
        return "الجمعة"
    elif num == 5:
        return "السبت"
    elif num == 6:
        return "الاحد"
    elif num == 0:
        return "الاثنين"
    elif num == 1:
        return "الثلاثاء"
    elif num == 2:
        return "الاربعاء"
    elif num == 3:
        return "الخميس"

def send_dollar(currencies):

    if "USD" not in currencies:
        return
    usd = currencies.get("USD", ("0", "0"))
    ts = time.localtime()
    date_str = time.strftime("%Y-%m-%d", ts)
    day = get_day(ts.tm_wday)
    message = (
         f"<b>سعر صرف الدولار مقابل الليرة الآن 🇺🇸</b>\n\n"
         f"<blockquote>شراء: {usd[0]}</blockquote>\n"
         f"<blockquote>مبيع: {usd[1]}</blockquote>\n\n"
         f"<blockquote>{day} - {date_str}  </blockquote>\n"
         f"https://t.me/{CHANNEL_name}")
    try:
        bot.send_message(f"@{CHANNEL_name}", message)
    except Exception:
        logging.error("خطأ في فحص الموقع")

def send_all(currencies , end):
    usd = currencies.get("USD", ("0", "0"))
    EUR = currencies.get("EUR", ("0", "0"))
    TRY = currencies.get("TRY", ("0", "0"))

    ts = time.localtime()
    date_str = time.strftime("%Y-%m-%d", ts)
    day = get_day(ts.tm_wday)

    if end:
        ttr = "اغلاق يوم "
    else:
        ttr = "افتتاح يوم "

    message = (
         f"<b>{ttr} {day}</b>\n\n"
         f"<b>🇺🇸 دولار امريكي</b>\n"
         f"<blockquote>شراء: {usd[0]}</blockquote>\n"
         f"<blockquote>مبيع: {usd[1]}</blockquote>\n\n"
         f"<b>🇪🇺 يورو</b>\n"
         f"<blockquote>شراء: {EUR[0]}</blockquote>\n"
         f"<blockquote>مبيع: {EUR[1]}</blockquote>\n\n"
         f"<b>🇹🇷 ليرة تركي</b>\n"
         f"<blockquote>شراء: {TRY[0]}</blockquote>\n"
         f"<blockquote>مبيع: {TRY[1]}</blockquote>\n\n"
         f"<blockquote>{day} - {date_str}  </blockquote>\n\n"
         f"https://t.me/{CHANNEL_name}")

    with open("Gold.jpeg", "rb") as photo:
        bot.send_photo(f"@{CHANNEL_name}", photo, caption=message)

def send_gold(currencies):
    k18 = currencies.get("18K", ("0"))
    k21 = currencies.get("21K", ("0"))
    k24 = currencies.get("24K", ("0"))

    ts = time.localtime()
    date_str = time.strftime("%Y-%m-%d", ts)
    day = get_day(ts.tm_wday)

    message = (
         f"<b>اسعار الذهب ليوم {day}</b>\n\n"
         f"<b>ذهب 18 قيراط</b>\n"
         f"<blockquote>{k18[0]}</blockquote>\n\n"
         f"<b>ذهب 21 قيراط</b>\n"
         f"<blockquote>{k21[0]}</blockquote>\n\n"
         f"<b>ذهب 24 قيراط</b>\n"
         f"<blockquote>{k24[0]}</blockquote>\n\n"
         f"<blockquote>{day} - {date_str}  </blockquote>\n\n"
         f"https://t.me/{CHANNEL_name}")

    with open("Price.jpg", "rb") as photo:
        bot.send_photo(f"@{CHANNEL_name}", photo, caption=message)

# -------------------------------------------- منطق الويب

@app.route("/", methods=["GET"])
def main_pag():

    if check_and_send():
        try:
            Go_Work()
        except Exception:
            logging.error("خطأ في فحص الموقع")
            Send_to_Admin("خطأ في فحص الموقع")

    return "ok", 200


@app.route(f"/{Token}", methods=["POST"])
def webhook():

    try:
        if request.headers.get('content-type') == 'application/json':
            json_str = request.get_data().decode("utf-8")
            update = telebot.types.Update.de_json(json_str)

            if update.message:

                if update.message.from_user.id == "Admin":
                #    Send_to_Admin("Hello")
                    testwork()
                
    except:
        logging.exception("خطأ في استقبال التلغرام الاساسي")
    finally:
        return "ok", 200

