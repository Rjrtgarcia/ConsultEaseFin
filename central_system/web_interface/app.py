"""
ConsultEase Web Interface

This module provides a web interface for the ConsultEase system, allowing users
to access the system from any device with a web browser.
"""

import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
import threading
import sys

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web_interface.log')
    ]
)
logger = logging.getLogger(__name__)

# Import models and controllers
try:
    from central_system.models import init_db
    from central_system.controllers import (
        FacultyController,
        ConsultationController
    )
    from central_system.models.faculty import Faculty
    from central_system.models.student import Student
    from central_system.models.consultation import Consultation
    logger.info("Successfully imported ConsultEase components")
except ImportError as e:
    logger.error(f"Failed to import ConsultEase components: {e}")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'consultease-web-interface')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_db()

# Initialize controllers
faculty_controller = FacultyController()
consultation_controller = ConsultationController()

# Start controllers
faculty_controller.start()

# Register for faculty status updates


@faculty_controller.register_callback
def handle_faculty_status_update(faculty):
    """
    Handle faculty status updates and broadcast to connected clients.
    """
    logger.info(
        f"Faculty status update: {faculty.name} (ID: {faculty.id}) - Status: {faculty.status}")
    socketio.emit('faculty_status_update', {
        'id': faculty.id,
        'name': faculty.name,
        'status': faculty.status
    })


@app.route('/')
def index():
    """
    Render the main page.
    """
    # Check if user is logged in
    if 'student_id' not in session:
        return redirect(url_for('login'))

    # Get student information
    student_id = session['student_id']
    student = Student.get_by_id(student_id)

    if not student:
        return redirect(url_for('login'))

    # Get all faculty
    faculties = faculty_controller.get_all_faculty()

    return render_template('index.html', student=student, faculties=faculties)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    """
    if request.method == 'POST':
        # In a real implementation, this would validate against the database
        # For now, we'll use a simple mock login
        student_id = request.form.get('student_id')

        # Get student by ID
        student = Student.get_by_id(student_id)

        if student:
            session['student_id'] = student.id
            session['student_name'] = student.name
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid student ID")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Handle user logout.
    """
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/faculty')
def get_faculty():
    """
    API endpoint to get all faculty.
    """
    faculties = faculty_controller.get_all_faculty()

    # Convert to JSON-serializable format
    faculty_list = []
    for faculty in faculties:
        faculty_list.append({
            'id': faculty.id,
            'name': faculty.name,
            'department': faculty.department,
            'status': faculty.status
        })

    return jsonify(faculty_list)


@app.route('/api/faculty/<int:faculty_id>')
def get_faculty_by_id(faculty_id):
    """
    API endpoint to get faculty by ID.
    """
    faculty = Faculty.get_by_id(faculty_id)

    if not faculty:
        return jsonify({'error': 'Faculty not found'}), 404

    return jsonify({
        'id': faculty.id,
        'name': faculty.name,
        'department': faculty.department,
        'status': faculty.status
    })


@app.route('/api/consultations', methods=['POST'])
def create_consultation():
    """
    API endpoint to create a new consultation request.
    """
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    faculty_id = data.get('faculty_id')
    message = data.get('message')
    course_code = data.get('course_code', '')

    if not faculty_id or not message:
        return jsonify({'error': 'Missing required fields'}), 400

    # Get faculty and student
    faculty = Faculty.get_by_id(faculty_id)
    student = Student.get_by_id(session['student_id'])

    if not faculty or not student:
        return jsonify({'error': 'Invalid faculty or student ID'}), 400

    # Create consultation request
    consultation = consultation_controller.create_consultation(
        student_id=student.id,
        faculty_id=faculty.id,
        message=message,
        course_code=course_code
    )

    if consultation:
        # Notify faculty desk unit via MQTT
        consultation_controller.notify_faculty_desk_unit(consultation)

        return jsonify({
            'id': consultation.id,
            'student_id': consultation.student_id,
            'faculty_id': consultation.faculty_id,
            'message': consultation.message,
            'course_code': consultation.course_code,
            'status': consultation.status,
            'created_at': consultation.created_at.isoformat()
        })
    else:
        return jsonify({'error': 'Failed to create consultation request'}), 500


@app.route('/api/consultations')
def get_consultations():
    """
    API endpoint to get consultations for the current student.
    """
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    student_id = session['student_id']
    consultations = consultation_controller.get_consultations(student_id=student_id)

    # Convert to JSON-serializable format
    consultation_list = []
    for consultation in consultations:
        consultation_list.append({
            'id': consultation.id,
            'student_id': consultation.student_id,
            'faculty_id': consultation.faculty_id,
            'faculty_name': consultation.faculty.name,
            'message': consultation.message,
            'course_code': consultation.course_code,
            'status': consultation.status,
            'created_at': consultation.created_at.isoformat()
        })

    return jsonify(consultation_list)


if __name__ == '__main__':
    # Run the Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
