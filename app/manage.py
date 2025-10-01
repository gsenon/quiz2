#!/usr/bin/env python3
import os
import sys

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(__file__))

from app import app, db, init_db

def main():
    """Утилита управления базой данных"""
    with app.app_context():
        if init_db():
            print("✅ Database initialized")
        else:
            print("❌ Database initialization failed")
            sys.exit(1)

if __name__ == "__main__":
    main()