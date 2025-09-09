#!/usr/bin/env python3
"""
🚀 Ganesh A.I. - Production Startup Script
==========================================
This script starts the complete Ganesh AI system with all features
"""

import os
import sys
import subprocess
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STARTUP - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import flask
        import telegram
        import openai
        import sqlalchemy
        import requests
        logger.info("✅ All core dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        return False

def setup_environment():
    """Setup environment variables"""
    if not os.path.exists('.env'):
        logger.error("❌ .env file not found!")
        return False
    
    logger.info("✅ Environment file found")
    return True

def start_application():
    """Start the Ganesh AI application"""
    try:
        logger.info("🚀 Starting Ganesh A.I. Production System...")
        
        # Import and run the main application
        from ganesh_ai_production import app, init_database, setup_scheduler, setup_telegram_webhook
        
        logger.info("📊 Initializing database...")
        init_database()
        
        logger.info("⏰ Setting up background scheduler...")
        setup_scheduler()
        
        logger.info("🤖 Setting up Telegram webhook...")
        setup_telegram_webhook()
        
        logger.info("🌐 Starting web server...")
        
        # Get port from environment or use default
        port = int(os.getenv('PORT', 12000))
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {str(e)}")
        return False

def main():
    """Main startup function"""
    print("""
    🤖 ================================
       GANESH A.I. STARTUP SYSTEM
    ================================
    
    🚀 Production-Ready AI Platform
    💰 Revenue Generation System
    🤖 Telegram Bot Integration
    👨‍💼 Admin Panel
    📊 Analytics Dashboard
    
    Starting system...
    """)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed!")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        logger.error("❌ Environment setup failed!")
        sys.exit(1)
    
    # Start application
    logger.info("🎯 All checks passed. Starting application...")
    start_application()

if __name__ == '__main__':
    main()