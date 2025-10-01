import os
import json
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get("APP_SECRET", "dev-secret-key-change-in-production")

# Импорт и инициализация базы данных
try:
    from database import db_instance
    db = db_instance
except ImportError:
    logger.error("Не удалось импортировать database.py")
    # Создаем заглушку
    class DBStub:
        def execute_query(self, *args, **kwargs):
            return []
        def init_database(self):
            return True
    db = DBStub()

class QuestionGenerator:
    """Заглушка генератора вопросов"""
    def get_test_questions(self, count=50):
        """Генерация тестовых вопросов"""
        questions = []
        for i in range(count):
            questions.append({
                'id': i + 1,
                'question': f'Тестовый вопрос №{i + 1}?',
                'type': 'single_choice',
                'options': ['Вариант A', 'Вариант B', 'Вариант C', 'Вариант D'],
                'correct': ['Вариант A'],
                'level': 'L1'
            })
        return questions
    
    def generate_question_pool(self, count=100):
        """Генерация пула вопросов"""
        return self.get_test_questions(count)

question_generator = QuestionGenerator()

def get_daily_password():
    """Генерация ежедневного пароля для админа"""
    return datetime.now().strftime("%d%m%Y")

def is_admin_authenticated():
    """Проверка аутентификации админа"""
    return session.get('admin_logged_in')

def get_smtp_settings():
    """Получение настроек SMTP"""
    try:
        settings = db.execute_query("SELECT key, value FROM settings")
        return {s['key']: s['value'] for s in settings}
    except:
        return {}

@app.route('/')
def index():
    """Главная страница"""
    return render_template("index.html")

@app.route('/start_test', methods=['GET', 'POST'])
def start_test():
    """Начало тестирования"""
    if request.method == 'GET':
        return render_template('start_test.html')
    
    full_name = request.form.get('full_name', '').strip()
    if not full_name:
        flash('Пожалуйста, введите ваше ФИО')
        return redirect(url_for('index'))
    
    try:
        # Получаем вопросы для теста
        test_questions = question_generator.get_test_questions(50)
        
        # Инициализируем сессию теста
        session['test_questions'] = test_questions
        session['user_name'] = full_name
        session['current_question'] = 0
        session['answers'] = []
        session['start_time'] = datetime.now().isoformat()
        
        logger.info(f"Тест начат для пользователя: {full_name}")
        return redirect(url_for('test_page'))
        
    except Exception as e:
        logger.error(f"Ошибка начала теста: {e}")
        flash('Ошибка при запуске теста. Попробуйте позже.')
        return redirect(url_for('index'))

@app.route('/test')
def test_page():
    """Страница тестирования"""
    if 'test_questions' not in session:
        flash('Пожалуйста, начните тест сначала')
        return redirect(url_for('index'))
    
    current_idx = session.get('current_question', 0)
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
    """Обработка ответа на вопрос"""
    if 'test_questions' not in session:
        flash('Сессия теста устарела. Пожалуйста, начните заново.')
        return redirect(url_for('index'))
    
    current_idx = session.get('current_question', 0)
    questions = session['test_questions']
    
    if current_idx >= len(questions):
        return redirect(url_for('test_results'))
    
    # Получаем ответ пользователя
    user_answer = request.form.getlist('answer')
    if not user_answer:
        user_answer = [request.form.get('answer')]
    
    # Фильтруем пустые ответы
    user_answer = [a for a in user_answer if a]
    
    if not user_answer:
        flash('Пожалуйста, выберите ответ')
        return redirect(url_for('test_page'))
    
    # Сохраняем ответ
    current_question = questions[current_idx]
    session['answers'].append({
        'question_id': current_idx,
        'user_answer': user_answer,
        'correct_answer': current_question.get('correct', []),
        'is_correct': set(user_answer) == set(current_question.get('correct', []))
    })
    
    # Переходим к следующему вопросу
    session['current_question'] = current_idx + 1
    
    if session['current_question'] >= len(questions):
        return redirect(url_for('test_results'))
    else:
        return redirect(url_for('test_page'))

@app.route('/test/results')
def test_results():
    """Страница результатов"""
    if 'test_questions' not in session or 'answers' not in session:
        flash('Результаты недоступны. Пожалуйста, пройдите тест.')
        return redirect(url_for('index'))
    
    questions = session['test_questions']
    answers = session['answers']
    
    # Расчет результатов
    total_score = sum(1 for answer in answers if answer.get('is_correct', False))
    total_questions = len(questions)
    percent_score = (total_score / total_questions) * 100 if total_questions > 0 else 0
    level = 'L2' if percent_score >= 70 else 'L1'
    
    # Сохранение результатов в базу
    try:
        db.execute_query('''
            INSERT INTO test_sessions 
            (user_identifier, user_display_name, questions_data, answers_data, score, percent, level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.get('user_name', 'unknown'),
            session.get('user_name', 'Unknown User'),
            json.dumps(questions),
            json.dumps(answers),
            total_score,
            round(percent_score, 2),
            level
        ))
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов: {e}")
    
    # Подготовка данных для шаблона
    results_data = []
    for i, (question, answer) in enumerate(zip(questions, answers)):
        results_data.append({
            'number': i + 1,
            'question': question.get('question', ''),
            'user_answer': answer.get('user_answer', []),
            'correct_answer': answer.get('correct_answer', []),
            'is_correct': answer.get('is_correct', False)
        })
    
    # Очистка сессии
    session.pop('test_questions', None)
    session.pop('answers', None)
    session.pop('current_question', None)
    session.pop('user_name', None)
    
    return render_template('results.html', 
                         score=total_score, 
                         total=total_questions, 
                         percent=round(percent_score, 2),
                         level=level,
                         results=results_data)

# Админ-панель
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Вход в админ-панель"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
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
    """Главная страница админ-панели"""
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))
    
    try:
        # Получаем статистику
        total_questions = len(db.execute_query("SELECT id FROM questions") or [])
        total_sessions = len(db.execute_query("SELECT id FROM test_sessions") or [])
        avg_result = db.execute_query("SELECT AVG(percent) as avg FROM test_sessions")
        avg_score = avg_result[0]['avg'] if avg_result else 0
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        total_questions = total_sessions = avg_score = 0
    
    return render_template('admin_dashboard.html',
                         total_questions=total_questions,
                         total_sessions=total_sessions,
                         avg_score=round(avg_score or 0, 1))

@app.route('/admin/questions')
def admin_questions():
    """Управление вопросами"""
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))
    
    try:
        questions = db.execute_query("SELECT * FROM questions ORDER BY id")
    except:
        questions = []
    
    return render_template('admin_questions.html', questions=questions)

@app.route('/admin/questions/generate', methods=['POST'])
def generate_questions():
    """Генерация вопросов"""
    if not is_admin_authenticated():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    try:
        count = int(request.json.get('count', 100))
        questions = question_generator.generate_question_pool(count)
        
        added_count = 0
        for q in questions:
            try:
                db.execute_query('''
                    INSERT INTO questions 
                    (question_text, question_type, options, correct_answer, category, level)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    q.get('question', ''),
                    q.get('type', 'single_choice'),
                    json.dumps(q.get('options', [])),
                    json.dumps(q.get('correct', [])),
                    'generated',
                    q.get('level', 'L1')
                ))
                added_count += 1
            except Exception as e:
                logger.error(f"Ошибка сохранения вопроса: {e}")
        
        return jsonify({'message': f'Сгенерировано {added_count} вопросов'})
    except Exception as e:
        logger.error(f"Ошибка генерации вопросов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/stats')
def admin_stats():
    """Статистика"""
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))
    
    try:
        total_questions = len(db.execute_query("SELECT id FROM questions") or [])
        total_sessions = len(db.execute_query("SELECT id FROM test_sessions") or [])
        avg_result = db.execute_query("SELECT AVG(percent) as avg FROM test_sessions")
        avg_score = avg_result[0]['avg'] if avg_result else 0
        recent_sessions = db.execute_query("SELECT * FROM test_sessions ORDER BY completed_at DESC LIMIT 10") or []
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")
        total_questions = total_sessions = avg_score = 0
        recent_sessions = []
    
    return render_template('admin_stats.html',
                         total_questions=total_questions,
                         total_sessions=total_sessions,
                         avg_score=round(avg_score or 0, 1),
                         recent_sessions=recent_sessions)

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

@app.route('/admin/logout')
def admin_logout():
    """Выход из админ-панели"""
    session.clear()
    flash('Вы вышли из админ-панели')
    return redirect(url_for('admin_login'))

def init_app():
    """Инициализация приложения"""
    with app.app_context():
        if db.init_database():
            logger.info("Приложение успешно инициализировано")
        else:
            logger.error("Ошибка инициализации приложения")

if __name__ == "__main__":
    init_app()
    app.run(host="0.0.0.0", port=8080, debug=True)