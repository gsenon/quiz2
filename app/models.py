from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    options = db.Column(db.Text)
    correct_answer = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(10), default='L1')
    weight = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_options(self):
        return json.loads(self.options) if self.options else []
    
    def get_correct_answer(self):
        return json.loads(self.correct_answer) if self.correct_answer else []

class TestSession(db.Model):
    __tablename__ = 'test_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_identifier = db.Column(db.String(200), nullable=False)
    user_display_name = db.Column(db.String(200), nullable=False)
    questions_data = db.Column(db.Text)
    answers_data = db.Column(db.Text)
    score = db.Column(db.Float)
    percent = db.Column(db.Float)
    level = db.Column(db.String(10))
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_access = db.Column(db.Boolean, default=False)
    manage_questions = db.Column(db.Boolean, default=False)
    manage_settings = db.Column(db.Boolean, default=False)
    manage_users = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)