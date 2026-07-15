from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, session
import base64
import cv2
import numpy as np
import face_recognition
import json
import db_service.database as database
import csv
from io import StringIO
import sqlite3
import os
import hashlib  # Used for secure teacher credential verification

app = Flask(__name__)
# Set a secret key to sign and secure session cookies for the admin panel
app.secret_key = 'super_secret_teacher_session_encryption_key'

import mimetypes
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')

# Initialize database schema tables and seed admin account on boot
database.init_db()

def base64_to_cv2(base64_string):
    """Decodes browser base64 canvas images directly into an OpenCV image array."""
    format, imgstr = base64_string.split(';base64,')
    ext = format.split('/')[-1]
    data = base64.b64decode(imgstr)
    np_arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

# --- Authentication Helper ---
def is_logged_in():
    return 'admin_user' in session

# --- Public Facing Route ---
@app.route('/')
def index():
    # Anyone can access the root domain to stand in front of the scanner camera viewport
    return render_template('index.html')

# --- Gatekeeper Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hash the incoming password string using SHA-256 to match the database state
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        
        # Directly target the SQLite database instance managed by the db_service
        db_path = os.path.join(os.path.dirname(__file__), 'db_service', 'attendance.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        admin = cursor.execute(
            "SELECT * FROM admins WHERE username = ? AND password_hash = ?", 
            (username, hashed_input)
        ).fetchone()
        conn.close()
        
        if admin:
            session['admin_user'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid Admin/Teacher Credentials. Access Denied.", 401
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_user', None)
    return redirect(url_for('index'))

# --- Protected Admin Operations Panel ---
@app.route('/admin_dashboard')
def admin_dashboard():
    # Strict Guardrail: Redirect unauthenticated students back to the login gateway
    if not is_logged_in():
        return redirect(url_for('login'))
        
    logs = database.get_attendance_logs()
    stats = database.get_dashboard_stats() 
    return render_template('admin_dashboard.html', logs=logs, stats=stats) 

@app.route('/register_page')
def register_page():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    if not is_logged_in():
        return "Unauthorized action protocol.", 403

    # Read binary multiform data fields matching the 'name' tags in HTML
    student_id = request.form.get('roll_no')
    name = request.form.get('name')
    
    if 'file' not in request.files:
        return "Registration Error: No file block passed.", 400
        
    file = request.files['file']
    if file.filename == '' or not student_id or not name:
        return "Registration Error: Missing input entries.", 400

    try:
        # 1. Parse image payload into an OpenCV matrix array
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 2. Assert face presence limits
        face_locations = face_recognition.face_locations(rgb_image)
        if len(face_locations) != 1:
            return "Registration Error: Please guarantee exactly one face is clearly visible in the image.", 400

        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        new_encoding = face_encodings[0]

        # 🔍 3. STRICT ANTI-DUPLICATE INTERCEPTION ENGINE
        known_students = database.get_all_students()
        if known_students:
            known_encodings = [json.loads(s['face_encoding']) for s in known_students]
            
            # Condition A: Biometric Conflict Checking (Duplicate Facial Structs)
            face_distances = face_recognition.face_distance(known_encodings, new_encoding)
            if len(face_distances) > 0 and np.min(face_distances) < 0.45:
                matched_idx = np.argmin(face_distances)
                existing_student = known_students[matched_idx]
                return f"Biometric Conflict: This profile matches an existing registered face ({existing_student['name']} - ID: {existing_student['id']}).", 400

            # Condition B: Duplicate Name / ID Explicit Validation Loop
            for student in known_students:
                if student['id'].lower() == student_id.lower():
                    return "Database Conflict: This Unique ID / Roll Number is already assigned.", 400
                if student['name'].lower() == name.lower():
                    return "Database Conflict: A student with this exact name has already been registered.", 400

        # 4. Commit validation clearance to the database
        success = database.register_student(student_id, name, new_encoding.tolist())
        if success:
            return redirect(url_for('admin_dashboard'))
        else:
            return "Registration Error: System integrity error writing to database.", 400

    except Exception as e:
        return f"System exception executing process: {str(e)}", 500

# --- Live Scanner API Channel ---
@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.json
    image_data = data.get('image')

    if not image_data:
        return jsonify({"status": "error", "message": "No image frame received."}), 400

    image = base64_to_cv2(image_data)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_image)
    if len(face_locations) == 0:
        return jsonify({"status": "unknown", "message": "No face detected in camera viewport."})

    unknown_encodings = face_recognition.face_encodings(rgb_image, face_locations)
    known_students = database.get_all_students()
    
    if not known_students:
        return jsonify({"status": "unknown", "message": "No registered records found in system database."})

    known_encodings = [json.loads(s['face_encoding']) for s in known_students]
    verified_names = []
    already_logged_names = []
    
    for unknown_encoding in unknown_encodings:
        matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.5)
        face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
        
        if True in matches:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                matched_student = known_students[best_match_index]
                student_id = matched_student['id']
                name = matched_student['name']
                
                is_new = database.log_attendance(student_id)
                if is_new:
                    verified_names.append(name)
                else:
                    already_logged_names.append(name)

    if not verified_names and not already_logged_names:
        return jsonify({"status": "unknown", "message": "No matching faces found in database records."})
        
    messages = []
    if verified_names:
        messages.append(f"Logged: {', '.join(verified_names)}")
    if already_logged_names:
        messages.append(f"Already marked: {', '.join(already_logged_names)}")
        
    return jsonify({
        "status": "success", 
        "message": " | ".join(messages)
    })

@app.route('/api/export-attendance')
def export_attendance():
    if not is_logged_in():
        return "Unauthorized operations.", 403
        
    logs = database.get_attendance_logs()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Timestamp', 'Student ID', 'Student Name'])
    
    for log in logs:
        cw.writerow([log['timestamp'], log['id'], log['name']])
        
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    return output

@app.route('/student_summary', methods=['GET', 'POST'])
def student_summary():
    student_stats = None
    error = None
    
    if request.method == 'POST':
        student_id = request.form.get('roll_no')
        
        # Connect to DB to fetch this specific student's info and total presence count
        db_path = os.path.join(os.path.dirname(__file__), 'db_service', 'attendance.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        student = cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        
        if student:
            # Count how many total days this student has been marked present
            presence_count = cursor.execute(
                "SELECT COUNT(*) FROM attendance WHERE student_id = ?", (student_id,)
            ).fetchone()[0]
            
            student_stats = {
                "name": student['name'],
                "id": student['id'],
                "days_present": presence_count
            }
        else:
            error = "No student record found with that Roll Number."
            
        conn.close()
        
    return render_template('student_summary.html', stats=student_stats, error=error)



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3000)
