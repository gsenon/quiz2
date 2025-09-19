# -*- coding: utf-8 -*-
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

class PDFGenerator:
    def __init__(self):
        self.font_available = False
        self._register_fonts()
    
    def _register_fonts(self):
        try:
            if os.path.exists("DejaVuSans.ttf"):
                pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
                self.font_available = True
                print("Шрифт DejaVuSans успешно зарегистрирован")
            else:
                print("Файл шрифта DejaVuSans.ttf не найден, используется Helvetica")
        except Exception as e:
            print(f"Ошибка регистрации шрифта: {e}")
    
    def generate_results_pdf(self, user_info, questions, answers, results):
        buff = io.BytesIO()
        c = canvas.Canvas(buff, pagesize=A4)
        width, height = A4
        margin = 40
        y = height - margin
        
        font_name = "DejaVuSans" if self.font_available else "Helvetica"
        
        # Заголовок
        c.setFont(font_name, 16)
        c.drawString(margin, y, "Результаты теста")
        y -= 30
        
        # Информация о пользователе
        c.setFont(font_name, 12)
        c.drawString(margin, y, f"Пользователь: {user_info.get('display_name', '')}")
        y -= 20
        c.drawString(margin, y, f"Логин: {user_info.get('username', '')}")
        y -= 20
        c.drawString(margin, y, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        y -= 20
        c.drawString(margin, y, f"Итог: {results['percent']}%  |  Уровень: {results['level']}")
        y -= 30
        
        # Детализация ответов
        c.setFont(font_name, 14)
        c.drawString(margin, y, "Детализация ответов:")
        y -= 30
        
        c.setFont(font_name, 10)
        
        for i, (qid, q_data) in enumerate(questions.items(), 1):
            q = q_data
            ua = answers.get(str(qid), "—")
            correct_answer = self._get_correct_answer(q)
            
            # Проверяем, достаточно ли места на странице
            if y < 100:
                c.showPage()
                y = height - margin
                c.setFont(font_name, 10)
            
            # Вопрос
            question_text = f"{i}. {q['question']}"
            lines = self._wrap_text(c, question_text, font_name, 10, width - 2 * margin)
            
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
            correct_text = f"Правильный ответ: {correct_answer}"
            correct_lines = self._wrap_text(c, correct_text, font_name, 10, width - 2 * margin - 20)
            
            for line in correct_lines:
                if y < 50:
                    c.showPage()
                    y = height - margin
                    c.setFont(font_name, 10)
                c.drawString(margin + 20, y, line)
                y -= 15
            
            # Разделитель
            y -= 10
            if y < 50:
                c.showPage()
                y = height - margin
                c.setFont(font_name, 10)
            c.line(margin, y, width - margin, y)
            y -= 15
        
        c.save()
        buff.seek(0)
        return buff.getvalue()
    
    def _get_correct_answer(self, q):
        if q["type"] == "single_choice":
            return q['correct'][0] if q.get('correct') else '—'
        elif q["type"] == "multiple_choice":
            return ', '.join(q.get('correct', []))
        elif q["type"] == "fill_blank":
            return q['correct'][0] if q.get('correct') else '—'
        elif q["type"] == "open_question":
            return ', '.join(q.get('correct_phrases', []))
        elif q["type"] == "matching":
            pairs = [f"{p[0]} → {p[1]}" for p in q.get('pairs', [])]
            return ', '.join(pairs)
        return "—"
    
    def _wrap_text(self, canvas, text, font_name, font_size, max_width):
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if canvas.stringWidth(test_line, font_name, font_size) < max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        
        return lines