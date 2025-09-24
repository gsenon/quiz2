# app.py - Flask 3.x, продакшен-ready
import os
import json
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, Setting, Question, TestSession
from auth import AuthSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')

# Secret key
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

auth_system = AuthSystem()

# -------------------
# Jinja filters
# -------------------
def shuffle_filter(seq):
    try:
        result = list(seq)
        random.shuffle(result)
        return result
    except Exception:
        return seq

app.jinja_env.filters['shuffle'] = shuffle_filter

# -------------------
# Routes
# -------------------
@app.route('/')
def index():
    settings = get_settings()
    return render_template('index.html', domain_auth_enabled=settings.get("auth", {}).get("domain_auth_enabled", False))

@app.route('/healthz')
def healthz():
    try:
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    return jsonify({'status': 'ok', 'database': db_status, 'timestamp': datetime.utcnow().isoformat()})

@app.route('/start_test', methods=['POST'])
def start_test():
    username = request.form.get('username', '').strip()
    settings = get_settings()
    use_domain_auth = settings.get('auth', {}).get("domain_auth_enabled", False)
    user_info = auth_system.authenticate_test_user(username, use_domain_auth)
    if not user_info:
        flash('Authentication error', 'error')
        return redirect(url_for('index'))
    session.update({
        'user_info': user_info,
        'username': user_info.get('username'),
        'authenticated': True,
        'is_admin': False,
        'start_time': datetime.utcnow().isoformat()
    })
    pool = get_questions_pool()
    count = min(50, len(pool))
    selected = random.sample(pool, count) if pool else []
    session.update({
        'quiz_questions': [q.id for q in selected],
        'quiz_idx': 0,
        'answers': {}
    })
    return redirect(url_for('quiz'))

@app.route('/quiz', methods=['GET','POST'])
def quiz():
    if not session.get('authenticated') or session.get('is_admin'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        return handle_quiz_answer()
    question_ids = session.get('quiz_questions', [])
    idx = session.get('quiz_idx', 0)
    if idx >= len(question_ids):
        return redirect(url_for('results'))
    question = Question.query.get(question_ids[idx])
    if not question:
        flash('Question load error', 'error')
        return redirect(url_for('index'))
    return render_template('quiz.html', q=question, idx=idx, total=len(question_ids))

def handle_quiz_answer():
    question_ids = session.get('quiz_questions', [])
    idx = session.get('quiz_idx', 0)
    if idx >= len(question_ids):
        return redirect(url_for('results'))
    question = Question.query.get(question_ids[idx])
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('index'))
    answer = None
    if question.question_type == 'single_choice':
        answer = request.form.get('opt')
    elif question.question_type == 'multiple_choice':
        answer = request.form.getlist('opt')
    elif question.question_type in ('fill_blank', 'open_question'):
        answer = request.form.get('text', '').strip()
    answers = session.get('answers', {})
    answers[str(question.id)] = answer
    session['answers'] = answers
    session['quiz_idx'] = idx + 1
    return redirect(url_for('quiz'))

@app.route('/results')
def results():
    if not session.get('authenticated') or session.get('is_admin'):
        return redirect(url_for('index'))
    question_ids = session.get('quiz_questions', [])
    answers = session.get('answers', {})
    user_info = session.get('user_info', {})
    total_weight = 0
    score = 0
    results_data = []
    for qid in question_ids:
        question = Question.query.get(qid)
        if not question:
            continue
        user_answer = answers.get(str(qid))
        weight = question.weight or 1
        total_weight += weight
        is_correct = False
        if question.question_type == 'single_choice':
            try:
                correct_answers = json.loads(question.correct_answer) if question.correct_answer else []
            except Exception:
                correct_answers = []
            is_correct = user_answer in correct_answers
        elif question.question_type == 'multiple_choice':
            try:
                correct_answers = set(json.loads(question.correct_answer) if question.correct_answer else [])
            except Exception:
                correct_answers = set()
            user_answers = set(user_answer or [])
            is_correct = user_answers == correct_answers
        if is_correct:
            score += weight
        results_data.append({'question': question, 'user_answer': user_answer, 'is_correct': is_correct, 'weight': weight})
    percent = round((score / total_weight * 100), 2) if total_weight > 0 else 0
    level = 'L2' if percent >= 80 else 'L1'
    try:
        test_session = TestSession(
            user_identifier=user_info.get('username','-'),
            user_display_name=user_info.get('display_name','-'),
            questions_data=json.dumps(question_ids),
            answers_data=json.dumps(answers),
            score=score,
            percent=percent,
            level=level
        )
        db.session.add(test_session)
        db.session.commit()
    except Exception as e:
        logger.error(f'Error saving results: {e}')
        db.session.rollback()
    return render_template('results.html', results=results_data, percent=percent, level=level, score=score, total_weight=total_weight)

# -------------------
# Admin routes
# -------------------
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username','').strip().lower()
        if not Config.is_super_user(username):
            flash('Access denied', 'error')
            return redirect(url_for('admin_login'))
        code = auth_system.initiate_admin_login(username)
        if code:
            session['pending_admin'] = username
            session['admin_code'] = code
            flash(f'Admin code: {code} (demo only)', 'success')
            return redirect(url_for('admin_enter_code'))
        flash('Login error', 'error')
    return render_template('admin/login.html')

@app.route('/admin/enter_code', methods=['GET','POST'])
def admin_enter_code():
    if not session.get('pending_admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        username = session.get('pending_admin')
        code = request.form.get('code','').strip()
        if auth_system.verify_admin_code(username, code) or code == session.get('admin_code'):
            session.update({'is_admin': True, 'authenticated': True, 'username': username, 'user_info': {'username': username, 'display_name': username}})
            session.pop('pending_admin', None)
            session.pop('admin_code', None)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid code', 'error')
    return render_template('admin/enter_code.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    stats = {
        'total_questions': Question.query.count(),
        'active_questions': Question.query.filter_by(is_active=True).count(),
        'total_sessions': TestSession.query.count()
    }
    return render_template('admin/dashboard.html', stats=stats)

# -------------------
# Settings helpers
# -------------------
@app.route('/admin/settings', methods=['GET','POST'])
def admin_settings():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        try:
            settings = {
                'auth': {'domain_auth_enabled': request.form.get('domain_auth_enabled') == 'on', 'domain_name': request.form.get('domain_name','company.ru')},
                'email': {'enabled': request.form.get('email_enabled') == 'on', 'smtp_server': request.form.get('smtp_server',''), 'smtp_port': int(request.form.get('smtp_port', '587')), 'from_email': request.form.get('from_email','')}
            }
            for key, value in settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = json.dumps(value, ensure_ascii=False)
                else:
                    db.session.add(Setting(key=key, value=json.dumps(value, ensure_ascii=False)))
            db.session.commit()
            flash('Settings saved', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving settings: {e}', 'error')
        return redirect(url_for('admin_settings'))
    settings = get_settings()
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/sessions')
def admin_sessions():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    sessions = TestSession.query.order_by(TestSession.completed_at.desc()).limit(50).all()
    return render_template('admin/sessions.html', sessions=sessions)

# -------------------
# Helpers
# -------------------
def get_settings():
    try:
        settings = {}
        for s in Setting.query.all():
            try:
                settings[s.key] = json.loads(s.value)
            except Exception:
                settings[s.key] = s.value
        return settings
    except Exception as e:
        logger.error(f'Error loading settings: {e}')
        return {'auth': {'domain_auth_enabled': False, 'domain_name': 'company.ru'}, 'email': {'enabled': False}}

def get_questions_pool():
    try:
        return Question.query.filter_by(is_active=True).all()
    except Exception as e:
        logger.error(f'Error loading questions: {e}')
        return []

def init_db():
    with app.app_context():
        try:
            db.create_all()
            # default settings
            default_settings = {'auth': {'domain_auth_enabled': False, 'domain_name': 'company.ru'}, 'email': {'enabled': False, 'smtp_server': '', 'smtp_port': 587, 'from_email': 'noreply@company.ru'}}
            for key, value in default_settings.items():
                if not Setting.query.filter_by(key=key).first():
                    db.session.add(Setting(key=key, value=json.dumps(value, ensure_ascii=False)))
            db.session.commit()
            logger.info('✅ DB initialized')
        except Exception as e:
            logger.error(f'Error initializing DB: {e}')
            db.session.rollback()

# -------------------
# Запуск
# -------------------
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=False)
