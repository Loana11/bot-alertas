--- stock_monitor.py
+++ stock_monitor.py
@@ 1,6c1,10
-import yfinance as yf
-import requests
-import logging
+import os
+import yfinance as yf
+import requests
+import logging
 from datetime import datetime
 from app import db
 from models import Stock, Alert, TelegramConfig
+
+# Usa un logger con nombre de módulo
+logger = logging.getLogger(__name__)

@@ -8,22 +16,42 @@ def send_telegram_message(message):
     """Send message via Telegram bot"""
-    try:
-        config = TelegramConfig.query.first()
-        if not config:
-            logging.error("No Telegram configuration found")
-            return False
-        
-        url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
-        data = {'chat_id': config.chat_id, 'text': message, 'parse_mode': 'HTML'}
-        resp = requests.post(url, data=data)
-        resp.raise_for_status()
-        return True
-    except Exception as e:
-        logging.error(f"Error sending Telegram message: {e}")
-        return False
+    # 1) Intenta leer desde ENV vars
+    token  = os.getenv("TELEGRAM_BOT_TOKEN")
+    chat_id = os.getenv("TELEGRAM_CHAT_ID")
+
+    # 2) Si falta env, cae al registro en la DB
+    if not token or not chat_id:
+        cfg = TelegramConfig.query.first()
+        if not cfg or not cfg.is_active:
+            logger.error("No Telegram configuration found (env ni DB)")
+            return False
+        token   = cfg.bot_token
+        chat_id = cfg.chat_id
+        logger.info("Usando configuración Telegram desde DB")
+    else:
+        logger.info("Usando configuración Telegram desde ENV vars")
+
+    url  = f"https://api.telegram.org/bot{token}/sendMessage"
+    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
+    try:
+        resp = requests.post(url, data=data, timeout=10)
+        resp.raise_for_status()
+        logger.info("Telegram message sent successfully")
+        return True
+    except Exception as e:
+        logger.exception(f"Error sending Telegram message: {e}")
+        return False

@@
-def check_all_stocks():
-    """Check all active stocks and send alerts if needed"""
-    logging.info("Starting stock price check...")
-    stocks = Stock.query.filter_by(is_active=True).all()
-    
-    for stock in stocks:
-        try:
-            # fetch and compare prices...
-            pass
-        except Exception as e:
-            logging.error(f"Error checking stock {stock.symbol}: {e}")
-    
-    # Commit all changes
-    db.session.commit()
-    logging.info("Stock price check completed")
+def check_all_stocks():
+    """Check all active stocks, actualizar precio y enviar alertas."""
+    logger.info("=== Iniciando stock price check ===")
+    stocks = Stock.query.filter_by(is_active=True).all()
+
+    for stock in stocks:
+        old_price = stock.current_price
+        try:
+            # 1) Obtengo precio con yfinance (tu método anterior aquí si lo tenías)
+            ticker = yf.Ticker(stock.symbol)
+            data   = ticker.history(period="1d", interval="1m")
+            if data.empty:
+                logger.warning(f"No data for {stock.symbol}")
+                continue
+            current_price = float(data["Close"].iloc[-1])
+
+            logger.info(f"[CHECK] {stock.symbol}: {old_price} → {current_price}")
+
+            # 2) Si cambió, guardo en DB
+            if current_price != old_price:
+                stock.current_price = current_price
+                db.session.commit()
+                logger.info(f"[DB] Guardado nuevo precio de {stock.symbol}")
+
+                # 3) Compruebo umbrales y envío alertas
+                if current_price >= stock.target_price:
+                    msg = f"🎯 {stock.symbol} alcanzó target: {current_price}"
+                    if send_telegram_message(msg):
+                        db.session.add(Alert(
+                            stock_symbol=stock.symbol,
+                            alert_type="target",
+                            price=current_price,
+                            message=msg,
+                            is_sent=True
+                        ))
+                        db.session.commit()
+                        logger.info(f"Alert TARGET enviada para {stock.symbol}")
+
+                if current_price <= stock.stop_loss:
+                    msg = f"💔 {stock.symbol} tocó stop loss: {current_price}"
+                    if send_telegram_message(msg):
+                        db.session.add(Alert(
+                            stock_symbol=stock.symbol,
+                            alert_type="stop_loss",
+                            price=current_price,
+                            message=msg,
+                            is_sent=True
+                        ))
+                        db.session.commit()
+                        logger.info(f"Alert STOP_LOSS enviada para {stock.symbol}")
+
+        except Exception:
+            logger.exception(f"[ERROR] al actualizar {stock.symbol}")
+
+    logger.info("=== Fin de stock price check ===")
