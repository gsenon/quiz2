from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, JSON
import os  # Добавлен недостающий импорт

db = SQLAlchemy()
Base = declarative_base()

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200))
    role = Column(String(50), default='admin')

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    options = Column(Text)
    correct_answer = Column(Text)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100))
    level = Column(String(10), default='L1')
    weight = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TestSession(Base):
    __tablename__ = 'test_sessions'
    id = Column(Integer, primary_key=True)
    user_identifier = Column(String(200), nullable=False)
    user_display_name = Column(String(200), nullable=False)
    questions_data = Column(Text)
    answers_data = Column(Text)
    score = Column(Integer)
    percent = Column(Integer)
    level = Column(String(10))
    completed_at = Column(DateTime, default=datetime.utcnow)

# Engine для Base.metadata.create_all
engine = create_engine(os.environ.get("DATABASE_URL") or "sqlite:///quiz_dev.db")