
# -*- coding: utf-8 -*-
import os, json, random, io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from question_generator import QuestionGenerator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from jinja2 import Environment

APP_SECRET = os.environ.get("APP_SECRET", "super_secret_key_change_me")
DATA_FILE = "quiz_data.json"

def shuffle_filter(seq):
    try:
        result = list(seq)
        random.shuffle(result)
        return result
    except:
        return seq

app = Flask(__name__)
app.secret_key = APP_SECRET

# Добавляем фильтр shuffle в Jinja2
app.jinja_env.filters['shuffle'] = shuffle_filter

# Регистрация шрифта после создания app
try:
    # Проверяем существует ли файл шрифта
    if os.path.exists("DejaVuSans.ttf"):
        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
        FONT_AVAILABLE = True
        print("Шрифт DejaVuSans успешно зарегистрирован")
    else:
        FONT_AVAILABLE = False
        print("Файл шрифта DejaVuSans.ttf не найден")
except Exception as e:
    FONT_AVAILABLE = False
    print(f"Ошибка регистрации шрифта: {e}")

# --------------- helpers ---------------
def today_pass():
    # Пароль = текущая дата в формате DDMMYYYY
    return datetime.now().strftime("%d%m%Y")

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"questions": []}
        save_db(db)
    return db

def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
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
    return render_template("index.html")

@app.post("/start")
def start_quiz():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Введите ФИО или email.", "error")
        return redirect(url_for("index"))
    db = ensure_pool()
    pool = db["questions"]
    # Выбираем 50 случайных уникальных вопросов
    count = min(50, len(pool))
    selected = random.sample(pool, count) if count > 0 else []
    # Сохраняем в сессию
    session["quiz_name"] = name
    session["quiz_qids"] = [q["id"] for q in selected]
    session["quiz_idx"] = 0
    session["answers"] = {}
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
    session["result"] = {"percent": percent, "level": level}
    return render_template("results.html", rows=rows, percent=percent, level=level)

@app.get("/download")
def download_pdf():
    name = session.get("quiz_name", "Пользователь")
    res = session.get("result", {"percent": 0, "level": "L1"})
    qids = session.get("quiz_qids", [])
    answers = session.get("answers", {})
    db = ensure_pool()
    pool = {q["id"]: q for q in db["questions"]}
    
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4
    margin = 40
    y = height - margin
    
    # Используем шрифт с поддержкой кириллицы
    if FONT_AVAILABLE:
        font_name = "DejaVuSans"
    else:
        font_name = "Helvetica"
    
    # Заголовок
    c.setFont(font_name, 16)
    c.drawString(margin, y, "Результаты теста")
    y -= 30
    
    # Информация о пользователе
    c.setFont(font_name, 12)
    c.drawString(margin, y, f"Пользователь: {name}")
    y -= 20
    c.drawString(margin, y, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    y -= 20
    c.drawString(margin, y, f"Итог: {res['percent']}%  |  Уровень: {res['level']}")
    y -= 30
    
    # Детализация ответов
    c.setFont(font_name, 14)
    c.drawString(margin, y, "Детализация ответов:")
    y -= 30
    
    c.setFont(font_name, 10)
    
    for i, qid in enumerate(qids, 1):
        q = pool[qid]
        ua = answers.get(str(qid), "—")
        
        # Проверяем, достаточно ли места на странице
        if y < 100:
            c.showPage()
            y = height - margin
            c.setFont(font_name, 10)
        
        # Вопрос
        question_text = f"{i}. {q['question']}"
        # Разбиваем длинный вопрос на несколько строк
        words = question_text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if c.stringWidth(test_line, font_name, 10) < (width - 2 * margin):
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        
        # Выводим вопрос
        for line in lines:
            if y < 50:
                c.showPage()
                y = height - margin
                c.setFont(font_name, 10)
            c.drawString(margin, y, line)
            y -= 15
        
        # Ответ пользователя
        user_answer = f"Ваш ответ: {ua}"
        if y < 50:
            c.showPage()
            y = height - margin
            c.setFont(font_name, 10)
        c.drawString(margin + 20, y, user_answer)
        y -= 15
        
        # Правильный ответ
        if q["type"] == "single_choice":
            correct_answer = f"Правильный ответ: {q['correct'][0] if q.get('correct') else '—'}"
        elif q["type"] == "multiple_choice":
            correct_answer = f"Правильные ответы: {', '.join(q.get('correct', []))}"
        elif q["type"] == "fill_blank":
            correct_answer = f"Правильный ответ: {q['correct'][0] if q.get('correct') else '—'}"
        elif q["type"] == "open_question":
            correct_answer = f"Ключевые фразы: {', '.join(q.get('correct_phrases', []))}"
        elif q["type"] == "matching":
            pairs = [f"{p[0]} → {p[1]}" for p in q.get('pairs', [])]
            correct_answer = f"Правильные пары: {', '.join(pairs)}"
        else:
            correct_answer = "Правильный ответ: —"
        
        # Разбиваем длинный правильный ответ на несколько строк
        words = correct_answer.split()
        correct_lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if c.stringWidth(test_line, font_name, 10) < (width - 2 * margin - 20):
                current_line = test_line
            else:
                correct_lines.append(current_line)
                current_line = word + " "
        if current_line:
            correct_lines.append(current_line)
        
        # Выводим правильный ответ
        for line in correct_lines:
            if y < 50:
                c.showPage()
                y = height - margin
                c.setFont(font_name, 10)
            c.drawString(margin + 20, y, line)
            y -= 15
        
        # Разделитель между вопросами
        y -= 10
        if y < 50:
            c.showPage()
            y = height - margin
            c.setFont(font_name, 10)
        c.line(margin, y, width - margin, y)
        y -= 15
    
    c.save()
    buff.seek(0)
    return send_file(buff, as_attachment=True, download_name=f"results_{name}.pdf")

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
        return redirect(url_for("admin_dashboard"))
    flash("Неверные учетные данные", "error")
    return redirect(url_for("admin_login"))

@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

@app.get("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = ensure_pool()
    return render_template("admin/dashboard.html", questions=db["questions"], today=datetime.now().strftime("%d.%m.%Y"))

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
    flash("Вопрос добавлен", "ok")
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
    flash("Вопрос обновлён", "ok")
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
    flash("Вопрос удалён" if after < before else "Вопрос не найден", "ok" if after < before else "error")
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
        if not set(correct_list).issubset(set(opts)):
            flash("Все правильные ответы должны присутствовать среди вариантов", "error")
            return None
        if qtype == "single_choice" and len(correct_list) != 1:
            flash("Для типа 'один ответ' должен быть ровно один правильный", "error")
            return None
        q["options"] = opts
        q["correct"] = correct_list
    elif qtype == "fill_blank":
        correct = (request.form.get("correct_single") or "").strip()
        if not correct:
            flash("Укажите правильное значение для заполняемого поля", "error")
            return None
        q["correct"] = [correct]
    elif qtype == "open_question":
        phrases_raw = request.form.get("phrases","").strip()
        phrases = [p.strip() for p in phrases_raw.split("\n") if p.strip()]
        if not phrases:
            flash("Добавьте ключевые фразы для проверки открытого ответа", "error")
            return None
        q["correct_phrases"] = phrases
    elif qtype == "matching":
        pairs_raw = request.form.get("pairs","").strip()
        pairs = []
        for line in pairs_raw.split("\n"):
            if "->" in line:
                left, right = line.split("->", 1)
                pairs.append([left.strip(), right.strip()])
        if not pairs:
            flash("Добавьте хотя бы одну пару в формате A->B", "error")
            return None
        q["pairs"] = pairs
    else:
        flash("Неизвестный тип вопроса", "error")
        return None
    return q

if __name__ == "__main__":
    ensure_pool()
    app.run(host="0.0.0.0", port=8000, debug=True)
