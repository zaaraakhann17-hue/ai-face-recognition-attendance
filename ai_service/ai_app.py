from flask import Flask, request, jsonify
import cv2
import numpy as np
import face_recognition
import base64
import json
import requests # Used to communicate with the DB Microservice
import os


app = Flask(__name__)
DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://127.0.0.1:5002")

def base64_to_cv2(base64_string):
    format, imgstr = base64_string.split(';base64,')
    data = base64.b64decode(imgstr)
    np_arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

@app.route('/process/scan', methods=['POST'])
def process_scan():
    data = request.json
    image = base64_to_cv2(data['image'])
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(rgb_image)
    if not face_locations:
        return jsonify({"status": "unknown", "message": "No face detected."})
        
    unknown_encoding = face_recognition.face_encodings(rgb_image, face_locations)[0]
    
    # Microservice Communication: Fetch known data array from DB Service
    response = requests.get(f"{DB_SERVICE_URL}/students")
    known_students = response.json()
    
    if not known_students:
        return jsonify({"status": "unknown", "message": "Database records are empty."})
        
    known_encodings = [json.loads(s['face_encoding']) for s in known_students]
    matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.5)
    face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    
    if True in matches:
        best_match_idx = np.argmin(face_distances)
        student = known_students[best_match_idx]
        
        # Microservice Communication: Instruct DB Service to mark attendance log
        log_res = requests.post(f"{DB_SERVICE_URL}/attendance/log", json={"student_id": student['id']}).json()
        if log_res['is_new']:
            return jsonify({"status": "success", "message": f"Welcome {student['name']}! Logged."})
        return jsonify({"status": "success", "message": f"Hello {student['name']}, already marked today."})
        
    return jsonify({"status": "unknown", "message": "Face match not found."})

if __name__ == '__main__':
    # Run this machine learning cluster independently on Port 5001
    app.run(debug=True, port=5001)