# -*- coding: utf-8 -*-
import random

class QuestionGenerator:
    def generate_pool(self, max_questions=1000):
        pool = []
        for i in range(max_questions):
            q = self._generate_question(i)
            pool.append(q)
        return pool

    def _generate_question(self, idx):
        types = ["single_choice", "multiple_choice", "fill_blank", "open_question", "matching"]
        qtype = random.choice(types)
        level = random.choice(["L1", "L2"])
        weight = random.randint(1, 3)
        
        if qtype == "single_choice":
            return self._generate_single_choice(idx, level, weight)
        elif qtype == "multiple_choice":
            return self._generate_multiple_choice(idx, level, weight)
        elif qtype == "fill_blank":
            return self._generate_fill_blank(idx, level, weight)
        elif qtype == "open_question":
            return self._generate_open_question(idx, level, weight)
        elif qtype == "matching":
            return self._generate_matching(idx, level, weight)

    def _generate_single_choice(self, idx, level, weight):
        question = f"Вопрос {idx+1}: Выберите один правильный ответ"
        options = [f"Вариант {i+1}" for i in range(4)]
        correct = [options[0]]
        return {
            "id": idx+1,
            "type": "single_choice",
            "question": question,
            "options": options,
            "correct": correct,
            "level": level,
            "weight": weight
        }

    def _generate_multiple_choice(self, idx, level, weight):
        question = f"Вопрос {idx+1}: Выберите все правильные ответы"
        options = [f"Вариант {i+1}" for i in range(5)]
        correct = options[:2]
        return {
            "id": idx+1,
            "type": "multiple_choice",
            "question": question,
            "options": options,
            "correct": correct,
            "level": level,
            "weight": weight
        }

    def _generate_fill_blank(self, idx, level, weight):
        question = f"Вопрос {idx+1}: Заполните пропуск: Столица России - ______"
        correct = ["Москва"]
        return {
            "id": idx+1,
            "type": "fill_blank",
            "question": question,
            "correct": correct,
            "level": level,
            "weight": weight
        }

    def _generate_open_question(self, idx, level, weight):
        question = f"Вопрос {idx+1}: Опишите основные принципы ООП"
        correct_phrases = ["инкапсуляция", "наследование", "полиморфизм", "абстракция"]
        return {
            "id": idx+1,
            "type": "open_question",
            "question": question,
            "correct_phrases": correct_phrases,
            "level": level,
            "weight": weight
        }

    def _generate_matching(self, idx, level, weight):
        question = f"Вопрос {idx+1}: Сопоставьте элементы"
        pairs = [
            ["Python", "Django"],
            ["JavaScript", "React"],
            ["Ruby", "Rails"],
            ["PHP", "Laravel"]
        ]
        return {
            "id": idx+1,
            "type": "matching",
            "question": question,
            "pairs": pairs,
            "level": level,
            "weight": weight
        }