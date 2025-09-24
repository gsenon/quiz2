# models.py - SQLAlchemy models
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

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
    subcategory = db.Column(db.String(100))
    level = db.Column(db.String(10), default='L1')
    weight = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
