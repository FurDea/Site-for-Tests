from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import os
import mimetypes
import sqlite3

DATABASE_PATH = os.path.join(os.path.dirname(file), 'python_db.sqlite')
users = []
test_results = []

# init_db.py
# Запусти этот файл один раз для создания БД и таблиц

import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(file), 'database.db')

def init_database():
    """Создает БД и все таблицы"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица USERS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица TESTS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_by INTEGER NOT NULL,
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица TEST_QUESTIONS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица TEST_RESULTS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL,
            result_text TEXT,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица USER_ANSWERS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            user_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            FOREIGN KEY (result_id) REFERENCES test_results(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES test_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # Вставляем начальные данные (админ + тестовые пользователи)
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES ('admin', 'admin@example.com', 'hashed_password_123', 'Admin User', 'admin')
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES ('alice', 'alice@example.com', 'hashed_pass_alice', 'Alice Smith', 'user')
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES ('bob', 'bob@example.com', 'hashed_pass_bob', 'Bob Johnson', 'user')
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✅ БД создана успешно!")
    print(f"📁 Путь: {DATABASE_PATH}")
    print(f"👤 Тестовые аккаунты:")
    print(f"   - admin / admin123")
    print(f"   - alice / alice123")

if name == 'main':
    init_database()

