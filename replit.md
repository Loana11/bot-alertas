# Stock Monitor Application

## Overview

This is a Flask-based stock monitoring application that tracks stock prices and sends Telegram alerts when target prices or stop-loss levels are reached. The application uses Yahoo Finance API for real-time stock data and includes a background scheduler for automated monitoring.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM
- **Database**: SQLite by default (configurable via DATABASE_URL environment variable)
- **Background Processing**: APScheduler for automated stock price monitoring every 30 minutes
- **API Integration**: Yahoo Finance (yfinance) for stock price data
- **Notification System**: Telegram Bot API for sending alerts

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **UI Framework**: Bootstrap 5 with dark theme
- **Icons**: Font Awesome
- **JavaScript**: Vanilla JavaScript for real-time price updates and interactive features

### Database Schema
- **Stock**: Stores stock symbols, target prices, stop-loss levels, and current prices
- **Alert**: Tracks sent alerts for audit purposes
- **TelegramConfig**: Stores Telegram bot configuration (token and chat ID)

## Key Components

### 1. Stock Monitoring System
- **Purpose**: Automated monitoring of stock prices against user-defined targets
- **Implementation**: Background scheduler checks all active stocks every 30 minutes
- **Alert Logic**: Triggers notifications when prices reach target or stop-loss levels

### 2. Telegram Integration
- **Purpose**: Real-time notifications to users via Telegram
- **Configuration**: Bot token and chat ID stored in database
- **Message Format**: HTML-formatted messages with stock details and price information

### 3. Web Dashboard
- **Purpose**: User interface for managing stocks and viewing current status
- **Features**: Real-time price display, progress indicators, manual refresh capability
- **Responsive Design**: Mobile-friendly interface with Bootstrap

### 4. Settings Management
- **Purpose**: Configuration of Telegram bot and stock portfolio
- **Features**: Add/remove stocks, configure alert thresholds, manage Telegram settings

## Data Flow

1. **Stock Price Monitoring**:
   - Background scheduler triggers every 30 minutes
   - Fetches current prices from Yahoo Finance API
   - Compares against target/stop-loss levels
   - Generates alerts when thresholds are crossed

2. **User Interaction**:
   - Web interface displays current portfolio status
   - Users can add/remove stocks and configure alerts
   - Manual price refresh available via AJAX calls

3. **Alert Generation**:
   - Alerts created in database when price thresholds met
   - Telegram messages sent via bot API
   - Alert history maintained for audit purposes

## External Dependencies

### APIs and Services
- **Yahoo Finance API**: Stock price data (via yfinance library)
- **Telegram Bot API**: Message delivery system
- **Requirements**: Internet connectivity for API calls

### Python Libraries
- Flask and Flask-SQLAlchemy for web framework
- APScheduler for background tasks
- yfinance for stock data
- requests for HTTP API calls

## Deployment Strategy

### Environment Configuration
- **Database**: Configurable via DATABASE_URL (defaults to SQLite)
- **Session Security**: SESSION_SECRET environment variable
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

### Production Considerations
- SQLite suitable for development; PostgreSQL recommended for production
- Background scheduler runs within Flask application
- Logging configured for debugging and monitoring
- Database connection pooling enabled for reliability

### Scaling Approach
- Single-instance deployment with SQLite for simplicity
- Can be scaled to use external database (PostgreSQL) for multi-instance deployments
- Background tasks currently tied to Flask app instance