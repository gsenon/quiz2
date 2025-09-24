# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

# Создаем экземпляр SQLAlchemy
db = SQLAlchemy()

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': json.loads(self.value) if self.value else {},
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    options = db.Column(db.Text)
    correct_answer = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False, index=True)
    subcategory = db.Column(db.String(100), index=True)
    level = db.Column(db.String(10), default='L1')
    weight = db.Column(db.Integer, default=1)
    explanation = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_options(self):
        return json.loads(self.options) if self.options else []
    
    def get_correct_answer(self):
        return json.loads(self.correct_answer) if self.correct_answer else []
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question_text,
            'type': self.question_type,
            'options': self.get_options(),
            'correct': self.get_correct_answer(),
            'category': self.category,
            'subcategory': self.subcategory,
            'level': self.level,
            'weight': self.weight,
            'explanation': self.explanation,
            'is_active': self.is_active
        }

class TestSession(db.Model):
    __tablename__ = 'test_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_identifier = db.Column(db.String(200), nullable=False, index=True)
    user_display_name = db.Column(db.String(200), nullable=False)
    user_email = db.Column(db.String(200))
    questions_data = db.Column(db.Text)
    answers_data = db.Column(db.Text)
    score = db.Column(db.Float)
    percent = db.Column(db.Float)
    level = db.Column(db.String(10))
    time_spent = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_identifier': self.user_identifier,
            'user_display_name': self.user_display_name,
            'score': self.score,
            'percent': self.percent,
            'level': self.level,
            'time_spent': self.time_spent,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

def init_db(app):
    """Инициализация базы данных"""
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        
        # Добавляем настройки по умолчанию
        from config import Config
        default_settings = Config.DEFAULT_SETTINGS
        
        for key, value in default_settings.items():
            if not Setting.query.filter_by(key=key).first():
                setting = Setting(
                    key=key,
                    value=json.dumps(value, ensure_ascii=False),
                    description=f"Настройки {key}"
                )
                db.session.add(setting)
        
        # Добавляем тестовые вопросы если база пустая
        if Question.query.count() == 0:
            from question_generator import QuestionGenerator
            generator = QuestionGenerator()
            questions_data = generator.generate_pool(200)
            
            for q_data in questions_data:
                question = Question(
                    question_text=q_data['question'],
                    question_type=q_data['type'],
                    options=json.dumps(q_data.get('options', []), ensure_ascii=False),
                    correct_answer=json.dumps(q_data.get('correct', []), ensure_ascii=False),
                    category=q_data['category'],
                    subcategory=q_data['subcategory'],
                    level=q_data['level'],
                    weight=q_data.get('weight', 1),
                    is_active=True
                )
                db.session.add(question)
        
        db.session.commit()
        print("✅ База данных инициализирована успешно!")

# Экспортируем db для импорта в других модулях
__all__ = ['db', 'Setting', 'Question', 'TestSession', 'init_db']