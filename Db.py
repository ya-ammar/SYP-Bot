import os
import psycopg2
import time
import logging

DATABASE_URL = os.getenv("DATABASE_URL")

def create_connection():
    try:  
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        logging.exception("خطأ في فتح اتصال")
        raise 

def initialize_db():
    with create_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS currency_history (
                        id SERIAL PRIMARY KEY,
                        code TEXT NOT NULL,
                        buy_price NUMERIC NOT NULL,
                        sell_price NUMERIC NOT NULL,
                        ts BIGINT NOT NULL
                    );
                """)
                conn.commit()
            except Exception:
                logging.exception("خطأ في انشاء الجداول")

def add_currency_record(code, buy_price, sell_price):
    
    t = time.localtime() 
    ts = int(time.mktime(t))
    with create_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO currency_history (code, buy_price, sell_price, ts)
                    VALUES (%s, %s, %s, %s);
                """, (code, buy_price, sell_price, ts))
                conn.commit()
            except Exception:
                logging.exception("خطأ في تحديث الاسعار")

def get_latest_price(code):
    with create_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT code, buy_price, sell_price, ts
                    FROM currency_history
                    WHERE code = %s
                    ORDER BY ts DESC
                    LIMIT 1;
                """, (code,))
                result = cur.fetchone()
                if result:
                    return result  # (code, buy_price, sell_price, ts)
                else:
                    return ("noValue", 0, 0, 0)
            except Exception:
                logging.exception("خطأ في جلب الاسعار")
                return ("noValue", 0, 0, 0)