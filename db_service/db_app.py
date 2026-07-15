from flask import Flask, request, jsonify
import database

app = Flask(__name__)
database.init_db()
database.init_db_extended()

@app.route('/students', methods=['GET'])
def get_students():
    return jsonify(database.get_all_students())

@app.route('/students', methods=['POST'])
def add_student():
    data = request.json
    success = database.register_student(data['id'], data['name'], data['encoding'])
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "ID collision"}), 400

@app.route('/attendance/log', methods=['POST'])
def log_attendance():
    data = request.json
    is_new = database.log_attendance(data['student_id'])
    return jsonify({"status": "success", "is_new": is_new})

@app.route('/attendance/logs', methods=['GET'])
def get_logs():
    return jsonify(database.get_attendance_logs())

@app.route('/dashboard/stats', methods=['GET'])
def get_stats():
    return jsonify(database.get_dashboard_stats())

@app.route('/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    if database.delete_student_record(student_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    # Run this service independently on Port 5002
    app.run(debug=True, port=5002)