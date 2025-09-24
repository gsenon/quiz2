# -*- coding: utf-8 -*-
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

class PDFGenerator:
    def generate_results_pdf(self, user_info, questions, answers, results):
        """Генерация PDF с результатами"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Заголовок
        c.drawString(100, 800, "Результаты тестирования")
        c.drawString(100, 780, f"Пользователь: {user_info.get('display_name', '')}")
        c.drawString(100, 760, f"Результат: {results.get('percent', 0)}%")
        c.drawString(100, 740, f"Уровень: {results.get('level', 'L1')}")
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()