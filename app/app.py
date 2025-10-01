import os
import json
import random
import logging
import sqlalchemy as sa
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .config import Config
from .models import db, Setting, Question, TestSession, Admin, User
from .auth import AuthSystem
from .generators import QuestionGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get("APP_SECRET") or Config.APP_SECRET_DEFAULT

# Database URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    pg_user = os.environ.get("DB_USER")
    pg_pass = os.environ.get("DB_PASSWORD")
    pg_host = os.environ.get("DB_HOST")
    pg_port = os.environ.get("DB_PORT")
    pg_name = os.environ.get("DB_NAME")
    if pg_user and pg_pass and pg_host and pg_port and pg_name:
        DATABASE_URL = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_name}"
    else:
        DATABASE_URL = "sqlite:///quiz_dev.db"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

auth_system = AuthSystem(app)
question_generator = QuestionGenerator()

# Регистрация шрифта DejaVuSans
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    logger.info("Шрифт DejaVuSans успешно зарегистрирован")
except Exception as e:
    logger.warning(f"Шрифт DejaVuSans не найден: {e}, будет использован стандартный шрифт")

def get_daily_password():
    """Генерация ежедневного пароля для админа"""
    today = datetime.now().strftime("%d%m%Y")
    return today

def is_admin_authenticated():
    """Проверка аутентификации админа"""
    return session.get('admin_logged_in') and session.get('admin_username')

def has_admin_permission(permission):
    """Проверка прав доступа админа"""
    if not is_admin_authenticated():
        return False
    
    username = session.get('admin_username')
    admin = Admin.query.filter_by(username=username).first()
    
    if not admin:
        return False
    
    # Суперпользователь имеет все права
    if Config.is_super_user(username):
        return True
    
    # Проверка конкретных прав
    user = User.query.filter_by(username=username).first()
    if user:
        if permission == 'full_access' and user.full_access:
            return True
        if permission == 'manage_questions' and user.manage_questions:
            return True
        if permission == 'manage_settings' and user.manage_settings:
            return True
        if permission == 'manage_users' and user.manage_users:
            return True
    
    return False

def get_smtp_settings():
    """Получение настроек SMTP из базы"""
    settings = {}
    for setting in Setting.query.all():
        settings[setting.key] = setting.value
    return settings

def generate_pdf_report(test_session, questions_data, answers_data):
    """Генерация PDF отчета с результатами теста"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Установка шрифта
    try:
        p.setFont("DejaVuSans", 12)
    except:
        p.setFont("Helvetica", 12)
    
    # Заголовок
    p.drawString(100, 800, "Результат тестирования")
    p.drawString(100, 780, f"Сотрудник: {test_session.user_display_name}")
    p.drawString(100, 760, f"Дата прохождения: {test_session.completed_at.strftime('%d.%m.%Y %H:%M')}")
    p.drawString(100, 740, f"Результат: {test_session.percent:.1f}% ({test_session.score} баллов)")
    
    # Вопросы и ответы
    y_position = 700
    for i, (question, user_answer, correct_answer) in enumerate(zip(questions_data, answers_data, questions_data)):
        if y_position < 100:
            p.showPage()
            try:
                p.setFont("DejaVuSans", 10)
            except:
                p.setFont("Helvetica", 10)
            y_position = 750
        
        p.drawString(100, y_position, f"Вопрос {i+1}: {question['question']}")
        y_position -= 20
        
        user_answer_text = user_answer['user_answer'] if isinstance(user_answer, dict) else user_answer
        correct_answer_text = correct_answer['correct'] if isinstance(correct_answer, dict) else correct_answer
        
        p.drawString(120, y_position, f"Ваш ответ: {user_answer_text}")
        y_position -= 20
        
        p.drawString(120, y_position, f"Правильный ответ: {correct_answer_text}")
        y_position -= 30
    
    p.save()
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/healthz')
def healthz():
    try:
        db.session.execute(sa.text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    return jsonify({'status': 'ok', 'database': db_status, 'timestamp': datetime.utcnow().isoformat()})

@app.route('/start_test', methods=['POST'])
def start_test():
    full_name = request.form.get('full_name')
    if not full_name:
        flash('Введите ФИО')
        return redirect(url_for('index'))
    
    # Проверка доменной авторизации если включена
    domain_auth_enabled = Setting.query.filter_by(key='domain_auth_enabled').first()
    if domain_auth_enabled and domain_auth_enabled.value == 'true':
        # Здесь должна быть логика доменной авторизации
        pass
    
    # Получаем 50 разнообразных вопросов
    try:
        test_questions = question_generator.get_test_questions(50)
        session['test_questions'] = test_questions
        session['user_name'] = full_name
        session['current_question'] = 0
        session['answers'] = []
        session['start_time'] = datetime.utcnow().isoformat()
        
        return redirect(url_for('test_page'))
    except Exception as e:
        logger.error(f"Ошибка при генерации вопросов: {e}")
        flash('Ошибка при подготовке теста. Попробуйте позже.')
        return redirect(url_for('index'))

@app.route('/test')
def test_page():
    if 'test_questions' not in session:
        return redirect(url_for('index'))
    
    current_idx = session['current_question']
    questions = session['test_questions']
    
    if current_idx >= len(questions):
        return redirect(url_for('test_results'))
    
    current_question = questions[current_idx]
    return render_template('test.html', 
                         question=current_question, 
                         question_num=current_idx + 1, 
                         total_questions=len(questions))

@app.route('/test/answer', methods=['POST'])
def process_answer():
    if 'test_questions' not in session:
        return redirect(url_for('index'))
    
    current_idx = session['current_question']
    questions = session['test_questions']
    current_question = questions[current_idx]
    
    user_answer = request.form.getlist('answer')  # Для multiple choice
    if not user_answer:
        user_answer = [request.form.get('answer')]  # Для single choice
    
    # Обработка случая когда ответ не выбран
    if not user_answer or user_answer == [None]:
        flash('Пожалуйста, выберите ответ')
        return redirect(url_for('test_page'))
    
    session['answers'].append({
        'question_id': current_idx,
        'user_answer': user_answer,
        'correct_answer': current_question['correct'],
        'is_correct': set(user_answer) == set(current_question['correct'])
    })
    
    session['current_question'] += 1
    
    if session['current_question'] >= len(questions):
        return redirect(url_for('test_results'))
    else:
        return redirect(url_for('test_page'))

@app.route('/test/results')
def test_results():
    if 'test_questions' not in session or 'answers' not in session:
        return redirect(url_for('index'))
    
    questions = session['test_questions']
    answers = session['answers']
    
    # Расчет результатов
    total_score = sum(1 for answer in answers if answer['is_correct'])
    total_possible = len(questions)
    percent_score = (total_score / total_possible) * 100 if total_possible > 0 else 0
    
    # Сохранение результатов в базу
    test_session = TestSession(
        user_identifier=session.get('user_name', 'unknown'),
        user_display_name=session.get('user_name', 'Unknown User'),
        questions_data=json.dumps(questions),
        answers_data=json.dumps(answers),
        score=total_score,
        percent=percent_score,
        level='L2' if percent_score >= 70 else 'L1',
        completed_at=datetime.utcnow()
    )
    
    try:
        db.session.add(test_session)
        db.session.commit()
    except Exception as e:
        logger.error(f"Ошибка при сохранении результатов: {e}")
        db.session.rollback()
    
    # Отправка email с результатом если настроено
    smtp_settings = get_smtp_settings()
    if smtp_settings.get('smtp_enabled') == 'true':
        send_test_results_email(test_session, questions, answers, smtp_settings)
    
    # Очистка сессии
    session.pop('test_questions', None)
    session.pop('answers', None)
    session.pop('current_question', None)
    session.pop('user_name', None)
    
    return render_template('results.html', 
                         score=total_score, 
                         total=total_possible, 
                         percent=percent_score,
                         answers=answers,
                         questions=questions,
                         test_session=test_session)

@app.route('/test/results/pdf/<int:session_id>')
def download_pdf(session_id):
    test_session = TestSession.query.get_or_404(session_id)
    questions_data = json.loads(test_session.questions_data)
    answers_data = json.loads(test_session.answers_data)
    
    pdf_buffer = generate_pdf_report(test_session, questions_data, answers_data)
    
    filename = f"test_result_{test_session.user_display_name}_{test_session.completed_at.strftime('%Y%m%d_%H%M')}.pdf"
    
    return send_file(pdf_buffer, 
                    as_attachment=True, 
                    download_name=filename, 
                    mimetype='application/pdf')

def send_test_results_email(test_session, questions, answers, smtp_settings):
    """Отправка результатов теста по email"""
    # Заглушка для реализации отправки email
    logger.info(f"Результаты теста готовы к отправке для {test_session.user_display_name}")
    logger.info(f"SMTP настройки: {smtp_settings.get('smtp_host')}")

# Админ-панель
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверка ежедневного пароля
        daily_password = get_daily_password()
        if username == 'admin' and password == daily_password:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Успешный вход в админ-панель')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверный логин или пароль')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))
    
    return render_template('admin_dashboard.html')

@app.route('/admin/questions')
def admin_questions():
    if not is_admin_authenticated() or not has_admin_permission('manage_questions'):
        flash('Недостаточно прав')
        return redirect(url_for('admin_dashboard'))
    
    questions = Question.query.all()
    return render_template('admin_questions.html', questions=questions)

@app.route('/admin/questions/add', methods=['POST'])
def add_question():
    if not is_admin_authenticated() or not has_admin_permission('manage_questions'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    try:
        question_data = request.json
        question = Question(
            question_text=question_data['question_text'],
            question_type=question_data['question_type'],
            options=json.dumps(question_data['options']),
            correct_answer=json.dumps(question_data['correct_answer']),
            category=question_data.get('category', 'general'),
            level=question_data.get('level', 'L1'),
            weight=question_data.get('weight', 1)
        )
        
        db.session.add(question)
        db.session.commit()
        
        return jsonify({'message': 'Вопрос добавлен'})
    except Exception as e:
        logger.error(f"Ошибка при добавлении вопроса: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/questions/generate', methods=['POST'])
def generate_questions():
    if not is_admin_authenticated() or not has_admin_permission('manage_questions'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    try:
        count = int(request.json.get('count', 100))
        questions = question_generator.generate_question_pool(count)
        
        # Сохраняем вопросы в базу
        for q_data in questions:
            question = Question(
                question_text=q_data['question'],
                question_type=q_data['type'],
                options=json.dumps(q_data['options']),
                correct_answer=json.dumps(q_data['correct']),
                category='generated',
                level=q_data.get('level', 'L1'),
                weight=q_data.get('weight', 1)
            )
            db.session.add(question)
        
        db.session.commit()
        
        return jsonify({'message': f'Сгенерировано {len(questions)} вопросов'})
    except Exception as e:
        logger.error(f"Ошибка при генерации вопросов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not is_admin_authenticated() or not has_admin_permission('manage_settings'):
        flash('Недостаточно прав')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        try:
            for key, value in request.form.items():
                if key.startswith('setting_'):
                    setting_key = key.replace('setting_', '')
                    setting = Setting.query.filter_by(key=setting_key).first()
                    if setting:
                        setting.value = value
                        setting.updated_at = datetime.utcnow()
                    else:
                        setting = Setting(key=setting_key, value=value)
                        db.session.add(setting)
            
            db.session.commit()
            flash('Настройки сохранены')
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")
            flash('Ошибка при сохранении настроек')
    
    settings = {s.key: s.value for s in Setting.query.all()}
    return render_template('admin_settings.html', settings=settings)

@app.route('/admin/users')
def admin_users():
    if not is_admin_authenticated() or not has_admin_permission('manage_users'):
        flash('Недостаточно прав')
        return redirect(url_for('admin_dashboard'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    if not is_admin_authenticated() or not has_admin_permission('manage_users'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    try:
        user_data = request.json
        hashed_password = generate_password_hash(user_data['password'])
        
        user = User(
            username=user_data['username'],
            password_hash=hashed_password,
            full_access=user_data.get('full_access', False),
            manage_questions=user_data.get('manage_questions', False),
            manage_settings=user_data.get('manage_settings', False),
            manage_users=user_data.get('manage_users', False)
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'message': 'Пользователь добавлен'})
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/stats')
def admin_stats():
    if not is_admin_authenticated():
        flash('Недостаточно прав')
        return redirect(url_for('admin_dashboard'))
    
    total_questions = Question.query.count()
    total_sessions = TestSession.query.count()
    avg_score = db.session.query(db.func.avg(TestSession.percent)).scalar() or 0
    
    recent_sessions = TestSession.query.order_by(TestSession.completed_at.desc()).limit(10).all()
    
    return render_template('admin_stats.html',
                         total_questions=total_questions,
                         total_sessions=total_sessions,
                         avg_score=avg_score,
                         recent_sessions=recent_sessions)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

def init_db():
    """Инициализация базы данных"""
    try:
        db.create_all()
        
        # Создаем администратора по умолчанию если нет пользователей
        if not Admin.query.first():
            admin = Admin(username='admin')
            db.session.add(admin)
            db.session.commit()
            logger.info("Создан администратор по умолчанию")
        
        # Создаем базовые настройки если их нет
        if not Setting.query.first():
            default_settings = [
                ('domain_auth_enabled', 'false'),
                ('smtp_enabled', 'false'),
                ('smtp_host', ''),
                ('smtp_port', '587'),
                ('smtp_username', ''),
                ('smtp_password', ''),
                ('notification_email', '')
            ]
            
            for key, value in default_settings:
                setting = Setting(key=key, value=value)
                db.session.add(setting)
            
            db.session.commit()
            logger.info("Созданы настройки по умолчанию")
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return False

if __name__ == "__main__":
    with app.app_context():
        if init_db():
            logger.info("База данных успешно инициализирована")
        else:
            logger.error("Ошибка при инициализации базы данных")
    
    app.run(host="0.0.0.0", port=8080, debug=True)