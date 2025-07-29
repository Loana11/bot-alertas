import logging

# 1. Configura el logger raíz para que INFO y superiores vayan a stdout
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

# 2. Eleva el nivel de yfinance para que no inunde tus logs
logging.getLogger("yfinance").setLevel(logging.WARNING)

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from routes import bp
app.register_blueprint(bp)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///stock_monitor.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Initialize scheduler
scheduler = BackgroundScheduler()

with app.app_context():
    # Import models to ensure tables are created
    import models
    import routes
    import stock_monitor
    
    db.create_all()
    
    # Start the background scheduler
    if not scheduler.running:
        scheduler.add_job(
            func=stock_monitor.check_all_stocks,
            trigger="interval",
            minutes=30,
            id='stock_price_check'
        )
        scheduler.start()
        
    # Register routes
    app.register_blueprint(routes.bp)

from stock_monitor import check_all_stocks

@app.route("/check")
def check_prices():
    check_all_stocks()
    return "Precios revisados"

