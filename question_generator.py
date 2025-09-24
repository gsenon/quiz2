# -*- coding: utf-8 -*-
import random

class QuestionGenerator:
    def __init__(self):
        self.categories = {
            "Python": ["основы", "функции", "ООП", "модули"],
            "SQL": ["SELECT", "JOIN", "GROUP BY", "индексы"],
            "Linux": ["команды", "файловая система", "процессы"]
        }
    
    def generate_question(self, qid, category, subcategory):
        base_text = f"Вопрос по {category} ({subcategory})"
        
        question_types = ["single_choice", "multiple_choice", "fill_blank"]
        q_type = random.choice(question_types)
        
        if q_type == "single_choice":
            return self._generate_single_choice(qid, base_text, category, subcategory)
        elif q_type == "multiple_choice":
            return self._generate_multiple_choice(qid, base_text, category, subcategory)
        else:
            return self._generate_fill_blank(qid, base_text, category, subcategory)
    
    def _generate_single_choice(self, qid, base_text, category, subcategory):
        question = f"{base_text} - выберите правильный вариант:"
        options = [f"Вариант {chr(65+i)}" for i in range(4)]
        correct = [options[0]]
        
        return {
            "id": qid,
            "question": question,
            "type": "single_choice",
            "options": options,
            "correct": correct,
            "category": category,
            "subcategory": subcategory,
            "level": "L1",
            "weight": 1
        }
    
    def _generate_multiple_choice(self, qid, base_text, category, subcategory):
        question = f"{base_text} - выберите все правильные варианты:"
        options = [f"Вариант {chr(65+i)}" for i in range(5)]
        correct = options[:2]
        
        return {
            "id": qid,
            "question": question,
            "type": "multiple_choice",
            "options": options,
            "correct": correct,
            "category": category,
            "subcategory": subcategory,
            "level": "L2",
            "weight": 2
        }
    
    def _generate_fill_blank(self, qid, base_text, category, subcategory):
        question = f"{base_text} - заполните пропуск: Основной язык программирования для веб-разработки это ______."
        correct = ["Python"]
        
        return {
            "id": qid,
            "question": question,
            "type": "fill_blank",
            "correct": correct,
            "category": category,
            "subcategory": subcategory,
            "level": "L1",
            "weight": 1
        }
    
    def generate_pool(self, max_questions=100):
        """Генерация пула вопросов"""
        questions = []
        qid = 1
        
        for category, subcategories in self.categories.items():
            for subcategory in subcategories:
                for i in range(10):  # По 10 вопросов на подкатегорию
                    if qid > max_questions:
                        break
                    question = self.generate_question(qid, category, subcategory)
                    questions.append(question)
                    qid += 1
        
        random.shuffle(questions)
        return questions