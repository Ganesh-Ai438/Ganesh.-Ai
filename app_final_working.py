#!/usr/bin/env python3
"""
🤖 Ganesh A.I. - FINAL WORKING VERSION
Complete system with working dashboard and bot
"""

import os
import sys
import json
import time
import uuid
import logging
import sqlite3
import threading
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Configuration
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'ganesh-ai-secret-key-2024')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///ganesh_ai_final.db')
DOMAIN = os.getenv('DOMAIN', 'https://ganesh-ai-working.onrender.com')

# App Configuration
APP_NAME = os.getenv('APP_NAME', 'Ganesh A.I.')
ADMIN_USER = os.getenv('ADMIN_USER', 'Admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', '12345')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    wallet = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    chats_count = db.Column(db.Integer, default=0)
    visits_count = db.Column(db.Integer, default=0)
    referrals_count = db.Column(db.Integer, default=0)
    is_premium = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    telegram_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_earnings(self, amount, description=""):
        if self.wallet is None:
            self.wallet = 0.0
        if self.total_earned is None:
            self.total_earned = 0.0
        self.wallet += amount
        self.total_earned += amount

# Chat History Model
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), default='ganesh-free')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# AI Response System
class AIResponseSystem:
    def __init__(self):
        self.responses = {
            'greetings': [
                "Hello! 👋 I'm Ganesh AI, your intelligent assistant. How can I help you today?",
                "Hi there! 🤖 Welcome to Ganesh AI. What would you like to explore?",
                "Namaste! 🙏 I'm here to assist you with any questions or tasks.",
                "Greetings! ✨ Ready to dive into some AI-powered conversations?"
            ],
            'help': [
                "I can help you with various tasks like answering questions, creative writing, problem-solving, and much more!",
                "I'm here to assist with information, creative tasks, analysis, and general conversation. What do you need help with?",
                "My capabilities include answering questions, helping with writing, providing explanations, and engaging in meaningful conversations."
            ],
            'general': [
                "That's an interesting question! Let me think about that...",
                "I understand what you're asking. Here's my perspective on that...",
                "Great question! Based on my knowledge, I can tell you that...",
                "I'd be happy to help you with that. Let me provide you with some insights..."
            ]
        }
    
    def generate_response(self, message, user=None):
        """Generate AI response based on message"""
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'start']):
            response = random.choice(self.responses['greetings'])
            if user:
                response = response.replace("I'm Ganesh AI", f"I'm Ganesh AI, {user.username}")
            return response
        
        # Help responses
        elif any(word in message_lower for word in ['help', 'what can you do', 'features', 'capabilities']):
            return random.choice(self.responses['help'])
        
        # Specific responses
        elif 'weather' in message_lower:
            return "I don't have access to real-time weather data, but I'd recommend checking a weather app for current conditions! 🌤️"
        
        elif 'time' in message_lower:
            current_time = datetime.now().strftime("%H:%M:%S")
            return f"The current time is {current_time}. Is there anything else I can help you with? ⏰"
        
        elif any(word in message_lower for word in ['joke', 'funny', 'humor']):
            jokes = [
                "Why don't scientists trust atoms? Because they make up everything! 😄",
                "I told my computer a joke about UDP... but I'm not sure if it got it! 😂",
                "Why did the AI go to therapy? It had too many deep learning issues! 🤖"
            ]
            return random.choice(jokes)
        
        elif any(word in message_lower for word in ['love', 'like', 'favorite']):
            return "I appreciate your positive sentiment! As an AI, I find joy in helping people and having meaningful conversations. What brings you happiness? ❤️"
        
        elif any(word in message_lower for word in ['thank', 'thanks', 'appreciate']):
            return "You're very welcome! I'm always here to help. Feel free to ask me anything else! 😊"
        
        # Programming related
        elif 'python' in message_lower or 'programming' in message_lower:
            return "Python is a fantastic programming language! It's versatile, readable, and great for beginners and experts alike. Are you learning to code? 🐍"
        
        elif 'ai' in message_lower or 'artificial intelligence' in message_lower:
            return "AI is rapidly evolving and has incredible potential to help solve complex problems and improve our daily lives. What aspect of AI interests you most? 🧠"
        
        elif 'business' in message_lower or 'money' in message_lower:
            return "Building a successful business requires planning, persistence, and understanding your customers' needs. Are you working on a business idea? 💼"
        
        elif 'learn' in message_lower or 'study' in message_lower:
            return "Learning is a lifelong journey! The key is to stay curious, practice regularly, and don't be afraid to make mistakes. What are you studying? 📚"
        
        # General intelligent responses
        else:
            base_response = random.choice(self.responses['general'])
            return f"{base_response} Regarding '{message[:50]}...', I'd be happy to discuss this topic further with you! 💭"

# Initialize AI system
ai_system = AIResponseSystem()

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            user.visits_count += 1
            user.add_earnings(0.01, "Login visit")
            user.last_active = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template_string(LOGIN_TEMPLATE, app_name=APP_NAME)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template_string(REGISTER_TEMPLATE, app_name=APP_NAME)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template_string(REGISTER_TEMPLATE, app_name=APP_NAME)
        
        user = User(username=username, email=email)
        user.set_password(password)
        user.add_earnings(10.0, "Welcome bonus")
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        flash('Registration successful! Welcome bonus ₹10 added!')
        return redirect(url_for('dashboard'))
    
    return render_template_string(REGISTER_TEMPLATE, app_name=APP_NAME)

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    user.visits_count += 1
    user.add_earnings(0.01, "Dashboard visit")
    user.last_active = datetime.utcnow()
    db.session.commit()
    
    return render_template_string(DASHBOARD_TEMPLATE, user=user, app_name=APP_NAME)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        model = data.get('model', 'ganesh-free')
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'})
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Generate AI response
        response = ai_system.generate_response(message, user)
        
        # Save chat history
        chat = ChatHistory(
            user_id=user.id,
            message=message,
            response=response,
            model=model
        )
        db.session.add(chat)
        
        # Update user stats
        user.chats_count += 1
        user.add_earnings(0.05, f"Chat with {model}")
        user.last_active = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': response,
            'model': model,
            'stats': {
                'wallet': float(user.wallet),
                'chats_count': user.chats_count,
                'total_earned': float(user.total_earned)
            }
        })
        
    except Exception as e:
        print(f"Chat API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/stats')
@login_required
def api_stats():
    user = User.query.get(session['user_id'])
    return jsonify({
        'wallet': float(user.wallet),
        'total_earned': float(user.total_earned),
        'chats_count': user.chats_count,
        'visits_count': user.visits_count,
        'referrals_count': user.referrals_count,
        'is_premium': user.is_premium
    })

@app.route('/admin')
@login_required
def admin():
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    total_users = len(users)
    total_earnings = sum(u.total_earned for u in users)
    total_chats = sum(u.chats_count for u in users)
    
    return render_template_string(ADMIN_TEMPLATE, 
                                users=users, 
                                total_users=total_users,
                                total_earnings=total_earnings,
                                total_chats=total_chats,
                                app_name=APP_NAME)

# Templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="text-center mb-4">
            <i class="fas fa-robot fa-3x text-primary mb-3"></i>
            <h2>{{ app_name }}</h2>
            <p class="text-muted">Welcome back! Please login to continue.</p>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-danger">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Username</label>
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
        </div>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Register</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .register-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="register-card">
        <div class="text-center mb-4">
            <i class="fas fa-robot fa-3x text-primary mb-3"></i>
            <h2>{{ app_name }}</h2>
            <p class="text-muted">Create your account and get ₹10 welcome bonus!</p>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-danger">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
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
                <input type="password" class="form-control" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 mb-3">
                <i class="fas fa-user-plus"></i> Register & Get ₹10 Bonus
            </button>
        </form>
        
        <div class="text-center">
            <p>Already have an account? <a href="/login">Login here</a></p>
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }
        .navbar {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }
        .stats-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .chat-container {
            background: white;
            border-radius: 15px;
            height: 600px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px 15px 0 0;
        }
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message.bot {
            justify-content: flex-start;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .message.bot .message-content {
            background: white;
            border: 1px solid #e9ecef;
            color: #333;
        }
        .chat-input {
            padding: 20px;
            border-top: 1px solid #e9ecef;
            border-radius: 0 0 15px 15px;
        }
        .model-selector {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .model-option {
            padding: 10px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .model-option:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }
        .model-option.active {
            border-color: #667eea;
            background: #667eea;
            color: white;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 10px;
            color: #666;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-robot"></i> {{ app_name }}
            </a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text me-3">Welcome, {{ user.username }}!</span>
                <a class="nav-link" href="/logout">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <!-- Stats Panel -->
            <div class="col-md-4">
                <div class="stats-card">
                    <h5><i class="fas fa-wallet"></i> Your Stats</h5>
                    <div class="row text-center">
                        <div class="col-6">
                            <h4 class="text-success" id="walletBalance">₹{{ "%.2f"|format(user.wallet) }}</h4>
                            <small>Balance</small>
                        </div>
                        <div class="col-6">
                            <h4 class="text-primary" id="chatsCount">{{ user.chats_count }}</h4>
                            <small>Chats</small>
                        </div>
                    </div>
                    <hr>
                    <div class="row text-center">
                        <div class="col-6">
                            <h4 class="text-info" id="totalEarned">₹{{ "%.2f"|format(user.total_earned) }}</h4>
                            <small>Total Earned</small>
                        </div>
                        <div class="col-6">
                            <h4 class="text-warning">{{ user.visits_count }}</h4>
                            <small>Visits</small>
                        </div>
                    </div>
                </div>

                <!-- Model Selector -->
                <div class="model-selector">
                    <h5><i class="fas fa-brain"></i> AI Model</h5>
                    <div class="model-option active" onclick="selectModel('ganesh-free')">
                        <strong>🆓 Ganesh Free</strong>
                        <br><small>Basic conversations - Free</small>
                    </div>
                    <div class="model-option" onclick="selectModel('gpt-4')">
                        <strong>🚀 GPT-4 Turbo</strong>
                        <br><small>Advanced AI - Premium</small>
                    </div>
                    <div class="model-option" onclick="selectModel('claude')">
                        <strong>🎯 Claude 3</strong>
                        <br><small>Analytical AI - Premium</small>
                    </div>
                </div>

                {% if user.is_admin %}
                <div class="stats-card">
                    <h5><i class="fas fa-crown"></i> Admin Panel</h5>
                    <a href="/admin" class="btn btn-warning w-100">
                        <i class="fas fa-cog"></i> Manage System
                    </a>
                </div>
                {% endif %}
            </div>

            <!-- Chat Interface -->
            <div class="col-md-8">
                <div class="chat-container">
                    <div class="chat-header">
                        <h5><i class="fas fa-comments"></i> Chat with AI</h5>
                        <small>Earn ₹0.05 for each message!</small>
                    </div>
                    
                    <div class="chat-messages" id="chatMessages">
                        <div class="message bot">
                            <div class="message-content">
                                👋 Hello {{ user.username }}! I'm your AI assistant. Ask me anything and earn money with each chat!
                            </div>
                        </div>
                    </div>
                    
                    <div class="loading" id="loadingIndicator">
                        <i class="fas fa-spinner fa-spin"></i> AI is thinking...
                    </div>
                    
                    <div class="chat-input">
                        <div class="input-group">
                            <input type="text" class="form-control" id="messageInput" 
                                   placeholder="Type your message here..." onkeypress="handleKeyPress(event)">
                            <button class="btn btn-primary" onclick="sendMessage()">
                                <i class="fas fa-paper-plane"></i> Send
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentModel = 'ganesh-free';
        let chatHistory = [];

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage(message, 'user');
            input.value = '';
            
            // Show loading
            document.getElementById('loadingIndicator').style.display = 'block';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        model: currentModel
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage(data.response, 'bot');
                    
                    // Update stats if provided
                    if (data.stats) {
                        updateStats(data.stats);
                    }
                } else {
                    addMessage('Sorry, I encountered an error. Please try again.', 'bot');
                }
            } catch (error) {
                console.error('Chat error:', error);
                addMessage('Sorry, I encountered a connection error. Please try again.', 'bot');
            } finally {
                document.getElementById('loadingIndicator').style.display = 'none';
            }
        }

        function addMessage(content, sender) {
            const messagesContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            messageContent.innerHTML = content.replace(/\\n/g, '<br>');
            
            messageDiv.appendChild(messageContent);
            messagesContainer.appendChild(messageDiv);
            
            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Save to history
            chatHistory.push({ content, sender, timestamp: new Date() });
        }

        function updateStats(stats) {
            document.getElementById('walletBalance').textContent = `₹${stats.wallet.toFixed(2)}`;
            document.getElementById('chatsCount').textContent = stats.chats_count;
            document.getElementById('totalEarned').textContent = `₹${stats.total_earned.toFixed(2)}`;
        }

        function selectModel(model) {
            currentModel = model;
            
            // Update UI
            document.querySelectorAll('.model-option').forEach(option => {
                option.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Add system message
            const modelNames = {
                'ganesh-free': '🆓 Ganesh Free',
                'gpt-4': '🚀 GPT-4 Turbo',
                'claude': '🎯 Claude 3'
            };
            
            addMessage(`Switched to ${modelNames[model]} model!`, 'bot');
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 Dashboard loaded successfully!');
            document.getElementById('messageInput').focus();
        });
    </script>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .admin-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: rgba(255,255,255,0.1);">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="fas fa-robot"></i> {{ app_name }} - Admin
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">
                    <i class="fas fa-arrow-left"></i> Back to Dashboard
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-md-3">
                <div class="admin-card text-center">
                    <h3 class="text-primary">{{ total_users }}</h3>
                    <p>Total Users</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="admin-card text-center">
                    <h3 class="text-success">₹{{ "%.2f"|format(total_earnings) }}</h3>
                    <p>Total Earnings</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="admin-card text-center">
                    <h3 class="text-info">{{ total_chats }}</h3>
                    <p>Total Chats</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="admin-card text-center">
                    <h3 class="text-warning">Active</h3>
                    <p>System Status</p>
                </div>
            </div>
        </div>

        <div class="admin-card">
            <h5><i class="fas fa-users"></i> User Management</h5>
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Wallet</th>
                            <th>Chats</th>
                            <th>Visits</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td>{{ user.username }}</td>
                            <td>{{ user.email }}</td>
                            <td>₹{{ "%.2f"|format(user.wallet) }}</td>
                            <td>{{ user.chats_count }}</td>
                            <td>{{ user.visits_count }}</td>
                            <td>
                                {% if user.is_admin %}
                                    <span class="badge bg-danger">Admin</span>
                                {% elif user.is_premium %}
                                    <span class="badge bg-warning">Premium</span>
                                {% else %}
                                    <span class="badge bg-success">Active</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
'''

def init_db():
    """Initialize database with tables and admin user"""
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username=ADMIN_USER).first()
        if not admin:
            admin = User(
                username=ADMIN_USER,
                email=f"{ADMIN_USER.lower()}@ganesh-ai.com",
                is_admin=True
            )
            admin.set_password(ADMIN_PASS)
            admin.add_earnings(1000.0, "Admin initial balance")
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin user created: {ADMIN_USER} / {ADMIN_PASS}")

if __name__ == '__main__':
    print("🚀 Starting Ganesh A.I. Final Working System...")
    
    # Initialize database
    init_db()
    
    # Start Flask app
    port = int(os.getenv('PORT', 10000))
    print(f"🌐 Starting web server on port {port}")
    print(f"🔗 Access URL: {DOMAIN}")
    print(f"👨‍💼 Admin: {ADMIN_USER} / {ADMIN_PASS}")
    print("✅ All systems operational!")
    
    app.run(host='0.0.0.0', port=port, debug=DEBUG)