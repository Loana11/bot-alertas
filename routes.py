from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from models import Stock, Alert, TelegramConfig
import yfinance as yf
import logging
from datetime import timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    """Main dashboard showing all stocks and their status"""
    stocks = Stock.query.filter_by(is_active=True).all()
    telegram_config = TelegramConfig.query.first()
    
    # Update current prices for display
    for stock in stocks:
        try:
            ticker = yf.Ticker(stock.symbol)
            info = ticker.info
            if 'regularMarketPrice' in info:
                stock.current_price = info['regularMarketPrice']
            elif 'currentPrice' in info:
                stock.current_price = info['currentPrice']
        except Exception as e:
            logging.error(f"Error fetching price for {stock.symbol}: {e}")
        # Convertir horario UTC a horario argentino (UTC-3)
    
    for stock in stocks:
        if stock.last_updated:
            stock.last_updated_local = (stock.last_updated - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            stock.last_updated_local = None

    return render_template('dashboard.html', stocks=stocks, telegram_configured=bool(telegram_config))

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
                    existing_stock.is_active = True
                else:
                    stock = Stock(
                        symbol=symbol,
                        target_price=target_price,
                        stop_loss=stop_loss,
                        current_price=current_price
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
    """Manually trigger price check"""
    try:
        from stock_monitor import check_all_stocks
        check_all_stocks()
        flash('Manual price check completed successfully!', 'success')
    except Exception as e:
        flash(f'Error during manual check: {str(e)}', 'error')
    
    return redirect(url_for('main.dashboard'))

@bp.route('/api/stock_prices')
def api_stock_prices():
    """API endpoint to get current stock prices"""
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
            logging.error(f"Error fetching price for {stock.symbol}: {e}")
            data.append({
                'symbol': stock.symbol,
                'current_price': stock.current_price,
                'target_price': stock.target_price,
                'stop_loss': stock.stop_loss,
                'status': 'error'
            })

    db.session.commit()
    return jsonify(data)

