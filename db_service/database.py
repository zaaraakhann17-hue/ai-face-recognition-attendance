import os
import sqlite3
import json
import hashlib

# 👇 FIX 1: Explicitly establish an absolute path for the database file inside your workspace folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'attendance.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema_path = os.path.join(BASE_DIR, 'schema.sql')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Open using our absolute path variable
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())
        
    conn.commit()
    conn.close()
    
    # 👇 FIX 2: Call the admin seeding logic automatically on initialization!
    init_db_extended()

def init_db_extended():
    """Ensures the admin table exists and seeds a default teacher account."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        default_password = "admin123"
        # Using a secure SHA-256 hash match to line up with our updated login router!
        hashed = hashlib.sha256(default_password.encode()).hexdigest()
        cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ("admin", hashed))
        conn.commit()
    conn.close()

def register_student(student_id, name, face_encoding_list):
    conn = get_db()
    encoding_str = json.dumps(face_encoding_list)
    try:
        conn.execute(
            "INSERT INTO students (id, name, face_encoding) VALUES (?, ?, ?)",
            (student_id, name, encoding_str)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def log_attendance(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM attendance WHERE student_id = ? AND date(timestamp) = date('now')",
        (student_id,)
    )
    if cursor.fetchone() is None:
        conn.execute("INSERT INTO attendance (student_id) VALUES (?)", (student_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_all_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, face_encoding FROM students")
    students = cursor.fetchall()
    conn.close()
    return students

def get_attendance_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.timestamp, s.id, s.name 
        FROM attendance a 
        JOIN students s ON a.student_id = s.id 
        ORDER BY a.timestamp DESC
    """)
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date(timestamp) = date('now')")
    present_today = cursor.fetchone()[0]
    
    absent_today = total_students - present_today
    
    conn.close()
    return {
        "total": total_students,
        "present": present_today,
        "absent": absent_today
    }   