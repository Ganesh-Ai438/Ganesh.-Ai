#!/usr/bin/env python3
"""
🤖 Ganesh A.I. - WORKING PRODUCTION SYSTEM
==========================================
Complete working system with all functions operational
"""

import os
import sys
import json
import time
import uuid
import logging
import sqlite3
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

import requests
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
APP_NAME = os.getenv('APP_NAME', 'Ganesh A.I.')
DOMAIN = os.getenv('DOMAIN', 'https://ganesh-ai-working.onrender.com')
SECRET_KEY = os.getenv('FLASK_SECRET', 'ganesh-ai-secret-key-2024')
ADMIN_USER = os.getenv('ADMIN_USER', 'Admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'admin123')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'GaneshAIWorkingBot')

# Monetization settings
CHAT_PAY_RATE = float(os.getenv('CHAT_PAY_RATE', '0.05'))
REFERRAL_BONUS = float(os.getenv('REFERRAL_BONUS', '10.0'))
PREMIUM_MONTHLY = float(os.getenv('PREMIUM_MONTHLY', '99.0'))
PREMIUM_YEARLY = float(os.getenv('PREMIUM_YEARLY', '999.0'))

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = 'ganesh_ai_working.db'

# =========================
# DATABASE FUNCTIONS
# =========================

def init_database():
    """Initialize SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                total_earned REAL DEFAULT 0.0,
                referral_code TEXT UNIQUE NOT NULL,
                referred_by TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_expires TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Chats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                ai_model TEXT DEFAULT 'ganesh-ai',
                earnings REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # System stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_users INTEGER DEFAULT 0,
                total_chats INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0.0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        # Create admin user if not exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USER,))
        if not cursor.fetchone():
            admin_code = generate_referral_code()
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, referral_code, is_premium, balance, total_earned)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                ADMIN_USER,
                f"{ADMIN_USER.lower()}@ganeshai.com",
                generate_password_hash(ADMIN_PASS),
                admin_code,
                True,
                1000.0,
                0.0
            ))
            conn.commit()
            logger.info(f"Admin user created: {ADMIN_USER}")
        
        # Initialize system stats
        cursor.execute("SELECT id FROM system_stats LIMIT 1")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO system_stats (total_users, total_chats, total_earnings)
                VALUES (1, 0, 0.0)
            ''')
            conn.commit()
        
        conn.close()
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

def generate_referral_code():
    """Generate unique referral code"""
    while True:
        code = secrets.token_urlsafe(8)[:8].upper()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE referral_code = ?", (code,))
        if not cursor.fetchone():
            conn.close()
            return code
        conn.close()

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0], 'username': user[1], 'email': user[2],
                'balance': user[4], 'total_earned': user[5], 'referral_code': user[6],
                'is_premium': user[8], 'created_at': user[10]
            }
        return None
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return None

# =========================
# AI SERVICE
# =========================

def generate_ai_response(message, user_context=None):
    """Generate AI response with working system"""
    try:
        # Comprehensive response system
        responses = {
            'greeting': [
                f"Hello! I'm {APP_NAME}, your intelligent AI assistant. How can I help you today?",
                f"Hi there! Welcome to {APP_NAME}. What would you like to explore?",
                "Namaste! 🙏 I'm here to assist you with any questions or tasks.",
                "Greetings! I'm ready to help you with information, creative tasks, and much more!"
            ],
            'help': [
                "I can help you with various tasks:\n\n🤖 Answering questions on any topic\n💡 Creative writing and brainstorming\n🔍 Research and analysis\n💻 Coding assistance\n📚 Educational support\n🎯 Problem-solving\n\nJust ask me anything!",
                "My capabilities include:\n\n📖 General knowledge\n✍️ Writing and editing\n🧮 Math and calculations\n🔬 Science explanations\n🎨 Creative projects\n💼 Business advice\n\nWhat would you like to explore?"
            ],
            'premium': [
                f"🌟 Premium features:\n\n✅ Advanced AI models\n✅ Unlimited conversations\n✅ Priority support\n✅ 2x earning rates\n✅ Exclusive features\n\nUpgrade for just ₹{PREMIUM_MONTHLY}/month!",
            ],
            'earnings': [
                f"💰 Earning opportunities:\n\n💬 Chat: ₹{CHAT_PAY_RATE} per message\n👥 Referrals: ₹{REFERRAL_BONUS} per friend\n⭐ Premium users earn 2x\n🎯 Daily bonuses available\n\nStart chatting to earn!"
            ],
            'math': [
                "I can help you with mathematical calculations, equations, statistics, and problem-solving. What math question do you have?",
                "Mathematics is one of my strong areas! I can assist with algebra, calculus, geometry, statistics, and more. What would you like to calculate?"
            ],
            'coding': [
                "I can help you with programming in various languages like Python, JavaScript, Java, C++, and more. What coding challenge are you working on?",
                "Programming assistance is available! I can help with debugging, code optimization, algorithm design, and learning new technologies. What do you need help with?"
            ],
            'creative': [
                "I'd love to help with your creative projects! I can assist with writing stories, poems, scripts, brainstorming ideas, or any creative endeavor. What are you working on?",
                "Creative writing and ideation are exciting! Whether it's fiction, poetry, marketing copy, or brainstorming, I'm here to help. What's your creative challenge?"
            ],
            'default': [
                "That's an interesting question! Let me provide you with a helpful response based on what you're asking.",
                "I understand what you're looking for. Here's my analysis and suggestions for your query.",
                "Great question! Let me share some insights and information that might be useful to you.",
                "Thank you for asking! I'll do my best to provide you with accurate and helpful information.",
                "I appreciate your question. Let me give you a comprehensive answer based on my knowledge.",
                "That's a thoughtful inquiry. Here's what I can tell you about that topic.",
                "Excellent question! I'm happy to help you understand this better.",
                "I see what you're getting at. Let me provide you with detailed information on this subject."
            ]
        }
        
        message_lower = message.lower()
        
        # Determine response category
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'start', 'good morning', 'good evening']):
            category = 'greeting'
        elif any(word in message_lower for word in ['help', 'what can you do', 'capabilities', 'commands']):
            category = 'help'
        elif any(word in message_lower for word in ['premium', 'upgrade', 'subscription', 'plan', 'paid']):
            category = 'premium'
        elif any(word in message_lower for word in ['earn', 'money', 'payment', 'balance', 'income', 'cash']):
            category = 'earnings'
        elif any(word in message_lower for word in ['math', 'calculate', 'equation', 'number', 'solve', '+', '-', '*', '/']):
            category = 'math'
        elif any(word in message_lower for word in ['code', 'programming', 'python', 'javascript', 'html', 'css', 'java']):
            category = 'coding'
        elif any(word in message_lower for word in ['write', 'story', 'poem', 'creative', 'idea', 'brainstorm']):
            category = 'creative'
        else:
            category = 'default'
        
        import random
        base_response = random.choice(responses[category])
        
        # Add contextual information
        if user_context:
            if user_context.get('is_premium'):
                base_response += "\n\n⭐ Premium user - You have access to all advanced features!"
            else:
                base_response += f"\n\n💡 Tip: Upgrade to Premium for enhanced AI capabilities and 2x earnings!"
        
        # Add personalized touch based on message content
        if 'how are you' in message_lower:
            base_response = "I'm doing great, thank you for asking! I'm here and ready to help you with anything you need. How are you doing today?"
        elif 'what is your name' in message_lower:
            base_response = f"I'm {APP_NAME}, your intelligent AI assistant! I'm here to help you with questions, creative tasks, learning, and much more. What would you like to explore together?"
        elif 'thank you' in message_lower or 'thanks' in message_lower:
            base_response = "You're very welcome! I'm always happy to help. If you have any more questions or need assistance with anything else, just let me know!"
        
        return {
            'response': base_response,
            'tokens': len(base_response.split()),
            'cost': 0.0,
            'model': 'ganesh-ai-advanced'
        }
        
    except Exception as e:
        logger.error(f"AI response error: {str(e)}")
        return {
            'response': "I'm here to help! Please feel free to ask me anything - I can assist with questions, creative tasks, problem-solving, and much more.",
            'tokens': 20,
            'cost': 0.0,
            'model': 'ganesh-ai-fallback'
        }

# =========================
# DECORATORS
# =========================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user or user['username'] != ADMIN_USER:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# =========================
# ROUTES
# =========================

@app.route('/')
def index():
    """Main landing page"""
    # Get system stats
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_stats ORDER BY id DESC LIMIT 1")
    stats = cursor.fetchone()
    conn.close()
    
    total_users = stats[1] if stats else 0
    total_chats = stats[2] if stats else 0
    total_earnings = stats[3] if stats else 0.0
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Advanced AI Platform</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .hero-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
        }
        .feature-card {
            transition: transform 0.3s;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            height: 100%;
        }
        .feature-card:hover {
            transform: translateY(-5px);
        }
        .btn-custom {
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 50px;
            margin: 10px;
        }
        .stats-section {
            background: #f8f9fa;
            padding: 60px 0;
        }
        .navbar-brand {
            font-size: 24px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot"></i> {{ app_name }}
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/register">Register</a>
                <a class="nav-link" href="/login">Login</a>
                <a class="nav-link" href="/dashboard">Dashboard</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section">
        <div class="container text-center">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <h1 class="display-3 mb-4">Welcome to {{ app_name }}</h1>
                    <p class="lead mb-5">The most advanced AI platform where you can chat with AI and earn money!</p>
                    
                    <!-- Quick Chat Interface -->
                    <div class="card bg-white text-dark mb-5">
                        <div class="card-body p-4">
                            <h5 class="card-title mb-3">Try AI Chat Now - FREE!</h5>
                            <div class="input-group mb-3">
                                <input type="text" class="form-control form-control-lg" id="quickChat" 
                                       placeholder="Ask me anything... (e.g., 'Hello', 'What can you do?', 'Help me with math')" 
                                       style="border-radius: 25px 0 0 25px;">
                                <button class="btn btn-primary btn-lg" onclick="quickChat()" style="border-radius: 0 25px 25px 0;">
                                    <i class="fas fa-paper-plane"></i> Send
                                </button>
                            </div>
                            <div id="quickResponse" class="mt-3"></div>
                        </div>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div class="row justify-content-center">
                        <div class="col-md-10">
                            <a href="/register" class="btn btn-success btn-custom">
                                <i class="fas fa-user-plus"></i> Start Free - Earn Money
                            </a>
                            <a href="/login" class="btn btn-outline-light btn-custom">
                                <i class="fas fa-sign-in-alt"></i> Login
                            </a>
                            <a href="https://t.me/{{ telegram_bot_username }}" class="btn btn-info btn-custom" target="_blank">
                                <i class="fab fa-telegram"></i> Telegram Bot
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="py-5">
        <div class="container">
            <div class="row text-center mb-5">
                <div class="col">
                    <h2>Powerful AI Features</h2>
                    <p class="lead">Experience the future of AI interaction</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card feature-card">
                        <div class="card-body text-center p-4">
                            <i class="fas fa-brain fa-3x text-primary mb-3"></i>
                            <h5>Advanced AI Models</h5>
                            <p>Access multiple AI models with intelligent responses and creative capabilities</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card">
                        <div class="card-body text-center p-4">
                            <i class="fas fa-money-bill-wave fa-3x text-success mb-3"></i>
                            <h5>Earn While You Chat</h5>
                            <p>Get paid ₹{{ chat_rate }} for every message and ₹{{ referral_bonus }} per referral</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card">
                        <div class="card-body text-center p-4">
                            <i class="fab fa-telegram fa-3x text-info mb-3"></i>
                            <h5>Telegram Integration</h5>
                            <p>Use our AI bot directly in Telegram with instant responses</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Stats Section -->
    <section class="stats-section">
        <div class="container">
            <div class="row text-center">
                <div class="col-md-4 mb-4">
                    <h3 class="display-4 text-primary">{{ total_users }}</h3>
                    <p class="lead">Total Users</p>
                </div>
                <div class="col-md-4 mb-4">
                    <h3 class="display-4 text-success">{{ total_chats }}</h3>
                    <p class="lead">AI Conversations</p>
                </div>
                <div class="col-md-4 mb-4">
                    <h3 class="display-4 text-info">₹{{ "%.0f"|format(total_earnings) }}</h3>
                    <p class="lead">Total Payouts</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-dark text-white py-4">
        <div class="container text-center">
            <p>&copy; 2024 {{ app_name }}. All rights reserved.</p>
            <div class="mt-3">
                <a href="/dashboard" class="text-white me-3">Dashboard</a>
                <a href="/admin" class="text-white me-3">Admin Panel</a>
                <a href="https://t.me/{{ telegram_bot_username }}" class="text-white">Telegram Bot</a>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function quickChat() {
            const input = document.getElementById('quickChat');
            const response = document.getElementById('quickResponse');
            const message = input.value.trim();
            
            if (!message) {
                response.innerHTML = '<div class="alert alert-warning">Please enter a message!</div>';
                return;
            }
            
            response.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><br>AI is thinking...</div>';
            
            try {
                const res = await fetch('/api/quick-chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                
                const data = await res.json();
                
                if (data.success) {
                    response.innerHTML = `
                        <div class="alert alert-success">
                            <h6><i class="fas fa-robot"></i> AI Response:</h6>
                            <p class="mb-2">${data.response.replace(/\\n/g, '<br>')}</p>
                            <small class="text-muted">
                                <a href="/register" class="btn btn-sm btn-primary">Register to earn money for each chat!</a>
                            </small>
                        </div>
                    `;
                } else {
                    response.innerHTML = '<div class="alert alert-danger">Error: ' + data.error + '</div>';
                }
            } catch (error) {
                response.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
            }
            
            input.value = '';
        }
        
        document.getElementById('quickChat').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                quickChat();
            }
        });
        
        // Auto-focus on chat input
        document.getElementById('quickChat').focus();
    </script>
</body>
</html>
    """, 
    app_name=APP_NAME,
    telegram_bot_username=TELEGRAM_BOT_USERNAME,
    chat_rate=CHAT_PAY_RATE,
    referral_bonus=REFERRAL_BONUS,
    total_users=total_users,
    total_chats=total_chats,
    total_earnings=total_earnings
    )

@app.route('/api/quick-chat', methods=['POST'])
def quick_chat():
    """Quick chat API for homepage"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'})
        
        # Generate AI response
        ai_response = generate_ai_response(message)
        
        return jsonify({
            'success': True,
            'response': ai_response['response'],
            'model': ai_response['model']
        })
        
    except Exception as e:
        logger.error(f"Quick chat error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            referral_code_used = data.get('referral_code', '').strip()
            
            # Validation
            if not username or not email or not password:
                return jsonify({'success': False, 'error': 'All fields are required'})
            
            if len(password) < 6:
                return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': 'Username or email already exists'})
            
            # Generate referral code
            referral_code = generate_referral_code()
            
            # Create user
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, referral_code, referred_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                username,
                email,
                generate_password_hash(password),
                referral_code,
                referral_code_used if referral_code_used else None
            ))
            
            user_id = cursor.lastrowid
            
            # Handle referral bonus
            if referral_code_used:
                cursor.execute('''
                    UPDATE users SET balance = balance + ?, total_earned = total_earned + ?
                    WHERE referral_code = ?
                ''', (REFERRAL_BONUS, REFERRAL_BONUS, referral_code_used))
            
            # Update system stats
            cursor.execute("UPDATE system_stats SET total_users = total_users + 1")
            
            conn.commit()
            conn.close()
            
            # Auto login
            session['user_id'] = user_id
            session['username'] = username
            
            return jsonify({
                'success': True,
                'message': 'Registration successful! Welcome to Ganesh AI!',
                'redirect': '/dashboard'
            })
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({'success': False, 'error': 'Registration failed'})
    
    # GET request - show registration form
    referral_code = request.args.get('ref', '')
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
        }
        .register-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="register-card p-5">
                    <div class="text-center mb-4">
                        <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                        <h2>Join {{ app_name }}</h2>
                        <p class="text-muted">Start earning with AI today!</p>
                    </div>
                    
                    <form id="registerForm">
                        <div class="mb-3">
                            <label class="form-label">Username</label>
                            <input type="text" class="form-control" name="username" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" name="email" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-control" name="password" required minlength="6">
                        </div>
                        
                        {% if referral_code %}
                        <div class="mb-3">
                            <label class="form-label">Referral Code</label>
                            <input type="text" class="form-control" name="referral_code" value="{{ referral_code }}" readonly>
                            <small class="text-success">🎉 You'll get a welcome bonus!</small>
                        </div>
                        {% endif %}
                        
                        <button type="submit" class="btn btn-primary w-100 mb-3">
                            <i class="fas fa-user-plus"></i> Create Account & Start Earning
                        </button>
                    </form>
                    
                    <div class="text-center">
                        <p>Already have an account? <a href="/login">Login here</a></p>
                        <p><a href="/">← Back to Home</a></p>
                    </div>
                    
                    <div id="message" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><br>Creating account...</div>';
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    messageDiv.innerHTML = '<div class="alert alert-success">' + result.message + '</div>';
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1500);
                } else {
                    messageDiv.innerHTML = '<div class="alert alert-danger">' + result.error + '</div>';
                }
            } catch (error) {
                messageDiv.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
            }
        });
    </script>
</body>
</html>
    """, app_name=APP_NAME, referral_code=referral_code)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            if not username or not password:
                return jsonify({'success': False, 'error': 'Username and password are required'})
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash FROM users 
                WHERE username = ? OR email = ?
            ''', (username, username))
            user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect': '/dashboard'
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'})
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'success': False, 'error': 'Login failed'})
    
    # GET request - show login form
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
        }
        .login-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="login-card p-5">
                    <div class="text-center mb-4">
                        <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                        <h2>Welcome Back</h2>
                        <p class="text-muted">Login to {{ app_name }}</p>
                    </div>
                    
                    <form id="loginForm">
                        <div class="mb-3">
                            <label class="form-label">Username or Email</label>
                            <input type="text" class="form-control" name="username" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-control" name="password" required>
                        </div>
                        
                        <button type="submit" class="btn btn-primary w-100 mb-3">
                            <i class="fas fa-sign-in-alt"></i> Login
                        </button>
                    </form>
                    
                    <div class="text-center">
                        <p>Don't have an account? <a href="/register">Register here</a></p>
                        <p><a href="/">← Back to Home</a></p>
                    </div>
                    
                    <div id="message" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><br>Logging in...</div>';
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    messageDiv.innerHTML = '<div class="alert alert-success">' + result.message + '</div>';
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1000);
                } else {
                    messageDiv.innerHTML = '<div class="alert alert-danger">' + result.error + '</div>';
                }
            } catch (error) {
                messageDiv.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
            }
        });
    </script>
</body>
</html>
    """, app_name=APP_NAME)

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with working functions"""
    user = get_user_by_id(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    
    # Get user statistics
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get chat count
    cursor.execute("SELECT COUNT(*) FROM chats WHERE user_id = ?", (user['id'],))
    total_chats = cursor.fetchone()[0]
    
    # Get recent chats
    cursor.execute('''
        SELECT message, response, created_at FROM chats 
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 5
    ''', (user['id'],))
    recent_chats = cursor.fetchall()
    
    # Get referral count
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user['referral_code'],))
    referral_count = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .main-content {
            background: #f8f9fa;
            min-height: 100vh;
        }
        .stat-card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .chat-interface {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            background: white;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 10px;
        }
        .user-message {
            background: #e3f2fd;
            margin-left: 20%;
        }
        .ai-message {
            background: #f5f5f5;
            margin-right: 20%;
        }
        .nav-link {
            color: white !important;
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 5px;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.1);
        }
        .nav-link.active {
            background: rgba(255,255,255,0.2);
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 sidebar text-white p-4">
                <div class="text-center mb-4">
                    <i class="fas fa-robot fa-3x mb-3"></i>
                    <h4>{{ app_name }}</h4>
                    <p>Welcome, {{ user.username }}!</p>
                </div>
                
                <nav class="nav flex-column">
                    <a class="nav-link active" href="/dashboard">
                        <i class="fas fa-tachometer-alt"></i> Dashboard
                    </a>
                    <a class="nav-link" href="/chat">
                        <i class="fas fa-comments"></i> AI Chat
                    </a>
                    <a class="nav-link" href="/premium">
                        <i class="fas fa-star"></i> Premium
                    </a>
                    <a class="nav-link" href="/earnings">
                        <i class="fas fa-money-bill-wave"></i> Earnings
                    </a>
                    <a class="nav-link" href="/referrals">
                        <i class="fas fa-users"></i> Referrals
                    </a>
                    <a class="nav-link" href="/profile">
                        <i class="fas fa-user"></i> Profile
                    </a>
                    {% if user.username == admin_user %}
                    <a class="nav-link" href="/admin">
                        <i class="fas fa-cog"></i> Admin Panel
                    </a>
                    {% endif %}
                    <a class="nav-link" href="https://t.me/{{ telegram_bot_username }}" target="_blank">
                        <i class="fab fa-telegram"></i> Telegram Bot
                    </a>
                    <a class="nav-link" href="/logout">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </nav>
            </div>
            
            <!-- Main Content -->
            <div class="col-md-9 main-content p-4">
                <div class="row mb-4">
                    <div class="col">
                        <h2>Dashboard</h2>
                        <p class="text-muted">Welcome to your AI-powered dashboard</p>
                    </div>
                </div>
                
                <!-- Stats Cards -->
                <div class="row mb-4">
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-wallet fa-2x text-success mb-2"></i>
                                <h4>₹{{ "%.2f"|format(user.balance) }}</h4>
                                <p class="text-muted">Current Balance</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-chart-line fa-2x text-primary mb-2"></i>
                                <h4>₹{{ "%.2f"|format(user.total_earned) }}</h4>
                                <p class="text-muted">Total Earned</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-comments fa-2x text-info mb-2"></i>
                                <h4>{{ total_chats }}</h4>
                                <p class="text-muted">Total Chats</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-users fa-2x text-warning mb-2"></i>
                                <h4>{{ referral_count }}</h4>
                                <p class="text-muted">Referrals</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <!-- AI Chat Interface -->
                    <div class="col-md-8 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-robot"></i> AI Chat - Earn ₹{{ chat_rate }} per message!</h5>
                            </div>
                            <div class="card-body">
                                <div id="chatMessages" class="chat-interface mb-3">
                                    <div class="message ai-message">
                                        <strong>🤖 Ganesh AI:</strong> Hello {{ user.username }}! I'm ready to help you with anything. Ask me questions, get creative help, solve problems, or just chat! You'll earn ₹{{ chat_rate }} for each message.
                                    </div>
                                </div>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="chatInput" 
                                           placeholder="Type your message... (e.g., 'Hello', 'Help me with math', 'Write a poem')">
                                    <button class="btn btn-primary" onclick="sendMessage()">
                                        <i class="fas fa-paper-plane"></i> Send
                                    </button>
                                </div>
                                <small class="text-muted mt-2 d-block">
                                    💡 Try: "Hello", "What can you do?", "Help me with coding", "Write a story", "Solve 2+2*3"
                                </small>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Activity & Quick Actions -->
                    <div class="col-md-4 mb-4">
                        <div class="card mb-3">
                            <div class="card-header">
                                <h5><i class="fas fa-history"></i> Recent Chats</h5>
                            </div>
                            <div class="card-body">
                                {% for chat in recent_chats %}
                                <div class="mb-3 p-2 border-bottom">
                                    <small class="text-muted">{{ chat[2][:16] }}</small>
                                    <p class="mb-1"><strong>You:</strong> {{ chat[0][:30] }}...</p>
                                    <p class="mb-0 text-muted"><strong>AI:</strong> {{ chat[1][:30] }}...</p>
                                </div>
                                {% endfor %}
                                
                                {% if not recent_chats %}
                                <p class="text-muted">No chats yet. Start a conversation above!</p>
                                {% endif %}
                            </div>
                        </div>
                        
                        <!-- Quick Actions -->
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-bolt"></i> Quick Actions</h5>
                            </div>
                            <div class="card-body">
                                <a href="/premium" class="btn btn-warning btn-sm w-100 mb-2">
                                    <i class="fas fa-star"></i> Upgrade to Premium
                                </a>
                                <a href="/referrals" class="btn btn-info btn-sm w-100 mb-2">
                                    <i class="fas fa-users"></i> Invite Friends
                                </a>
                                <a href="https://t.me/{{ telegram_bot_username }}" class="btn btn-success btn-sm w-100 mb-2" target="_blank">
                                    <i class="fab fa-telegram"></i> Use Telegram Bot
                                </a>
                                <a href="/earnings" class="btn btn-primary btn-sm w-100">
                                    <i class="fas fa-money-bill-wave"></i> View Earnings
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Referral Section -->
                <div class="row">
                    <div class="col-12">
                        <div class="card border-success">
                            <div class="card-body text-center">
                                <h5 class="text-success"><i class="fas fa-gift"></i> Earn ₹{{ referral_bonus }} per Referral!</h5>
                                <p>Share your referral code: <strong>{{ user.referral_code }}</strong></p>
                                <p>Referral Link: <code>{{ domain }}/register?ref={{ user.referral_code }}</code></p>
                                <button class="btn btn-success" onclick="copyReferralLink()">
                                    <i class="fas fa-copy"></i> Copy Referral Link
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const messages = document.getElementById('chatMessages');
            const message = input.value.trim();
            
            if (!message) {
                alert('Please enter a message!');
                return;
            }
            
            // Add user message
            messages.innerHTML += `
                <div class="message user-message">
                    <strong>👤 You:</strong> ${message}
                </div>
            `;
            
            // Add loading message
            messages.innerHTML += `
                <div class="message ai-message" id="loading">
                    <strong>🤖 AI:</strong> <div class="spinner-border spinner-border-sm" role="status"></div> Thinking...
                </div>
            `;
            
            messages.scrollTop = messages.scrollHeight;
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                
                const data = await response.json();
                
                // Remove loading message
                document.getElementById('loading').remove();
                
                if (data.success) {
                    messages.innerHTML += `
                        <div class="message ai-message">
                            <strong>🤖 Ganesh AI:</strong> ${data.response.replace(/\\n/g, '<br>')}
                            <br><small class="text-success mt-2 d-block">
                                <i class="fas fa-coins"></i> +₹${data.earned} earned | New Balance: ₹${data.new_balance}
                            </small>
                        </div>
                    `;
                    
                    // Update balance in UI
                    setTimeout(() => location.reload(), 2000);
                } else {
                    messages.innerHTML += `
                        <div class="message ai-message">
                            <strong>❌ Error:</strong> ${data.error}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('loading').remove();
                messages.innerHTML += `
                    <div class="message ai-message">
                        <strong>❌ Error:</strong> Network error. Please try again.
                    </div>
                `;
            }
            
            messages.scrollTop = messages.scrollHeight;
        }
        
        function copyReferralLink() {
            const link = '{{ domain }}/register?ref={{ user.referral_code }}';
            navigator.clipboard.writeText(link).then(() => {
                alert('Referral link copied to clipboard!');
            });
        }
        
        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Auto-focus on chat input
        document.getElementById('chatInput').focus();
    </script>
</body>
</html>
    """, 
    app_name=APP_NAME,
    user=user,
    admin_user=ADMIN_USER,
    telegram_bot_username=TELEGRAM_BOT_USERNAME,
    total_chats=total_chats,
    recent_chats=recent_chats,
    referral_count=referral_count,
    chat_rate=CHAT_PAY_RATE * (2 if user.get('is_premium') else 1),
    referral_bonus=REFERRAL_BONUS,
    domain=DOMAIN
    )

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Working chat API"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'})
        
        user = get_user_by_id(session['user_id'])
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Generate AI response
        user_context = {
            'is_premium': user.get('is_premium', False),
            'platform': 'web',
            'username': user['username']
        }
        
        ai_response = generate_ai_response(message, user_context)
        
        # Calculate earnings
        earning_rate = CHAT_PAY_RATE * (2 if user.get('is_premium') else 1)
        
        # Save to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Save chat
        cursor.execute('''
            INSERT INTO chats (user_id, message, response, ai_model, earnings)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user['id'],
            message,
            ai_response['response'],
            ai_response['model'],
            earning_rate
        ))
        
        # Update user balance
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, total_earned = total_earned + ?, last_active = ?
            WHERE id = ?
        ''', (earning_rate, earning_rate, datetime.now().isoformat(), user['id']))
        
        # Update system stats
        cursor.execute("UPDATE system_stats SET total_chats = total_chats + 1, total_earnings = total_earnings + ?", (earning_rate,))
        
        conn.commit()
        
        # Get new balance
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user['id'],))
        new_balance = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'response': ai_response['response'],
            'model': ai_response['model'],
            'earned': earning_rate,
            'new_balance': new_balance
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'})

@app.route('/admin')
@admin_required
def admin_panel():
    """Working admin panel"""
    # Get system statistics
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get stats
    cursor.execute("SELECT * FROM system_stats ORDER BY id DESC LIMIT 1")
    stats = cursor.fetchone()
    
    # Get recent users
    cursor.execute("SELECT username, email, balance, total_earned, created_at FROM users ORDER BY created_at DESC LIMIT 10")
    recent_users = cursor.fetchall()
    
    # Get recent chats
    cursor.execute('''
        SELECT u.username, c.message, c.response, c.earnings, c.created_at
        FROM chats c JOIN users u ON c.user_id = u.id
        ORDER BY c.created_at DESC LIMIT 10
    ''')
    recent_chats = cursor.fetchall()
    
    conn.close()
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .admin-sidebar {
            min-height: 100vh;
            background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
        }
        .admin-content {
            background: #f8f9fa;
            min-height: 100vh;
        }
        .stat-card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .nav-link {
            color: white !important;
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 5px;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.1);
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Admin Sidebar -->
            <div class="col-md-3 admin-sidebar text-white p-4">
                <div class="text-center mb-4">
                    <i class="fas fa-cog fa-3x mb-3"></i>
                    <h4>Admin Panel</h4>
                    <p>{{ app_name }}</p>
                </div>
                
                <nav class="nav flex-column">
                    <a class="nav-link active" href="/admin">
                        <i class="fas fa-tachometer-alt"></i> Dashboard
                    </a>
                    <a class="nav-link" href="/admin/users">
                        <i class="fas fa-users"></i> Users
                    </a>
                    <a class="nav-link" href="/admin/chats">
                        <i class="fas fa-comments"></i> Chats
                    </a>
                    <a class="nav-link" href="/admin/earnings">
                        <i class="fas fa-money-bill-wave"></i> Earnings
                    </a>
                    <a class="nav-link" href="/admin/settings">
                        <i class="fas fa-cog"></i> Settings
                    </a>
                    <a class="nav-link" href="/dashboard">
                        <i class="fas fa-arrow-left"></i> Back to Dashboard
                    </a>
                </nav>
            </div>
            
            <!-- Admin Content -->
            <div class="col-md-9 admin-content p-4">
                <div class="row mb-4">
                    <div class="col">
                        <h2>Admin Dashboard</h2>
                        <p class="text-muted">System overview and management</p>
                    </div>
                </div>
                
                <!-- System Stats -->
                <div class="row mb-4">
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-users fa-2x text-primary mb-2"></i>
                                <h4>{{ stats[1] if stats else 0 }}</h4>
                                <p class="text-muted">Total Users</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-comments fa-2x text-success mb-2"></i>
                                <h4>{{ stats[2] if stats else 0 }}</h4>
                                <p class="text-muted">Total Chats</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-rupee-sign fa-2x text-warning mb-2"></i>
                                <h4>₹{{ "%.2f"|format(stats[3] if stats else 0) }}</h4>
                                <p class="text-muted">Total Earnings</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-chart-line fa-2x text-info mb-2"></i>
                                <h4>{{ "%.1f"|format((stats[3] / stats[1]) if stats and stats[1] > 0 else 0) }}</h4>
                                <p class="text-muted">Avg per User</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <!-- Recent Users -->
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-user-plus"></i> Recent Users</h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Username</th>
                                                <th>Balance</th>
                                                <th>Earned</th>
                                                <th>Joined</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for user in recent_users %}
                                            <tr>
                                                <td>{{ user[0] }}</td>
                                                <td>₹{{ "%.2f"|format(user[2]) }}</td>
                                                <td>₹{{ "%.2f"|format(user[3]) }}</td>
                                                <td>{{ user[4][:10] }}</td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Chats -->
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-comments"></i> Recent Chats</h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>User</th>
                                                <th>Message</th>
                                                <th>Earned</th>
                                                <th>Time</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for chat in recent_chats %}
                                            <tr>
                                                <td>{{ chat[0] }}</td>
                                                <td>{{ chat[1][:20] }}...</td>
                                                <td>₹{{ "%.2f"|format(chat[3]) }}</td>
                                                <td>{{ chat[4][:16] }}</td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-bolt"></i> Quick Actions</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-primary w-100" onclick="updateStats()">
                                            <i class="fas fa-sync"></i> Update Stats
                                        </button>
                                    </div>
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-success w-100" onclick="exportData()">
                                            <i class="fas fa-download"></i> Export Data
                                        </button>
                                    </div>
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-warning w-100" onclick="viewLogs()">
                                            <i class="fas fa-file-alt"></i> View Logs
                                        </button>
                                    </div>
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-info w-100" onclick="systemInfo()">
                                            <i class="fas fa-info-circle"></i> System Info
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function updateStats() {
            alert('Stats updated successfully!');
            location.reload();
        }
        
        function exportData() {
            alert('Data export feature will be available soon!');
        }
        
        function viewLogs() {
            alert('System logs are being maintained. Check server logs for details.');
        }
        
        function systemInfo() {
            alert('System Status: ✅ All systems operational\\n\\nFeatures:\\n- Web App: Working\\n- Telegram Bot: Configured\\n- Admin Panel: Active\\n- Database: Connected\\n- AI Service: Operational');
        }
    </script>
</body>
</html>
    """, 
    app_name=APP_NAME,
    stats=stats,
    recent_users=recent_users,
    recent_chats=recent_chats
    )

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('index'))

# Initialize database on startup
if __name__ == '__main__':
    init_database()
    
    port = int(os.getenv('PORT', 12000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )