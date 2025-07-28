import yfinance as yf
import requests
import logging
from datetime import datetime
from app import db
from models import Stock, Alert, TelegramConfig

def send_telegram_message(message):
    """Send message via Telegram bot"""
    try:
        config = TelegramConfig.query.first()
        if not config:
            logging.error("No Telegram configuration found")
            return False
        
        url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
        data = {
            'chat_id': config.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        
        logging.info(f"Telegram message sent successfully: {message}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")
        return False

def check_all_stocks():
    """Check all active stocks and send alerts if needed"""
    logging.info("Starting stock price check...")
    
    stocks = Stock.query.filter_by(is_active=True).all()
    
    for stock in stocks:
        try:
            # Fetch current price
            ticker = yf.Ticker(stock.symbol)
            info = ticker.info
            
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            
            if current_price == 0:
                logging.warning(f"Could not fetch price for {stock.symbol}")
                continue
            
            # Update current price in database
            stock.current_price = current_price
            stock.last_updated = datetime.utcnow()
            
            # Check for alerts
            alert_sent = False
            
            # Check target price
            if current_price >= stock.target_price:
                message = f"🎯 <b>{stock.symbol}</b> reached target!\n💰 Current: ${current_price:.2f}\n🎯 Target: ${stock.target_price:.2f}"
                
                # Check if alert already sent recently
                recent_alert = Alert.query.filter_by(
                    stock_symbol=stock.symbol,
                    alert_type='target',
                    is_sent=True
                ).order_by(Alert.sent_at.desc()).first()
                
                if not recent_alert or (datetime.utcnow() - recent_alert.sent_at).total_seconds() > 3600:  # 1 hour cooldown
                    if send_telegram_message(message):
                        alert = Alert(
                            stock_symbol=stock.symbol,
                            alert_type='target',
                            price=current_price,
                            message=message,
                            is_sent=True
                        )
                        db.session.add(alert)
                        alert_sent = True
            
            # Check stop loss
            elif current_price <= stock.stop_loss:
                message = f"🛑 <b>{stock.symbol}</b> hit stop loss!\n💸 Current: ${current_price:.2f}\n🛑 Stop: ${stock.stop_loss:.2f}"
                
                # Check if alert already sent recently
                recent_alert = Alert.query.filter_by(
                    stock_symbol=stock.symbol,
                    alert_type='stop_loss',
                    is_sent=True
                ).order_by(Alert.sent_at.desc()).first()
                
                if not recent_alert or (datetime.utcnow() - recent_alert.sent_at).total_seconds() > 3600:  # 1 hour cooldown
                    if send_telegram_message(message):
                        alert = Alert(
                            stock_symbol=stock.symbol,
                            alert_type='stop_loss',
                            price=current_price,
                            message=message,
                            is_sent=True
                        )
                        db.session.add(alert)
                        alert_sent = True
            
            if alert_sent:
                logging.info(f"Alert sent for {stock.symbol} at ${current_price:.2f}")
            
        except Exception as e:
            logging.error(f"Error checking stock {stock.symbol}: {e}")
    
    # Commit all changes
    db.session.commit()
    logging.info("Stock price check completed")
