
# -*- coding: utf-8 -*-
import random
import re
from copy import deepcopy
from models import INTERNAL_KNOWLEDGE

def uniqueize(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

class QuestionGenerator:
    """
    Генерирует максимально большой пул уникальных вопросов на основе
    внутренней базы знаний. Цель — до 10 000 уникальных вопросов.
    """
    def __init__(self, knowledge=None, seed=42):
        self.kb = deepcopy(knowledge or INTERNAL_KNOWLEDGE)
        random.seed(seed)

    def _sanitize(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text

    def generate_pool(self, max_questions=10000):
        q = []
        q += self._component_from_description()
        q += self._description_from_component()
        q += self._interaction_matching()
        q += self._incidents_multi()
        q += self._rules_fill_open()
        # Вариативные переформулировки
        q = self._paraphrase(q)
        # Удаляем дубли по тексту вопроса
        uniq = []
        seen = set()
        for item in q:
            t = self._sanitize(item["question"])
            if t not in seen:
                seen.add(t)
                uniq.append(item)
            if len(uniq) >= max_questions:
                break
        # Гарантируем корректность вариантов
        for item in uniq:
            if item["type"] in ("single_choice", "multiple_choice"):
                opts = item.get("options", [])
                item["options"] = uniqueize(opts)
        # Проставим id
        for i, item in enumerate(uniq, 1):
            item["id"] = i
        return uniq

    # ---------- шаблоны генерации ----------
    def _component_from_description(self):
        forms = [
            "Какой компонент {desc}?",
            "Назовите компонент, который {desc}.",
            "Выберите компонент: он {desc}.",
            "Какой из компонентов {desc}?",
        ]
        out = []
        names = list(self.kb["components"].keys())
        for name, data in self.kb["components"].items():
            desc = data["description"].lower()
            wrong = [n for n in names if n != name]
            if len(wrong) < 3: 
                continue
            for f in forms:
                options = [name] + random.sample(wrong, 3)
                random.shuffle(options)
                out.append({
                    "type": "single_choice",
                    "question": f.format(desc=desc),
                    "options": options,
                    "correct": [name],
                    "weight": 1,
                    "level": "L2"
                })
        return out

    def _description_from_component(self):
        forms = [
            "Что делает компонент {name}?",
            "Выберите верное описание для {name}.",
            "Какова основная функция {name}?",
            "Какую задачу решает {name}?",
        ]
        out = []
        names = list(self.kb["components"].keys())
        descs = [d["description"] for d in self.kb["components"].values()]
        for name, data in self.kb["components"].items():
            right = data["description"]
            wrong = [d for d in descs if d != right]
            if len(wrong) < 3:
                continue
            for f in forms:
                options = [right] + random.sample(wrong, 3)
                random.shuffle(options)
                out.append({
                    "type": "single_choice",
                    "question": f.format(name=name),
                    "options": options,
                    "correct": [right],
                    "weight": 1,
                    "level": "L1"
                })
        return out

    def _interaction_matching(self):
        out = []
        for inter in self.kb["interactions"]:
            parts = [p.strip() for p in re.split(r"[→>-]+", inter) if p.strip()]
            if len(parts) < 2: 
                continue
            pairs = [(parts[i], parts[i+1]) for i in range(len(parts)-1)]
            random.shuffle(pairs)
            out.append({
                "type": "matching",
                "question": "Установите соответствия в технологической цепочке обработки:",
                "pairs": pairs,
                "weight": len(pairs),
                "level": "L2"
            })
        return out

    def _incidents_multi(self):
        out = []
        # Собираем общий пул действий
        pool = set()
        for inc in self.kb["incidents"]:
            if "→" in inc and ":" in inc:
                _, tail = inc.split("→", 1)
                if ":" in tail:
                    _, actions = tail.split(":", 1)
                    for a in actions.split(","):
                        pool.add(a.strip())
        for inc in self.kb["incidents"]:
            if ":" not in inc: 
                continue
            problem, rest = inc.split("→", 1) if "→" in inc else (inc, inc)
            if ":" not in rest:
                continue
            _, actions = rest.split(":", 1)
            correct = [a.strip() for a in actions.split(",") if a.strip()]
            wrong = list(pool.difference(correct))
            add_wrong = random.sample(wrong, min(max(0, 6-len(correct)), len(wrong))) if wrong else []
            options = list(set(correct + add_wrong))
            random.shuffle(options)
            out.append({
                "type": "multiple_choice",
                "question": f"Ваши первичные действия, если {problem.strip().lower()}:",
                "options": options,
                "correct": correct,
                "weight": max(1, len(correct)),
                "level": "L2"
            })
        return out

    def _rules_fill_open(self):
        out = []
        rules = self.kb["rules"]
        for rule in rules:
            words = rule.split()
            if words and words[0].lower() == "только" and len(words) > 1:
                blank = words[1]
                q = rule.replace(blank, "______", 1)
                out.append({
                    "type": "fill_blank",
                    "question": q,
                    "correct": [blank],
                    "weight": 1,
                    "level": "L1"
                })
            else:
                # Открытые по ключевым фразам
                if "dovecot-rms" in rule.lower():
                    out.append({
                        "type": "open_question",
                        "question": "Почему изменения в БД должны выполняться только через dovecot-rms?",
                        "correct_phrases": [
                            "целостность", "индексы", "рассинхронизация", "согласованность"
                        ],
                        "weight": 2,
                        "level": "L2"
                    })
                if "подключения" in rule.lower():
                    out.append({
                        "type": "open_question",
                        "question": "Зачем направлять все подключения пользователя в один dovecot-rms?",
                        "correct_phrases": [
                            "согласованность", "сессия", "избежать рассинхронизации"
                        ],
                        "weight": 2,
                        "level": "L1"
                    })
        # Общий архитектурный открытый
        out.append({
            "type": "open_question",
            "question": "Опишите путь входящего письма от приёма до хранения.",
            "correct_phrases": [
                "resmtp", "mx-in", "director", "dovecot-rms", "проверка"
            ],
            "weight": 3,
            "level": "L2"
        })
        return out

    def _paraphrase(self, items):
        """Небольшие переформулировки для увеличения разнообразия без потери смысла."""
        paraphrased = []
        for item in items:
            paraphrased.append(item)
            if item["type"] == "single_choice":
                # альтернативная формулировка
                alt = dict(item)
                alt["question"] = "Определите компонент: " + item["question"].rstrip("?").strip(".") + "."
                paraphrased.append(alt)
            elif item["type"] == "multiple_choice":
                alt = dict(item)
                alt["question"] = item["question"].replace("первичные действия", "какие шаги вы предпримете")
                paraphrased.append(alt)
        return paraphrased
