import logging
from sqlalchemy.exc import IntegrityError
from ..models.student import Student
from ..models.base import get_db, close_db, db_operation_with_retry
from ..services import get_rfid_service

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
    def add_student(self, db, name: str, department: str, rfid_uid: str):
        """
        Add a new student to the database.
        Checks for existing RFID UID.
        Refreshes RFID service cache on success.

        Args:
            db: The database session.
            name (str): Name of the student.
            department (str): Department of the student.
            rfid_uid (str): RFID UID of the student.

        Returns:
            Student: The newly created student object, or None if error.
        
        Raises:
            ValueError: If RFID UID already exists.
        """
        logger.info(f"Attempting to add student: Name='{name}', Department='{department}', RFID='{rfid_uid}'")
        # Case-insensitive check for existing RFID UID
        existing_student = db.query(Student).filter(Student.rfid_uid.ilike(rfid_uid)).first()
        if existing_student:
            logger.warning(f"Failed to add student. RFID UID '{rfid_uid}' already exists for student '{existing_student.name}'.")
            raise ValueError(f"RFID UID '{rfid_uid}' already exists.")

        new_student = Student(name=name, department=department, rfid_uid=rfid_uid)
        db.add(new_student)
        # db.commit() and db.refresh() handled by decorator
        logger.info(f"DB: Successfully added student '{new_student.name}' with ID '{new_student.id}' and RFID '{new_student.rfid_uid}'.")
        
        # It's crucial to refresh the RFID service cache after adding/updating/deleting students
        rfid_service = get_rfid_service()
        rfid_service.refresh_student_data()
        logger.info("RFID service student cache refreshed after adding student.")
        
        return new_student

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

        rfid_service = get_rfid_service()
        rfid_service.refresh_student_data()
        logger.info("RFID service student cache refreshed after updating student.")
        
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
        
        rfid_service = get_rfid_service()
        rfid_service.refresh_student_data()
        logger.info("RFID service student cache refreshed after deleting student.")
        
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