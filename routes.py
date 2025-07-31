from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from models import Stock, Alert, TelegramConfig
import yfinance as yf
import logging
from datetime import timedelta
from stock_monitor import send_telegram_message

bp = Blueprint('main', __name__)

@bp.route('/test-alert')
def test_alert():
    success = send_telegram_message("🔔 Test de alerta desde Railway.")
    return "Mensaje enviado" if success else "Fallo el envío"
    
@bp.route('/')
def dashboard():
    from datetime import datetime
    stocks = Stock.query.filter_by(is_active=True).all()
    telegram_config = TelegramConfig.query.first()

    for stock in stocks:
        # Evaluar el estado según los precios actualizados
        if stock.current_price >= stock.target_price:
            stock.status = "target_reached"
        elif stock.current_price <= stock.stop_loss:
            stock.status = "stop_loss"
        else:
            stock.status = "monitoring"

    return render_template('dashboard.html', stocks=stocks, telegram_configured=bool(telegram_config))
    
@bp.route('/debug_price/<symbol>')
def debug_price(symbol):
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        return f"{symbol.upper()} = {price}"
    except Exception as e:
        return f"Error: {e}"
    
@bp.route('/check')
def check_prices():
    from stock_monitor import check_all_stocks
    check_all_stocks()
    return "Precios revisados"


@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for Telegram configuration and stock management"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'telegram_config':
            bot_token = request.form.get('bot_token')
            chat_id = request.form.get('chat_id')
            
            # Clear existing config
            TelegramConfig.query.delete()
            
            # Add new config
            config = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
            db.session.add(config)
            db.session.commit()
            
            flash('Telegram configuration updated successfully!', 'success')
        
        elif action == 'add_stock':
            symbol = request.form.get('symbol').upper()
            target_price = float(request.form.get('target_price'))
            stop_loss = float(request.form.get('stop_loss'))
            description = request.form.get('description', '')  # 👈 NUEVO
        
            # Validate stock symbol
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if 'regularMarketPrice' not in info and 'currentPrice' not in info:
                    raise ValueError("Invalid stock symbol")
        
                current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        
                # Check if stock already exists
                existing_stock = Stock.query.filter_by(symbol=symbol).first()
                if existing_stock:
                    existing_stock.target_price = target_price
                    existing_stock.stop_loss = stop_loss
                    existing_stock.current_price = current_price
                    existing_stock.description = description  # 👈 NUEVO
                    existing_stock.is_active = True
                else:
                    stock = Stock(
                        symbol=symbol,
                        target_price=target_price,
                        stop_loss=stop_loss,
                        current_price=current_price,
                        description=description  # 👈 NUEVO
                    )
                    db.session.add(stock)
        
                db.session.commit()
                flash(f'Stock {symbol} added/updated successfully!', 'success')
        
            except Exception as e:
                flash(f'Error adding stock {symbol}: {str(e)}', 'error')

        
        return redirect(url_for('main.settings'))
    
    # GET request
    telegram_config = TelegramConfig.query.first()
    stocks = Stock.query.filter_by(is_active=True).all()
    
    return render_template('settings.html', telegram_config=telegram_config, stocks=stocks)

@bp.route('/delete_stock/<int:stock_id>')
def delete_stock(stock_id):
    """Delete a stock from monitoring"""
    stock = Stock.query.get_or_404(stock_id)
    stock.is_active = False
    db.session.commit()
    flash(f'Stock {stock.symbol} removed from monitoring.', 'info')
    return redirect(url_for('main.settings'))

@bp.route('/alerts')
def alerts():
    """View alert history"""
    alerts = Alert.query.order_by(Alert.sent_at.desc()).limit(50).all()
    return render_template('alerts.html', alerts=alerts)

@bp.route('/manual_check')
def manual_check():
    """Manually trigger price check and update dashboard visually"""
    from stock_monitor import check_all_stocks
    from datetime import datetime

    try:
        check_all_stocks()

        # Después del chequeo, devolvemos el estado actualizado como JSON
        stocks = Stock.query.filter_by(is_active=True).all()
        data = []

        for stock in stocks:
            if stock.current_price >= stock.target_price:
                status = 'target_reached'
            elif stock.current_price <= stock.stop_loss:
                status = 'stop_loss'
            else:
                status = 'monitoring'

            data.append({
                'symbol': stock.symbol,
                'current_price': stock.current_price,
                'target_price': stock.target_price,
                'stop_loss': stock.stop_loss,
                'status': status
            })

        return jsonify(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route('/api/stock_prices')
def api_stock_prices():
    """API endpoint to get current stock prices"""
    from datetime import datetime
    stocks = Stock.query.filter_by(is_active=True).all()
    data = []

    for stock in stocks:
        try:
            ticker = yf.Ticker(stock.symbol)
            info = ticker.info
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))

            if current_price == 0:
                raise ValueError(f"Invalid price (0) for {stock.symbol}")

            # Update in database
            stock.current_price = current_price
            stock.last_updated = datetime.utcnow()

            # Estado actual
            if current_price >= stock.target_price:
                status = 'target_reached'
            elif current_price <= stock.stop_loss:
                status = 'stop_loss'
            else:
                status = 'monitoring'

            data.append({
                'symbol': stock.symbol,
                'current_price': current_price,
                'target_price': stock.target_price,
                'stop_loss': stock.stop_loss,
                'status': status
            })

        except Exception as e:
            import traceback
            logging.error(f"❌ Error fetching price for {stock.symbol}: {e}")
            traceback.print_exc()
            data.append({
                'symbol': stock.symbol,
                'current_price': stock.current_price,
                'target_price': stock.target_price,
                'stop_loss': stock.stop_loss,
                'status': 'error'
            })

    db.session.commit()
    return jsonify(data)


