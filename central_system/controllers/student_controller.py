import logging
from sqlalchemy.exc import IntegrityError
from ..models.student import Student
from ..models.base import get_db, close_db, db_operation_with_retry
from ..services import get_rfid_service
import re

logger = logging.getLogger(__name__)

class StudentController:
    """
    Controller for managing student data.
    """
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the StudentController."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Initialize the StudentController.
        """
        if StudentController._instance is not None:
            raise RuntimeError("StudentController is a singleton, use StudentController.instance()")
        StudentController._instance = self
        logger.info("StudentController initialized")

    @db_operation_with_retry()
    def add_student(self, db, name, student_id, email, rfid_uid=None):
        """
        Add a new student.
        Note: `db` is provided by the decorator.
        Args:
            db: SQLAlchemy session (from decorator)
            name (str): Student name
            student_id (str): Student ID
            email (str): Student email
            rfid_uid (str, optional): RFID UID

        Returns:
            Student: New student object
        """
        # Validate inputs
        if not name or not student_id or not email:
            raise ValueError("Name, student ID, and email are required")
            
        # Basic email validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email format")
            
        # Validate student ID format (assuming alphanumeric with possible dashes/dots)
        if not re.match(r"^[A-Za-z0-9.\-_]{3,20}$", student_id):
            raise ValueError("Student ID must be 3-20 alphanumeric characters (dots, dashes, underscores allowed)")
            
        # Validate name (no extremely long names, no special characters except spaces)
        if not re.match(r"^[A-Za-z0-9 ]{2,100}$", name):
            raise ValueError("Name must be 2-100 characters (letters, numbers, spaces only)")
            
        # Validate RFID UID format if provided
        if rfid_uid and not re.match(r"^[A-Fa-f0-9]{4,32}$", rfid_uid):
            raise ValueError("RFID UID must be a valid hexadecimal string (4-32 characters)")

        # Check if student_id already exists
        existing = db.query(Student).filter(Student.student_id == student_id).first()
        if existing:
            raise ValueError(f"Student with ID {student_id} already exists")

        # Check if RFID UID already exists (if provided)
        if rfid_uid:
            existing_rfid = db.query(Student).filter(Student.rfid_uid == rfid_uid).first()
            if existing_rfid:
                raise ValueError(f"RFID UID {rfid_uid} is already assigned to another student")

        # Create new student
        student = Student(
            name=name,
            student_id=student_id,
            email=email,
            rfid_uid=rfid_uid
        )

        db.add(student)
        # db.commit() # Decorator handles commit on success

        logger.info(f"Created new student: {student.name} (ID: {student.id}, Student ID: {student.student_id})")
        return student

    @db_operation_with_retry()
    def update_student(self, db, student_id: int, name: str, department: str, rfid_uid: str):
        """
        Update an existing student's information.
        Checks if the new RFID UID is already in use by another student.
        Refreshes RFID service cache on success.

        Args:
            db: The database session.
            student_id (int): ID of the student to update.
            name (str): New name of the student.
            department (str): New department of the student.
            rfid_uid (str): New RFID UID of the student.

        Returns:
            Student: The updated student object, or None if error.
            
        Raises:
            ValueError: If student not found or RFID UID conflict.
        """
        logger.info(f"Attempting to update student ID '{student_id}': Name='{name}', Department='{department}', RFID='{rfid_uid}'")
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            logger.warning(f"Failed to update student. Student with ID '{student_id}' not found.")
            raise ValueError(f"Student with ID '{student_id}' not found.")

        # Check if the new RFID UID is already used by *another* student (case-insensitive)
        if student.rfid_uid.lower() != rfid_uid.lower(): # Compare lowercased versions for change detection
            existing_rfid_student = db.query(Student).filter(Student.rfid_uid.ilike(rfid_uid), Student.id != student_id).first()
            if existing_rfid_student:
                logger.warning(f"Failed to update student ID '{student_id}'. New RFID UID '{rfid_uid}' already exists for student '{existing_rfid_student.name}'.")
                raise ValueError(f"RFID UID '{rfid_uid}' is already registered to another student.")
        
        student.name = name
        student.department = department
        student.rfid_uid = rfid_uid
        # db.commit() and db.refresh() handled by decorator
        logger.info(f"DB: Successfully updated student '{student.name}' (ID: {student.id}).")
        
        return student

    @db_operation_with_retry()
    def delete_student(self, db, student_id: int):
        """
        Delete a student from the database.
        Refreshes RFID service cache on success.

        Args:
            db: The database session.
            student_id (int): ID of the student to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        
        Raises:
            ValueError: If student not found.
        """
        logger.info(f"Attempting to delete student ID '{student_id}'")
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            logger.warning(f"Failed to delete student. Student with ID '{student_id}' not found.")
            raise ValueError(f"Student with ID '{student_id}' not found.")
        
        student_name_for_log = student.name
        db.delete(student)
        # db.commit() handled by decorator
        logger.info(f"DB: Successfully deleted student '{student_name_for_log}' (ID: {student_id}).")
        
        return True

    def get_student_by_id(self, student_id: int):
        """
        Retrieve a student by their ID.

        Args:
            student_id (int): ID of the student.

        Returns:
            Student: The student object, or None if not found.
        """
        db = get_db()
        try:
            logger.debug(f"Fetching student by ID: {student_id}")
            return db.query(Student).filter(Student.id == student_id).first()
        except Exception as e:
            logger.error(f"Error fetching student by ID '{student_id}': {e}")
            return None
        finally:
            close_db()

    def get_student_by_rfid(self, rfid_uid: str):
        """
        Retrieve a student by their RFID UID.

        Args:
            rfid_uid (str): RFID UID of the student.

        Returns:
            Student: The student object, or None if not found.
        """
        db = get_db()
        try:
            logger.debug(f"Fetching student by RFID: {rfid_uid}")
            return db.query(Student).filter(Student.rfid_uid == rfid_uid).first()
        except Exception as e:
            logger.error(f"Error fetching student by RFID '{rfid_uid}': {e}")
            return None
        finally:
            close_db()

    def get_all_students(self):
        """
        Retrieve all students from the database.

        Returns:
            list[Student]: A list of all student objects.
        """
        db = get_db()
        try:
            logger.debug("Fetching all students")
            return db.query(Student).all()
        except Exception as e:
            logger.error(f"Error fetching all students: {e}")
            return []
        finally:
            close_db()

def get_student_controller():
    """
    Factory function to get the singleton instance of StudentController.
    """
    return StudentController.instance() 