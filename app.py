"""
Entry point for Render deployment
"""
import os
import sys
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for production
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('DEBUG', 'False')

# Import the Flask app from main module
try:
    logger.info("Importing Flask app from main module...")
    from main import app
    logger.info("✅ Flask app imported successfully")
    
    # Initialize the app context for database setup
    with app.app_context():
        try:
            from main import db, User, ADMIN_USER, ADMIN_PASS, BUSINESS_EMAIL
            
            # Drop and recreate database tables for fresh start
            db.drop_all()
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Create admin user if not exists
            admin_user = User.query.filter_by(username=ADMIN_USER).first()
            if not admin_user:
                admin_user = User(
                    username=ADMIN_USER,
                    email=BUSINESS_EMAIL,
                    role='admin'
                )
                admin_user.set_password(ADMIN_PASS)
                db.session.add(admin_user)
                db.session.commit()  # Commit first to get ID
                admin_user.generate_referral_code()
                db.session.commit()  # Commit again to save referral code
                logger.info(f"Admin user '{ADMIN_USER}' created successfully")
            else:
                logger.info(f"Admin user '{ADMIN_USER}' already exists")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            
except ImportError as e:
    logger.error(f"❌ Failed to import Flask app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)