# bot-alertas-main/stock_monitor.py

import os
import logging
import requests
import yfinance as yf
from datetime import datetime

from app import db
from models import Stock, Alert, TelegramConfig

# ———————————————
# Logger setup para este módulo
# ———————————————
logger = logging.getLogger("stock_monitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(sh)

# Quita el verbose de yfinance excepto WARNING+
logging.getLogger("yfinance").setLevel(logging.WARNING)


def send_telegram_message(message: str) -> bool:
    """
    Envía un mensaje por Telegram.
    Primero busca TOKEN/CHAT_ID en vars de entorno; si no están,
    usa la tabla TelegramConfig de la DB.
    """
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if token and chat_id:
        logger.info("📡 Usando configuración de Telegram desde ENV")
    else:
        cfg = TelegramConfig.query.first()
        if not cfg or not cfg.is_active:
            logger.error("⚠️ No existe config de Telegram ni en ENV ni en DB")
            return False
        token   = cfg.bot_token
        chat_id = cfg.chat_id
        logger.info("📡 Usando configuración de Telegram desde DB")

    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": "HTML",
    }

    try:
        # Enviar como JSON para asegurar Content-Type correcto
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            # Se loguea el cuerpo para ver error detallado
            logger.error(f"Telegram HTTP {resp.status_code} – {resp.text}")
            return False
        logger.info("✅ Mensaje de Telegram enviado")
        return True
    except Exception as e:
        logger.exception(f"❌ Excepción enviando Telegram: {e}")
        return False


def check_all_stocks():
    """
    Recorre todas las acciones activas, actualiza precio y manda alertas
    si supera target o cae en stop_loss.
    """
    logger.info("▶️ Iniciando stock price check")
    stocks = Stock.query.filter_by(is_active=True).all()

    for stock in stocks:
        old_price = stock.current_price or 0.0

        try:
            # — Obtener precio más reciente con yfinance
            ticker = yf.Ticker(stock.symbol)
            df     = ticker.history(period="1d", interval="1m")
            if df.empty:
                logger.warning(f"⚠️ Sin datos para {stock.symbol}, salteando")
                continue

            current_price = float(df["Close"].iloc[-1])
            logger.info(f"[CHECK] {stock.symbol}: {old_price} → {current_price}")

            # — Si cambió, guardo en DB
            if current_price != old_price:
                stock.current_price = current_price
                db.session.commit()
                logger.info(f"[DB] Precio actualizado para {stock.symbol}")

                # — Alertas
                # Target
                if stock.target_price and current_price >= stock.target_price:
                    msg = f"🎯 <b>{stock.symbol}</b> alcanzó target: {current_price}"
                    if stock.description:
                        msg += f"\n📝 {stock.description}"
                    if send_telegram_message(msg):
                        alert = Alert(
                            stock_symbol=stock.symbol,
                            alert_type="target",
                            price=current_price,
                            message=msg,
                            sent_at=datetime.utcnow(),  # ✅ corregido
                            is_sent=True
                        )

                        db.session.add(alert)
                        db.session.commit()
                        logger.info(f"[ALERT] Target enviada para {stock.symbol}")

                # Stop loss
                if stock.stop_loss and current_price <= stock.stop_loss:
                    msg = f"💔 <b>{stock.symbol}</b> tocó stop loss: {current_price}"
                    if stock.description:
                        msg += f"\n📝 {stock.description}"
                    if send_telegram_message(msg):
                        alert = Alert(
                            stock_symbol=stock.symbol,
                            alert_type="stop_loss",
                            price=current_price,
                            message=msg,
                            sent_at=datetime.utcnow(),  # ✅ corregido
                            is_sent=True
                        )

                        db.session.add(alert)
                        db.session.commit()
                        logger.info(f"[ALERT] Stop loss enviada para {stock.symbol}")

        except Exception:
            logger.exception(f"[ERROR] Falló al procesar {stock.symbol}")

    logger.info("✅ Fin de stock price check")
