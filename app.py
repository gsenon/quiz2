# -*- coding: utf-8 -*-
import os
import json
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from jinja2 import Environment

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация из переменных окружения
app.secret_key = os.environ.get("APP_SECRET", "super_secret_key_change_in_production")

# Конфигурация БД
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True
}

# Инициализация БД
db = SQLAlchemy(app)

# ===== МОДЕЛИ БАЗЫ ДАННЫХ =====

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

# ===== КОНФИГУРАЦИЯ И ПОМОЩНИКИ =====

class Config:
    SUPER_USERS = ["k.skachilov"]
    
    @staticmethod
    def is_super_user(username):
        return username.lower() in [user.lower() for user in Config.SUPER_USERS]
    
    @staticmethod
    def generate_code(length=6):
        import string
        return ''.join(random.choices(string.digits, k=length))

def get_settings():
    """Получение настроек из БД"""
    try:
        settings_dict = {}
        settings = Setting.query.all()
        for setting in settings:
            settings_dict[setting.key] = json.loads(setting.value)
        return settings_dict
    except Exception as e:
        logger.error(f"Ошибка получения настроек: {e}")
        return {
            "auth": {"domain_auth_enabled": False, "domain_name": "company.ru"},
            "email": {"enabled": False}
        }

def get_questions_pool():
    """Получение активных вопросов из БД"""
    try:
        questions = Question.query.filter_by(is_active=True).all()
        return questions
    except Exception as e:
        logger.error(f"Ошибка получения вопросов: {e}")
        return []

def shuffle_filter(seq):
    """Jinja2 фильтр для перемешивания"""
    try:
        result = list(seq)
        random.shuffle(result)
        return result
    except:
        return seq

app.jinja_env.filters['shuffle'] = shuffle_filter

# ===== СИСТЕМА АУТЕНТИФИКАЦИИ =====

class AuthSystem:
    def __init__(self):
        self.pending_admin_logins = {}
    
    def initiate_admin_login(self, username):
        """Инициация входа в админку"""
        if not Config.is_super_user(username):
            return False
        
        code = Config.generate_code()
        self.pending_admin_logins[username] = {
            'code': code,
            'attempts': 0
        }
        return code
    
    def verify_admin_code(self, username, code):
        """Проверка кода админки"""
        if username not in self.pending_admin_logins:
            return False
        
        login_data = self.pending_admin_logins[username]
        login_data['attempts'] += 1
        
        if login_data['code'] == code:
            del self.pending_admin_logins[username]
            return True
        return False
    
    def authenticate_test_user(self, username, use_domain_auth=False):
        """Аутентификация пользователя для тестирования"""
        if use_domain_auth:
            if not username or '@' not in username:
                return False
            login = username.split('@')[0].lower()
            return {
                "username": login,
                "email": username,
                "display_name": login
            }
        else:
            if not username:
                return False
            return {
                "username": username,
                "email": "",
                "display_name": username
            }

auth_system = AuthSystem()

# ===== МАРШРУТЫ =====

@app.route('/')
def index():
    """Главная страница"""
    settings = get_settings()
    return render_template("index.html", 
                         domain_auth_enabled=settings["auth"]["domain_auth_enabled"])

@app.route('/health')
def health():
    """Health check для Kubernetes"""
    try:
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/start_test', methods=['POST'])
def start_test():
    """Начало тестирования"""
    username = request.form.get("username", "").strip()
    settings = get_settings()
    use_domain_auth = settings["auth"]["domain_auth_enabled"]
    
    user_info = auth_system.authenticate_test_user(username, use_domain_auth)
    if not user_info:
        flash("Ошибка аутентификации", "error")
        return redirect(url_for('index'))
    
    # Создаем сессию
    session.update({
        "user_info": user_info,
        "username": user_info["username"],
        "authenticated": True,
        "is_admin": False,
        "start_time": datetime.utcnow().isoformat()
    })
    
    # Выбор вопросов
    pool = get_questions_pool()
    count = min(50, len(pool))
    selected = random.sample(pool, count) if pool else []
    
    session.update({
        "quiz_questions": [q.id for q in selected],
        "quiz_idx": 0,
        "answers": {}
    })
    
    return redirect(url_for('quiz'))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    """Страница вопроса"""
    if not session.get("authenticated") or session.get("is_admin"):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        return handle_quiz_answer()
    
    # GET request - показать вопрос
    question_ids = session.get("quiz_questions", [])
    idx = session.get("quiz_idx", 0)
    
    if idx >= len(question_ids):
        return redirect(url_for('results'))
    
    question = Question.query.get(question_ids[idx])
    if not question:
        flash("Ошибка загрузки вопроса", "error")
        return redirect(url_for('index'))
    
    return render_template("quiz.html", 
                         q=question, 
                         idx=idx, 
                         total=len(question_ids))

def handle_quiz_answer():
    """Обработка ответа на вопрос"""
    question_ids = session.get("quiz_questions", [])
    idx = session.get("quiz_idx", 0)
    
    question = Question.query.get(question_ids[idx])
    if not question:
        flash("Вопрос не найден", "error")
        return redirect(url_for('index'))
    
    # Обработка ответа в зависимости от типа вопроса
    answer = None
    if question.question_type == "single_choice":
        answer = request.form.get("opt")
    elif question.question_type == "multiple_choice":
        answer = request.form.getlist("opt")
    elif question.question_type in ["fill_blank", "open_question"]:
        answer = request.form.get("text", "").strip()
    
    answers = session.get("answers", {})
    answers[str(question.id)] = answer
    session["answers"] = answers
    session["quiz_idx"] = idx + 1
    
    return redirect(url_for('quiz'))

@app.route('/results')
def results():
    """Страница результатов"""
    if not session.get("authenticated") or session.get("is_admin"):
        return redirect(url_for('index'))
    
    question_ids = session.get("quiz_questions", [])
    answers = session.get("answers", {})
    user_info = session.get("user_info", {})
    
    # Расчет результатов
    total_weight = 0
    score = 0
    results_data = []
    
    for qid in question_ids:
        question = Question.query.get(qid)
        if not question:
            continue
            
        user_answer = answers.get(str(qid))
        weight = question.weight
        total_weight += weight
        
        # Простая логика оценки
        is_correct = False
        if question.question_type == "single_choice":
            correct_answers = json.loads(question.correct_answer) if question.correct_answer else []
            is_correct = user_answer in correct_answers
        elif question.question_type == "multiple_choice":
            correct_answers = set(json.loads(question.correct_answer) if question.correct_answer else [])
            user_answers = set(user_answer or [])
            is_correct = user_answers == correct_answers
        
        if is_correct:
            score += weight
        
        results_data.append({
            "question": question,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "weight": weight
        })
    
    percent = round((score / total_weight * 100), 2) if total_weight > 0 else 0
    level = "L2" if percent >= 80 else "L1"
    
    # Сохранение результатов
    try:
        test_session = TestSession(
            user_identifier=user_info["username"],
            user_display_name=user_info["display_name"],
            questions_data=json.dumps(question_ids),
            answers_data=json.dumps(answers),
            score=score,
            percent=percent,
            level=level
        )
        db.session.add(test_session)
        db.session.commit()
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов: {e}")
    
    return render_template("results.html", 
                         results=results_data, 
                         percent=percent, 
                         level=level,
                         score=score,
                         total_weight=total_weight)

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash("Вы успешно вышли из системы", "success")
    return redirect(url_for('index'))

# ===== АДМИНКА =====

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Вход в админку"""
    if request.method == 'POST':
        username = request.form.get("username", "").strip().lower()
        
        if not Config.is_super_user(username):
            flash("Доступ запрещен", "error")
            return redirect(url_for('admin_login'))
        
        code = auth_system.initiate_admin_login(username)
        if code:
            # В реальной системе здесь была бы отправка email
            session["pending_admin"] = username
            session["admin_code"] = code  # Для демонстрации храним в сессии
            flash(f"Код доступа: {code} (в реальной системе отправлен на email)", "success")
            return redirect(url_for('admin_enter_code'))
        
        flash("Ошибка входа", "error")
    
    return render_template("admin/login.html")

@app.route('/admin/enter_code', methods=['GET', 'POST'])
def admin_enter_code():
    """Ввод кода админки"""
    if not session.get("pending_admin"):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        username = session.get("pending_admin")
        code = request.form.get("code", "").strip()
        
        if auth_system.verify_admin_code(username, code) or code == session.get("admin_code"):
            session.update({
                "is_admin": True,
                "authenticated": True,
                "username": username,
                "user_info": {"username": username, "display_name": username}
            })
            session.pop("pending_admin", None)
            session.pop("admin_code", None)
            return redirect(url_for('admin_dashboard'))
        
        flash("Неверный код подтверждения", "error")
    
    return render_template("admin/enter_code.html")

@app.route('/admin')
def admin_dashboard():
    """Панель администратора"""
    if not session.get("is_admin"):
        return redirect(url_for('admin_login'))
    
    stats = {
        'total_questions': Question.query.count(),
        'active_questions': Question.query.filter_by(is_active=True).count(),
        'total_sessions': TestSession.query.count(),
    }
    
    return render_template("admin/dashboard.html", stats=stats)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """Настройки системы"""
    if not session.get("is_admin"):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            settings = {
                "auth": {
                    "domain_auth_enabled": request.form.get("domain_auth_enabled") == "on",
                    "domain_name": request.form.get("domain_name", "company.ru")
                },
                "email": {
                    "enabled": request.form.get("email_enabled") == "on",
                    "smtp_server": request.form.get("smtp_server", ""),
                    "smtp_port": request.form.get("smtp_port", "587"),
                    "from_email": request.form.get("from_email", "")
                }
            }
            
            for key, value in settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = json.dumps(value, ensure_ascii=False)
                else:
                    setting = Setting(key=key, value=json.dumps(value, ensure_ascii=False))
                    db.session.add(setting)
            
            db.session.commit()
            flash("Настройки сохранены", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка сохранения: {e}", "error")
        
        return redirect(url_for('admin_settings'))
    
    settings = get_settings()
    return render_template("admin/settings.html", settings=settings)

@app.route('/admin/sessions')
def admin_sessions():
    """Просмотр сессий тестирования"""
    if not session.get("is_admin"):
        return redirect(url_for('admin_login'))
    
    sessions = TestSession.query.order_by(TestSession.completed_at.desc()).limit(50).all()
    return render_template("admin/sessions.html", sessions=sessions)

# ===== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =====

def init_db():
    """Инициализация базы данных с начальными данными"""
    with app.app_context():
        try:
            # Создаем таблицы
            db.create_all()
            
            # Добавляем начальные настройки
            default_settings = {
                "auth": {
                    "domain_auth_enabled": False,
                    "domain_name": "company.ru"
                },
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "from_email": "noreply@company.ru"
                }
            }
            
            for key, value in default_settings.items():
                if not Setting.query.filter_by(key=key).first():
                    setting = Setting(key=key, value=json.dumps(value, ensure_ascii=False))
                    db.session.add(setting)
            
            # Добавляем тестовые вопросы если база пустая
            if Question.query.count() == 0:
                from question_generator import QuestionGenerator
                generator = QuestionGenerator()
                questions_data = generator.generate_pool(100)
                
                for q_data in questions_data:
                    question = Question(
                        question_text=q_data['question'],
                        question_type=q_data['type'],
                        options=json.dumps(q_data.get('options', [])),
                        correct_answer=json.dumps(q_data.get('correct', [])),
                        category=q_data['category'],
                        subcategory=q_data['subcategory'],
                        level=q_data['level'],
                        weight=q_data.get('weight', 1),
                        is_active=True
                    )
                    db.session.add(question)
            
            db.session.commit()
            logger.info("✅ База данных инициализирована успешно!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            db.session.rollback()

# Инициализация БД при запуске
@app.before_first_request
def initialize():
    init_db()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000, debug=False)