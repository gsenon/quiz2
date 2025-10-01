# app/generators/question_generator.py
import random
import json
import logging
from typing import List, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self):
        self.components_data = self._load_components_data()
        self.templates = self._load_templates()
        self.generated_hashes = set()
        self._question_pool = []
        
    def _load_components_data(self) -> Dict:
        """Загрузка данных о компонентах из предоставленных материалов"""
        return {
            # Компоненты и их функции
            'resmtp': {
                'functions': [
                    "обрабатывает входящие SMTP-сообщения и выполняет первичную проверку",
                    "проверяет белые и черные списки IP и хостов отправителей",
                    "балансирует входящие письма на хосты mx-in",
                    "проверяет максимальный размер письма"
                ],
                'config_files': ['resmtp.conf'],
                'interactions': ['mx-in', 'dovecot-rpc', 'dns-black-list', 'dns-white-list']
            },
            'mx-in': {
                'functions': ["очередь входящих писем"],
                'config_files': ['main.cf'],
                'interactions': ['director', 'resmtp']
            },
            'mx-out': {
                'functions': ["очередь исходящих писем"],
                'config_files': ['main.cf'],
                'interactions': ['compose', 'carlos', 'fallback']
            },
            'director': {
                'functions': ["балансировка IMAP-подключений"],
                'interactions': ['dovecot', 'mx-in']
            },
            'dovecot-rms': {
                'functions': ["хранение тел писем в Cassandra"],
                'config_files': ['dovecot.conf'],
                'interactions': ['director', 'cassandra', 'postgresql', 'mail-search']
            },
            'compose': {
                'functions': ["создание исходящих писем"],
                'interactions': ['mx-out', 'mail-id']
            },
            'mail-id': {
                'functions': ["авторизация пользователей"],
                'interactions': ['director', 'memcached', 'adsync']
            },
            'caldav': {
                'functions': ["работа с календарями"],
                'interactions': ['beanstalkd', 'caldav-mail']
            },
            'beanstalkd': {
                'functions': ["очередь событий"],
                'interactions': ['caldav', 'mail-events']
            },
            'caldav-mail': {
                'functions': ["уведомления о событиях календаря"],
                'interactions': ['caldav', 'mx-out']
            }
        }
    
    def _load_templates(self) -> Dict:
        """Шаблоны вопросов с фонетическими вариациями"""
        return {
            'component_function': [
                "Какой компонент {function}?",
                "Определите компонент: {function}.",
                "Назовите компонент, который {function}.",
                "Выберите компонент: он {function}.",
                "Какой из компонентов {function}?",
                "Какой сервис отвечает за {function}?",
                "Определите сервис: {function}.",
                "Какой модуль выполняет {function}?"
            ],
            'function_component': [
                "Что делает компонент {component}?",
                "Определите функцию: Что делает компонент {component}.",
                "Выберите верное описание для {component}.",
                "Какова основная функция {component}?",
                "Какую задачу решает {component}?",
                "Какая функция у компонента {component}?",
                "Определите назначение сервиса {component}."
            ],
            'configuration': [
                "В каком файле настраивается {component}?",
                "Какой файл конфигурации используется для {component}?",
                "Где находятся настройки {component}?",
                "Определите файл конфигурации для {component}.",
                "В каком конфиг-файле настраивается {component}?"
            ],
            'interaction': [
                "С какими компонентами взаимодействует {component}?",
                "Какие сервисы связаны с {component}?",
                "Определите взаимодействия компонента {component}.",
                "С какими модулями интегрируется {component}?"
            ],
            'troubleshooting': [
                "Какие компоненты проверять при проблеме с {problem}?",
                "Ваши первичные действия, если {problem}:",
                "Ваши какие шаги вы предпримете, если {problem}:",
                "Как диагностировать проблему с {problem}?"
            ]
        }
    
    def _phonetic_variations(self, text: str) -> str:
        """Создание фонетических вариаций текста"""
        variations = {
            'компонент': ['компонент', 'сервис', 'модуль', 'элемент системы', 'блок'],
            'обрабатывает': ['обрабатывает', 'выполняет обработку', 'осуществляет обработку', 'занимается обработкой'],
            'проверяет': ['проверяет', 'выполняет проверку', 'осуществляет проверку', 'проводит проверку'],
            'очередь': ['очередь', 'буфер', 'список обработки', 'очередь сообщений'],
            'балансировка': ['балансировка', 'распределение нагрузки', 'балансирование', 'распределение'],
            'хранение': ['хранение', 'сохранение', 'хранение данных', 'сохранение информации'],
            'авторизация': ['авторизация', 'аутентификация', 'проверка доступа', 'идентификация']
        }
        
        result = text
        for original, variants in variations.items():
            if original in result:
                result = result.replace(original, random.choice(variants), 1)
        
        return result
    
    def _generate_question_hash(self, question_text: str, correct_answers: List) -> str:
        """Генерация хеша для проверки уникальности"""
        return hash(frozenset([question_text.strip().lower()] + sorted(correct_answers)))
    
    def generate_single_choice(self, component: str = None, used_hashes: set = None) -> Dict:
        """Генерация вопроса с одним правильным ответом"""
        if component is None:
            components = list(self.components_data.keys())
            component = random.choice(components)
        
        if used_hashes is None:
            used_hashes = set()
            
        component_data = self.components_data[component]
        
        # Выбираем случайный шаблон
        template_type = random.choice(['component_function', 'function_component'])
        
        if template_type == 'component_function':
            function = random.choice(component_data['functions'])
            function = self._phonetic_variations(function)
            template = random.choice(self.templates[template_type])
            question_text = template.format(function=function)
            correct_answers = [component]
        
        elif template_type == 'function_component':
            template = random.choice(self.templates[template_type])
            question_text = template.format(component=component)
            correct_answers = [random.choice(component_data['functions'])]
        
        # Генерируем неправильные варианты
        other_components = [c for c in self.components_data.keys() if c != component]
        wrong_answers = random.sample(other_components, min(3, len(other_components)))
        options = correct_answers + wrong_answers
        random.shuffle(options)
        
        question_hash = self._generate_question_hash(question_text, correct_answers)
        
        # Проверяем уникальность
        if question_hash in used_hashes or question_hash in self.generated_hashes:
            return self.generate_single_choice(component, used_hashes)
        
        used_hashes.add(question_hash)
        self.generated_hashes.add(question_hash)
        
        return {
            'type': 'single_choice',
            'question': question_text,
            'options': options,
            'correct': correct_answers,
            'component': component,
            'level': random.choice(['L1', 'L2']),
            'weight': 1
        }
    
    def generate_multiple_choice(self, problem_type: str = None, used_hashes: set = None) -> Dict:
        """Генерация вопроса с несколькими правильными ответами"""
        if used_hashes is None:
            used_hashes = set()
            
        troubleshooting_map = {
            'ошибка авторизации': ['mail-id', 'memcached', 'adsync'],
            'письма теряются': ['journaling', 'nats', 'mail-events'],
            'календарь не синхронизируется': ['caldav', 'beanstalkd', 'network'],
            'не отправляются письма': ['mx-out', 'compose', 'фильтры'],
            'пользователь не получает письма': ['resmtp', 'mx-in', 'квоту в directory']
        }
        
        if problem_type is None or problem_type not in troubleshooting_map:
            problem_type = random.choice(list(troubleshooting_map.keys()))
        
        correct_components = troubleshooting_map[problem_type]
        template = random.choice(self.templates['troubleshooting'])
        question_text = template.format(problem=problem_type)
        
        # Генерируем все возможные варианты
        all_components = list(self.components_data.keys()) + ['network', 'фильтры', 'квоту в directory']
        wrong_components = [c for c in all_components if c not in correct_components]
        wrong_answers = random.sample(wrong_components, min(3, len(wrong_components)))
        
        options = correct_components + wrong_answers
        random.shuffle(options)
        
        question_hash = self._generate_question_hash(question_text, correct_components)
        
        if question_hash in used_hashes or question_hash in self.generated_hashes:
            return self.generate_multiple_choice(problem_type, used_hashes)
        
        used_hashes.add(question_hash)
        self.generated_hashes.add(question_hash)
        
        return {
            'type': 'multiple_choice',
            'question': question_text,
            'options': options,
            'correct': correct_components,
            'problem_type': problem_type,
            'level': 'L2',
            'weight': 3
        }
    
    def ensure_diversity(self, questions: List[Dict], pool_size: int = 50) -> List[Dict]:
        """Обеспечивает разнообразие вопросов в пуле"""
        component_count = {}
        question_hashes = set()
        diverse_questions = []
        
        for question in questions:
            component = question.get('component') or question.get('problem_type', 'unknown')
            question_hash = self._generate_question_hash(question['question'], question['correct'])
            
            # Проверяем, что в пуле не больше 2 вопросов на компонент
            if component_count.get(component, 0) >= 2:
                continue
            
            # Проверяем уникальность вопроса
            if question_hash in question_hashes:
                continue
            
            component_count[component] = component_count.get(component, 0) + 1
            question_hashes.add(question_hash)
            diverse_questions.append(question)
            
            if len(diverse_questions) >= pool_size:
                break
        
        return diverse_questions
    
    def generate_question_pool(self, size: int = 100) -> List[Dict]:
        """Генерация большого пула вопросов"""
        questions = []
        components = list(self.components_data.keys())
        problem_types = ['ошибка авторизации', 'письма теряются', 'календарь не синхронизируется', 
                        'не отправляются письма', 'пользователь не получает письма']
        
        used_hashes = set()
        
        for i in range(size):
            try:
                if i % 5 == 0:  # Каждый 5-й вопрос - multiple choice
                    problem_type = random.choice(problem_types)
                    question = self.generate_multiple_choice(problem_type, used_hashes)
                else:
                    component = random.choice(components)
                    question = self.generate_single_choice(component, used_hashes)
                
                if question:
                    questions.append(question)
                
                if i % 100 == 0 and i > 0:
                    logger.info(f"Сгенерировано {i} вопросов")
                    
            except Exception as e:
                logger.error(f"Ошибка при генерации вопроса {i}: {e}")
                continue
        
        logger.info(f"Всего сгенерировано {len(questions)} вопросов")
        return questions
    
    def get_test_questions(self, count: int = 50) -> List[Dict]:
        """Получение разнообразного набора вопросов для теста"""
        if not self._question_pool:
            self._question_pool = self.generate_question_pool(100)
        
        if not self._question_pool:
            logger.error("Не удалось сгенерировать вопросы для теста")
            return []
        
        # Выбираем случайные вопросы и обеспечиваем разнообразие
        candidate_count = min(count * 3, len(self._question_pool))
        candidate_questions = random.sample(self._question_pool, candidate_count)
        return self.ensure_diversity(candidate_questions, count)