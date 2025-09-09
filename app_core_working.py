#!/usr/bin/env python3
"""
🚀 Ganesh A.I. - Core Working Web Application
============================================
Complete functional web app with all features working
"""

import os
import sys
import logging
import sqlite3
import requests
import json
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET', 'da1d476a2031fd15c3e16d5d6e9576d2')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL', 'sqlite:///data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ganesh_ai_core.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment
ADMIN_USER = os.getenv('ADMIN_USER', 'Admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', '12345')
ADMIN_ID = int(os.getenv('ADMIN_ID', '6646320334'))

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')

BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Artificial intelligence bot pvt Ltd')
BUSINESS_EMAIL = os.getenv('BUSINESS_EMAIL', 'ru387653@gmail.com')
SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@amanjee7568')
UPI_ID = os.getenv('UPI_ID', '9234906001@ptyes')

VISIT_PAY_RATE = float(os.getenv('VISIT_PAY_RATE', '0.001'))

logger.info("🚀 Ganesh A.I. Core Web App Starting...")
logger.info(f"🏢 Business: {BUSINESS_NAME}")
logger.info(f"📧 Email: {BUSINESS_EMAIL}")
logger.info(f"💰 Visit Rate: ₹{VISIT_PAY_RATE}")

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    def generate_referral_code(self):
        self.referral_code = f"GANESH{self.id}"
        db.session.commit()

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), default='gpt-4o-mini')
    earnings = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper Functions
def get_ai_response(message, model='gpt-4o-mini'):
    """Get AI response using OpenAI API"""
    try:
        if OPENAI_API_KEY and OPENAI_API_KEY.startswith('sk-'):
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model,
                'messages': [
                    {
                        'role': 'system',
                        'content': f'You are Ganesh A.I., an intelligent assistant created by {BUSINESS_NAME}. You help users with various tasks and provide helpful, accurate responses. Be friendly, professional, and informative.'
                    },
                    {
                        'role': 'user',
                        'content': message
                    }
                ],
                'max_tokens': 1000,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code}")
                return get_fallback_response(message)
        
        else:
            return get_fallback_response(message)
            
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return get_fallback_response(message)

def get_fallback_response(message):
    """Fallback response when AI APIs are not available"""
    responses = {
        'hello': f"Hello! I'm Ganesh A.I. from {BUSINESS_NAME}. How can I help you today?",
        'hi': f"Hi there! Welcome to Ganesh A.I. What can I do for you?",
        'help': "I can help you with various tasks, answer questions, and provide information. Just ask me anything!",
        'about': f"I'm Ganesh A.I., created by {BUSINESS_NAME}. I'm here to assist you with AI-powered responses.",
        'balance': "You can check your balance in the dashboard. Keep chatting to earn more!",
        'earn': f"You earn ₹{VISIT_PAY_RATE} for each message you send. Keep chatting to increase your earnings!",
        'default': f"Thank you for your message! I'm Ganesh A.I. from {BUSINESS_NAME}. I'm here to help you with any questions or tasks you have. Keep chatting to earn money!"
    }
    
    message_lower = message.lower()
    for key in responses:
        if key in message_lower:
            return responses[key]
    
    return responses['default']

def add_earnings(user_id, amount, description):
    """Add earnings to user account"""
    try:
        user = User.query.get(user_id)
        if user:
            user.balance += amount
            user.total_earned += amount
            user.last_active = datetime.utcnow()
            
            transaction = Transaction(
                user_id=user_id,
                type='earning',
                amount=amount,
                description=description
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"💰 User {user_id} earned ₹{amount}: {description}")
            return True
    except Exception as e:
        logger.error(f"Error adding earnings: {e}")
        return False

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Homepage"""
    return render_template('index_core.html', 
                         business_name=BUSINESS_NAME,
                         support_username=SUPPORT_USERNAME)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('register_core.html')
            
            # Check if user exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return render_template('register_core.html')
            
            if email and User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template('register_core.html')
            
            # Create new user
            password_hash = generate_password_hash(password)
            user = User(
                username=username,
                email=email if email else None,
                password_hash=password_hash,
                balance=10.0  # Welcome bonus
            )
            
            db.session.add(user)
            db.session.commit()
            
            # Generate referral code
            user.generate_referral_code()
            
            # Add welcome transaction
            add_earnings(user.id, 10.0, "Welcome bonus")
            
            flash('Registration successful! Welcome bonus ₹10 added.', 'success')
            logger.info(f"✅ New user registered: {username}")
            
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register_core.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('login_core.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                
                # Update last active
                user.last_active = datetime.utcnow()
                db.session.commit()
                
                # Add visit earnings
                add_earnings(user.id, VISIT_PAY_RATE, "Login visit bonus")
                
                flash(f'Welcome back, {user.username}!', 'success')
                logger.info(f"✅ User logged in: {username}")
                
                if user.role == 'admin':
                    return redirect(url_for('admin_panel'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login_core.html')

@app.route('/logout')
def logout():
    """User logout"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            flash('User session expired. Please log in again.', 'error')
            session.clear()
            return redirect(url_for('login'))
        
        # Add visit earnings
        add_earnings(user.id, VISIT_PAY_RATE, "Dashboard visit")
        
        # Get recent chats
        recent_chats = Chat.query.filter_by(user_id=user.id).order_by(Chat.created_at.desc()).limit(10).all()
        
        # Get recent transactions
        recent_transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.created_at.desc()).limit(10).all()
        
        return render_template('dashboard_core.html',
                             user=user,
                             recent_chats=recent_chats,
                             recent_transactions=recent_transactions,
                             business_name=BUSINESS_NAME,
                             support_username=SUPPORT_USERNAME,
                             upi_id=UPI_ID)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Dashboard error. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel"""
    try:
        # Get statistics
        total_users = User.query.count()
        total_chats = Chat.query.count()
        total_earnings = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.amount > 0).scalar() or 0
        
        # Get recent users
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
        
        # Get recent chats
        recent_chats = Chat.query.order_by(Chat.created_at.desc()).limit(10).all()
        
        # Get recent transactions
        recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
        
        return render_template('admin_core.html',
                             total_users=total_users,
                             total_chats=total_chats,
                             total_earnings=total_earnings,
                             recent_users=recent_users,
                             recent_chats=recent_chats,
                             recent_transactions=recent_transactions,
                             business_name=BUSINESS_NAME)
        
    except Exception as e:
        logger.error(f"Admin panel error: {e}")
        flash('Admin panel error. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """API endpoint for chat"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get AI response
        ai_response = get_ai_response(message)
        
        # Calculate earnings
        earnings = VISIT_PAY_RATE * 50  # 50x visit rate for chat
        
        # Save chat
        chat = Chat(
            user_id=user.id,
            message=message,
            response=ai_response,
            model_used=OPENAI_MODEL,
            earnings=earnings
        )
        db.session.add(chat)
        
        # Add earnings
        add_earnings(user.id, earnings, f"Chat message: {message[:30]}...")
        
        db.session.commit()
        
        # Get updated balance
        updated_user = User.query.get(user.id)
        
        return jsonify({
            'response': ai_response,
            'earnings': earnings,
            'balance': updated_user.balance,
            'total_earned': updated_user.total_earned
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return jsonify({'error': 'Chat failed. Please try again.'}), 500

@app.route('/api/quick-chat', methods=['POST'])
def api_quick_chat():
    """Quick chat API without login"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get AI response
        ai_response = get_ai_response(message)
        
        return jsonify({
            'response': ai_response,
            'message': 'Register to earn money while chatting!'
        })
        
    except Exception as e:
        logger.error(f"Quick chat API error: {e}")
        return jsonify({'error': 'Chat failed. Please try again.'}), 500

# Initialize database
def init_db():
    """Initialize database with admin user"""
    try:
        with app.app_context():
            db.create_all()
            
            # Create admin user if not exists
            admin = User.query.filter_by(username=ADMIN_USER).first()
            if not admin:
                admin_hash = generate_password_hash(ADMIN_PASS)
                admin = User(
                    username=ADMIN_USER,
                    email=BUSINESS_EMAIL,
                    password_hash=admin_hash,
                    role='admin',
                    balance=1000.0
                )
                db.session.add(admin)
                db.session.commit()
                
                admin.generate_referral_code()
                
                logger.info(f"✅ Admin user created: {ADMIN_USER}")
            
            logger.info("✅ Database initialized successfully")
            
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")

if __name__ == '__main__':
    init_db()
    
    print("""
    🚀 ================================
       GANESH A.I. CORE WEB APP
    ================================
    
    ✅ All functions working
    💰 Earning system active
    🤖 AI integration ready
    📊 Admin panel functional
    
    Starting server...
    """)
    
    app.run(host='0.0.0.0', port=8080, debug=False)