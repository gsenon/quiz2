# -*- coding: utf-8 -*-
import os, json, random, io
import logging
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from jinja2 import Environment

from config import Config
from auth import DomainAuth
from email_sender import EmailSender
from pdf_generator import PDFGenerator
from question_generator import QuestionGenerator

def shuffle_filter(seq):
    try:
        result = list(seq)
        random.shuffle(result)
        return result
    except:
        return seq



app = Flask(__name__)
app.secret_key = Config.APP_SECRET

# Инициализация модулей
domain_auth = DomainAuth()
email_sender = EmailSender()
pdf_generator = PDFGenerator()
# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Добавляем фильтр shuffle в Jinja2
app.jinja_env.filters['shuffle'] = shuffle_filter

# --------------- helpers ---------------
def today_pass():
    return Config.today_pass()

def load_db():
    if os.path.exists(Config.DATA_FILE):
        with open(Config.DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"questions": []}

def save_db(db):
    with open(Config.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def ensure_pool():
    db = load_db()
    if not db["questions"]:
        gen = QuestionGenerator()
        pool = gen.generate_pool(max_questions=10000)
        db["questions"] = pool
        save_db(db)
    return db

def require_admin():
    return session.get("is_admin") is True

# --------------- routes: public ---------------
@app.get("/")
def index():
    settings = Config.load_settings()
    return render_template("index.html", domain_auth_enabled=settings["domain_auth"]["enabled"])

@app.post("/start")
def start_quiz():
    settings = Config.load_settings()
    logger.debug(f"Настройки доменной авторизации: enabled={settings['domain_auth']['enabled']}")
    
    if settings["domain_auth"]["enabled"]:
        # Доменная аутентификация
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        # Безопасное логирование пароля
        password_hash = base64.b64encode(password.encode()).decode() if password else "empty"
        logger.debug(f"Попытка доменной аутентификации для: {username}, пароль (base64): {password_hash}")
        
        if not username or not password:
            logger.warning("Не указаны логин или пароль домена")
            flash("Введите логин и пароль домена", "error")
            return redirect(url_for("index"))
        
        if not domain_auth.authenticate(username, password):
            logger.warning(f"Неудачная аутентификация для: {username}")
            flash("Неверные учетные данные домена", "error")
            return redirect(url_for("index"))
        
        # Получаем информацию о пользователе
        user_info = domain_auth.get_user_info(username)
        
        # Создаем сессионный токен вместо хранения пароля
        session_token = domain_auth.create_session_token(username)
        
        # Сохраняем в сессии только необходимые данные
        session["user_info"] = user_info
        session["auth_token"] = session_token
        session["username"] = username
        session["authenticated"] = True
        
        logger.info(f"Успешная аутентификация пользователя: {username}")
        
    else:
        # Старая аутентификация по ФИО
        name = request.form.get("name", "").strip()
        if not name:
            logger.warning("Не указано ФИО или email")
            flash("Введите ФИО или email", "error")
            return redirect(url_for("index"))
        
        session["user_info"] = {"display_name": name, "username": name}
        session["authenticated"] = True
        logger.info(f"Аутентификация по ФИО: {name}")
    
    # Выбор вопросов
    db = ensure_pool()
    pool = db["questions"]
    count = min(50, len(pool)) #колличество вопросов
    selected = random.sample(pool, count) if count > 0 else []
    
    session["quiz_qids"] = [q["id"] for q in selected]
    session["quiz_idx"] = 0
    session["answers"] = {}
    
    logger.debug(f"Выбрано {len(selected)} вопросов для тестирования")
    
    return redirect(url_for("quiz"))

@app.get("/quiz")
def quiz():
    qids = session.get("quiz_qids", [])
    idx = session.get("quiz_idx", 0)
    if not qids:
        return redirect(url_for("index"))
    if idx >= len(qids):
        return redirect(url_for("results"))
    db = ensure_pool()
    pool = {q["id"]: q for q in db["questions"]}
    q = pool[qids[idx]]
    return render_template("quiz.html", q=q, idx=idx, total=len(qids))

@app.post("/quiz")
def quiz_post():
    qids = session.get("quiz_qids", [])
    idx = session.get("quiz_idx", 0)
    if not qids or idx >= len(qids):
        return redirect(url_for("index"))
    db = ensure_pool()
    pool = {q["id"]: q for q in db["questions"]}
    q = pool[qids[idx]]

    # Считываем ответ
    ans = None
    if q["type"] == "single_choice":
        ans = request.form.get("opt")
    elif q["type"] == "multiple_choice":
        ans = request.form.getlist("opt")
    elif q["type"] == "fill_blank":
        ans = request.form.get("text", "").strip()
    elif q["type"] == "open_question":
        ans = request.form.get("text", "").strip()
    elif q["type"] == "matching":
        ans = {}
        for pair in q["pairs"]:
            left = pair[0]
            ans[left] = request.form.get(f"match_{left}", "")

    answers = session.get("answers", {})
    answers[str(q["id"])] = ans
    session["answers"] = answers
    session["quiz_idx"] = idx + 1
    return redirect(url_for("quiz"))

@app.get("/results")
def results():
    qids = session.get("quiz_qids", [])
    answers = session.get("answers", {})
    user_info = session.get("user_info", {})
    db = ensure_pool()
    pool = {q["id"]: q for q in db["questions"]}

    total_weight = 0
    score = 0.0
    rows = []

    for qid in qids:
        q = pool[qid]
        ua = answers.get(str(qid), None)
        weight = q.get("weight", 1)
        total_weight += weight
        status = "❌"
        part = 0.0

        if q["type"] == "single_choice":
            ok = (ua == (q["correct"][0] if q.get("correct") else None))
            status = "✅" if ok else "❌"
            if ok: score += weight

        elif q["type"] == "multiple_choice":
            cs = set(q.get("correct", []))
            us = set(ua or [])
            if us == cs:
                status = "✅"
                score += weight
            elif us and us.issubset(cs):
                part = len(us)/max(1,len(cs))
                score += weight*part
                status = "🟡"

        elif q["type"] == "fill_blank":
            ok = isinstance(ua, str) and q.get("correct") and ua.lower().strip() == q["correct"][0].lower().strip()
            status = "✅" if ok else "❌"
            if ok: score += weight

        elif q["type"] == "open_question":
            text = (ua or "").lower()
            kw = [k.lower() for k in q.get("correct_phrases", [])]
            hits = sum(1 for k in kw if k in text)
            if hits >= max(1, len(kw)//2):
                status = "✅"
                score += weight
            elif hits > 0:
                part = hits / max(1,len(kw))
                score += weight*part
                status = "🟡"

        elif q["type"] == "matching":
            pairs = set(tuple(p) for p in q.get("pairs", []))
            user_pairs = set()
            for left,right in (ua or {}).items():
                if right:
                    user_pairs.add((left, right))
            if user_pairs == pairs:
                status = "✅"
                score += weight
            elif user_pairs and user_pairs.issubset(pairs):
                part = len(user_pairs)/max(1,len(pairs))
                score += weight*part
                status = "🟡"

        rows.append({
            "q": q,
            "ua": ua,
            "status": status
        })

    percent = round(100.0 * score / max(1,total_weight), 2)
    level = "L2" if percent >= 80 else "L1"
    results_data = {"percent": percent, "level": level}
    session["result"] = results_data
    
    # Генерация PDF и отправка email
    questions_dict = {qid: pool[qid] for qid in qids}
    pdf_data = pdf_generator.generate_results_pdf(user_info, questions_dict, answers, results_data)
    
    # Логирование для отладки
    logger.debug(f"Сгенерирован PDF размером: {len(pdf_data)} байт")
    
    # Безопасное логирование пользовательских данных
    safe_user_info = user_info.copy()
    if 'email' in safe_user_info and safe_user_info['email']:
        safe_user_info['email'] = safe_user_info['email'].split('@')[0] + '@***'
    logger.debug(f"Данные пользователя: {safe_user_info}")
    
    # Безопасное логирование email настроек
    email_settings = Config.load_settings()["email"].copy()
    if email_settings["smtp_password"]:
        email_settings["smtp_password"] = "***"
    if email_settings["smtp_username"]:
        email_settings["smtp_username"] = email_settings["smtp_username"].split('@')[0] + '@***'
    logger.debug(f"Настройки email: {email_settings}")
    
    # Отправка email вместо скачивания
    if email_sender.send_results(user_info, pdf_data, results_data):
        flash("Результаты отправлены на вашу почту", "success")
    else:
        flash("Ошибка отправки результатов", "error")
    
    return render_template("results.html", rows=rows, percent=percent, level=level)

# Middleware для проверки аутентификации
@app.before_request
def check_authentication():
    # Не проверяем аутентификацию для публичных маршрутов
    public_routes = ['index', 'start', 'quiz', 'quiz_post', 'results', 
                    'admin_login', 'admin_login_post', 'static']
    
    if request.endpoint in public_routes:
        return
    
    # Для админских маршрутов проверяем is_admin
    if request.endpoint and request.endpoint.startswith('admin_'):
        if not session.get('is_admin'):
            logger.warning(f"Попытка доступа к админ-маршруту без прав: {request.endpoint}")
            flash("Требуются права администратора", "error")
            return redirect(url_for('admin_login'))
    
    # Проверяем аутентификацию для защищенных маршрутов
    if not session.get('authenticated'):
        logger.warning(f"Попытка доступа к защищенному маршруту без аутентификации: {request.endpoint}")
        flash("Требуется аутентификация", "error")
        return redirect(url_for('index'))
    
    # Для доменной авторизации проверяем сессионный токен
    if session.get('username') and session.get('auth_token'):
        if not domain_auth.validate_session_token(session['auth_token'], session['username']):
            logger.warning(f"Невалидный сессионный токен для пользователя: {session['username']}")
            session.clear()
            flash("Сессия истекла, пожалуйста, войдите снова", "error")
            return redirect(url_for('index'))

# --------------- routes: admin ---------------
@app.get("/admin/login")
def admin_login():
    return render_template("admin/login.html")

@app.post("/admin/login")
def admin_login_post():
    login = request.form.get("login","").strip()
    pwd = request.form.get("password","").strip()
    if login == "admin" and pwd == today_pass():
        session["is_admin"] = True
        session["authenticated"] = True  # Добавьте эту строку
        session["username"] = "admin"    # Добавьте эту строку
        logger.info(f"Успешный вход в админку пользователя: {login}")
        return redirect(url_for("admin_dashboard"))
    flash("Неверные учетные данные", "error")
    logger.warning(f"Неудачная попытка входа в админку: {login}")
    return redirect(url_for("admin_login"))

@app.get("/admin/logout")
def admin_logout():
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"Пользователь {username} вышел из системы")
    flash("Вы успешно вышли из системы", "success")
    return redirect(url_for("index"))

@app.get("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = ensure_pool()
    return render_template("admin/dashboard.html", questions=db["questions"], today=datetime.now().strftime("%d.%m.%Y"))

@app.get("/admin/settings")
def admin_settings():
    if not require_admin():
        return redirect(url_for("admin_login"))
    
    settings = Config.load_settings()
    return render_template("admin/settings.html", settings=settings)

@app.post("/admin/settings")
def admin_settings_post():
    if not require_admin():
        return redirect(url_for("admin_login"))
    
    settings = Config.load_settings()
    
    # Обновление настроек домена
    settings["domain_auth"]["enabled"] = request.form.get("domain_enabled") == "on"
    settings["domain_auth"]["domain"] = request.form.get("domain", "")
    settings["domain_auth"]["ldap_server"] = request.form.get("ldap_server", "")
    settings["domain_auth"]["base_dn"] = request.form.get("base_dn", "")
    
    # Обновление настроек email
    settings["email"]["enabled"] = request.form.get("email_enabled") == "on"
    settings["email"]["smtp_server"] = request.form.get("smtp_server", "")
    settings["email"]["smtp_port"] = int(request.form.get("smtp_port", 587))
    settings["email"]["smtp_username"] = request.form.get("smtp_username", "")
    settings["email"]["smtp_password"] = request.form.get("smtp_password", "")
    settings["email"]["from_email"] = request.form.get("from_email", "")
    settings["email"]["admin_emails"] = [e.strip() for e in request.form.get("admin_emails", "").split(",") if e.strip()]
    settings["email"]["subject"] = request.form.get("email_subject", "Результаты тестирования")
    
    Config.save_settings(settings)
    flash("Настройки сохранены", "success")
    return redirect(url_for("admin_settings"))

@app.get("/admin/add")
def admin_add():
    if not require_admin():
        return redirect(url_for("admin_login"))
    return render_template("admin/add_edit.html", q=None)

@app.post("/admin/add")
def admin_add_post():
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = ensure_pool()
    q = _read_question_from_form()
    if not q:
        return redirect(url_for("admin_add"))
    # присвоить новый id
    max_id = max([qq["id"] for qq in db["questions"]], default=0)
    q["id"] = max_id + 1
    # проверка дубликата по тексту
    if any(qq["question"].strip() == q["question"].strip() for qq in db["questions"]):
        flash("Вопрос с такой формулировкой уже существует", "error")
        return redirect(url_for("admin_add"))
    db["questions"].append(q)
    save_db(db)
    flash("Вопрос добавлен", "success")
    return redirect(url_for("admin_dashboard"))

@app.get("/admin/edit/<int:qid>")
def admin_edit(qid):
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = ensure_pool()
    q = next((qq for qq in db["questions"] if qq["id"] == qid), None)
    if not q:
        flash("Вопрос не найден", "error")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/add_edit.html", q=q)

@app.post("/admin/edit/<int:qid>")
def admin_edit_post(qid):
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = ensure_pool()
    q = next((qq for qq in db["questions"] if qq["id"] == qid), None)
    if not q:
        flash("Вопрос не найден", "error")
        return redirect(url_for("admin_dashboard"))
    new_q = _read_question_from_form()
    if not new_q:
        return redirect(url_for("admin_edit", qid=qid))
    # проверка дубликата по тексту
    if any(qq["id"] != qid and qq["question"].strip() == new_q["question"].strip() for qq in db["questions"]):
        flash("Вопрос с такой формулировкой уже существует", "error")
        return redirect(url_for("admin_edit", qid=qid))
    # обновить
    new_q["id"] = qid
    idx = db["questions"].index(q)
    db["questions"][idx] = new_q
    save_db(db)
    flash("Вопрос обновлён", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/delete/<int:qid>")
def admin_delete(qid):
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = ensure_pool()
    before = len(db["questions"])
    db["questions"] = [q for q in db["questions"] if q["id"] != qid]
    after = len(db["questions"])
    save_db(db)
    if after < before:
        flash("Вопрос удалён", "success")
    else:
        flash("Вопрос не найден", "error")
    return redirect(url_for("admin_dashboard"))

def _read_question_from_form():
    qtype = request.form.get("type")
    level = request.form.get("level") or "L2"
    weight = int(request.form.get("weight") or 1)
    text = (request.form.get("question") or "").strip()
    if not qtype or not text:
        flash("Заполните тип и текст вопроса", "error")
        return None
    q = {"type": qtype, "question": text, "weight": weight, "level": level}
    if qtype in ("single_choice","multiple_choice"):
        options_raw = request.form.get("options","").strip()
        opts = [o.strip() for o in options_raw.split("\n") if o.strip()]
        opts = list(dict.fromkeys(opts))
        if len(opts) < 2:
            flash("Нужно минимум 2 варианта ответа", "error")
            return None
        correct_raw = request.form.get("correct","").strip()
        correct_list = [c.strip() for c in correct_raw.split("\n") if c.strip()]
        if not correct_list:
            flash("Укажите правильные ответы (каждый с новой строки)", "error")
            return None
        if qtype == "single_choice" and len(correct_list) > 1:
            flash("Для single_choice должен быть только один правильный ответ", "error")
            return None
        q["options"] = opts
        q["correct"] = correct_list
    elif qtype == "fill_blank":
        correct = (request.form.get("correct") or "").strip()
        if not correct:
            flash("Укажите правильный ответ", "error")
            return None
        q["correct"] = [correct]
    elif qtype == "open_question":
        correct_phrases_raw = request.form.get("correct_phrases","").strip()
        correct_phrases = [p.strip() for p in correct_phrases_raw.split("\n") if p.strip()]
        if not correct_phrases:
            flash("Укажите ключевые фразы (каждая с новой строки)", "error")
            return None
        q["correct_phrases"] = correct_phrases
    elif qtype == "matching":
        pairs_raw = request.form.get("pairs","").strip()
        pairs = []
        for line in pairs_raw.split("\n"):
            parts = line.strip().split(":")
            if len(parts) >= 2:
                left = parts[0].strip()
                right = parts[1].strip()
                if left and right:
                    pairs.append([left, right])
        if len(pairs) < 2:
            flash("Нужно минимум 2 пары", "error")
            return None
        q["pairs"] = pairs
    return q

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)