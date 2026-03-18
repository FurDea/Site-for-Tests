from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import os
import mimetypes
import sqlite3
import hashlib
import uuid
import urllib.parse

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

# Функция для хеширования паролей
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Функция для получения соединения с БД
def get_db():
    return sqlite3.connect(DATABASE_PATH)

# Инициализация БД при запуске
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
            title TEXT NOT NULL,
            description TEXT,
            test_type TEXT NOT NULL,
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
            answers TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
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
            user_answer INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,
            FOREIGN KEY (result_id) REFERENCES test_results(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES test_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # Вставляем начальные данные (админ + тестовые пользователи)
    admin_hash = hash_password('admin123')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ('admin', 'admin@example.com', admin_hash, 'Admin User', 'admin'))
    
    alice_hash = hash_password('alice123')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ('alice', 'alice@example.com', alice_hash, 'Alice Smith', 'user'))
    
    bob_hash = hash_password('bob123')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ('bob', 'bob@example.com', bob_hash, 'Bob Johnson', 'user'))
    
    conn.commit()
    conn.close()
    
    print(f"✅ БД инициализирована успешно!")
    print(f"📁 Путь: {DATABASE_PATH}")
    print(f"👤 Тестовые аккаунты:")
    print(f"   - admin / admin123")
    print(f"   - alice / alice123")
    print(f"   - bob / bob123")

# Вызываем инициализацию при запуске
init_database()

class PersonalityHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def get_client_ip(self):
        if "X-Forwarded-For" in self.headers:
            return self.headers["X-Forwarded-For"].split(",")[0].strip()
        return self.client_address[0]

    def do_GET(self):
        path = self.path

        if path == "/":
            path = "/index.html"
        elif path == "/admin":
            path = "/admin_panel_unified.html"

        # Убираем ведущий слеш для получения пути к файлу
        if path.startswith('/'):
            filepath = path[1:]
        else:
            filepath = path

        # Проверяем существование файла
        if not os.path.exists(filepath):
            self.send_error(404, f"File {filepath} not found")
            return

        content_type, _ = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            with open(filepath, "rb") as f:
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        # ---- регистрация / логин ----
        if self.path == "/api/register":
            required_fields = ["name", "email", "password"]
            if not all(field in data for field in required_fields):
                self.send_json({"error": "Missing fields"}, 400)
                return

            name = data["name"].strip()
            email = data["email"].strip().lower()
            password = data["password"]
            
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                # Проверяем существование пользователя
                cursor.execute('SELECT id, username, email, role FROM users WHERE email = ?', (email,))
                existing = cursor.fetchone()
                
                if existing:
                    self.send_json({
                        "status": "exists",
                        "user": {
                            "id": existing[0],
                            "name": existing[1],
                            "email": existing[2],
                            "role": existing[3]
                        }
                    })
                    conn.close()
                    return
                
                # Создаем нового пользователя
                password_hash = hash_password(password)
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                ''', (name, email, password_hash, 'user'))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                self.send_json({
                    "status": "registered",
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "role": "user"
                })
                
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        # ---- логин ----
        elif self.path == "/api/login":
            required_fields = ["email", "password"]
            if not all(field in data for field in required_fields):
                self.send_json({"error": "Missing fields"}, 400)
                return

            email = data["email"].strip().lower()
            password = data["password"]
            password_hash = hash_password(password)
            
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT id, username, email, role FROM users 
                    WHERE email = ? AND password_hash = ?
                ''', (email, password_hash))
                
                user = cursor.fetchone()
                
                if user:
                    self.send_json({
                        "status": "success",
                        "user": {
                            "id": user[0],
                            "name": user[1],
                            "email": user[2],
                            "role": user[3]
                        }
                    })
                else:
                    self.send_json({"error": "Invalid email or password"}, 401)
                    
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        # ---- проверка админа ----
        elif self.path == "/api/check-admin":
            required_fields = ["userId", "email"]
            if not all(field in data for field in required_fields):
                self.send_json({"isAdmin": False}, 200)
                return

            user_id = data["userId"]
            email = data["email"]
            
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT role FROM users WHERE id = ? AND email = ?', (user_id, email))
                result = cursor.fetchone()
                
                if result and result[0] == 'admin':
                    self.send_json({"isAdmin": True})
                else:
                    self.send_json({"isAdmin": False})
                    
            except sqlite3.Error:
                self.send_json({"isAdmin": False})
            finally:
                conn.close()

        # ---- получение всех тестов ----
        elif self.path == "/api/get-tests":
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT id, title, description, test_type, created_by, is_published 
                    FROM tests WHERE is_published = 1
                ''')
                
                tests = []
                for row in cursor.fetchall():
                    tests.append({
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "test_type": row[3],
                        "created_by": row[4],
                        "is_published": row[5]
                    })
                
                self.send_json({"tests": tests})
                
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        # ---- получение теста по ID ----
        elif self.path == "/api/get-test":
            if "testId" not in data:
                self.send_json({"error": "Missing testId"}, 400)
                return
            
            test_id = data["testId"]
            
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                # Получаем тест
                cursor.execute('''
                    SELECT id, title, description, test_type, created_by 
                    FROM tests WHERE id = ? AND is_published = 1
                ''', (test_id,))
                
                test_row = cursor.fetchone()
                if not test_row:
                    self.send_json({"error": "Test not found"}, 404)
                    return
                
                # Получаем вопросы
                cursor.execute('''
                    SELECT id, question_text, answers, correct_answer 
                    FROM test_questions WHERE test_id = ?
                ''', (test_id,))
                
                questions = []
                for q_row in cursor.fetchall():
                    questions.append({
                        "id": q_row[0],
                        "text": q_row[1],
                        "answers": json.loads(q_row[2]),
                        "correct": q_row[3]
                    })
                
                self.send_json({
                    "test": {
                        "id": test_row[0],
                        "title": test_row[1],
                        "description": test_row[2],
                        "test_type": test_row[3],
                        "created_by": test_row[4],
                        "questions": questions
                    }
                })
                
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        # ---- сохранение теста (для админа) ----
        elif self.path == "/api/save-test":
            required_fields = ["title", "description", "test_type", "questions", "created_by"]
            if not all(field in data for field in required_fields):
                self.send_json({"error": "Missing fields"}, 400)
                return
            
            # Проверяем, что пользователь - админ
            user_id = data["created_by"]
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                
                if not user or user[0] != 'admin':
                    self.send_json({"error": "Access denied"}, 403)
                    return
                
                title = data["title"]
                description = data["description"]
                test_type = data["test_type"]
                questions = data["questions"]
                test_id = data.get("test_id")
                
                if test_id:
                    # Обновляем существующий тест
                    cursor.execute('''
                        UPDATE tests SET title = ?, description = ?, test_type = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND created_by = ?
                    ''', (title, description, test_type, test_id, user_id))
                    
                    # Удаляем старые вопросы
                    cursor.execute('DELETE FROM test_questions WHERE test_id = ?', (test_id,))
                else:
                    # Создаем новый тест
                    cursor.execute('''
                        INSERT INTO tests (title, description, test_type, created_by)
                        VALUES (?, ?, ?, ?)
                    ''', (title, description, test_type, user_id))
                    test_id = cursor.lastrowid
                
                # Добавляем новые вопросы
                for i, q in enumerate(questions):
                    answers_json = json.dumps(q["answers"])
                    cursor.execute('''
                        INSERT INTO test_questions (test_id, question_text, answers, correct_answer)
                        VALUES (?, ?, ?, ?)
                    ''', (test_id, q["text"], answers_json, q["correct"]))
                
                conn.commit()
                
                self.send_json({
                    "status": "success",
                    "test_id": test_id
                })
                
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        # ---- удаление теста (для админа) ----
        elif self.path == "/api/delete-test":
            required_fields = ["test_id", "user_id"]
            if not all(field in data for field in required_fields):
                self.send_json({"error": "Missing fields"}, 400)
                return
            
            test_id = data["test_id"]
            user_id = data["user_id"]
            
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                # Проверяем, что пользователь - админ
                cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                
                if not user or user[0] != 'admin':
                    self.send_json({"error": "Access denied"}, 403)
                    return
                
                cursor.execute('DELETE FROM tests WHERE id = ?', (test_id,))
                conn.commit()
                
                self.send_json({"status": "success"})
                
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        # ---- сохранение результата теста ----
        elif self.path == "/api/save-result":
            required_fields = ["user_id", "test_id", "score", "total_questions", "answers"]
            if not all(field in data for field in required_fields):
                self.send_json({"error": "Missing fields"}, 400)
                return
            
            user_id = data["user_id"]
            test_id = data["test_id"]
            score = data["score"]
            total_questions = data["total_questions"]
            answers = data["answers"]
            percentage = (score / total_questions) * 100 if total_questions > 0 else 0
            
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO test_results (user_id, test_id, score, total_questions, percentage)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, test_id, score, total_questions, percentage))
                
                result_id = cursor.lastrowid
                
                # Сохраняем ответы пользователя
                for ans in answers:
                    cursor.execute('''
                        INSERT INTO user_answers (result_id, question_id, user_answer, is_correct)
                        VALUES (?, ?, ?, ?)
                    ''', (result_id, ans["question_id"], ans["user_answer"], 1 if ans["is_correct"] else 0))
                
                conn.commit()
                
                self.send_json({"status": "saved", "result_id": result_id})
                
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                conn.close()

        else:
            self.send_json({"error": "Not found"}, 404)

if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("0.0.0.0", port), PersonalityHandler)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"

    print(f"\nСервер запущен на http://{local_ip}:{port}")
    print("Нажмите Ctrl+C для остановки\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")