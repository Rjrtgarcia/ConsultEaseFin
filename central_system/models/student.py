from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from .base import Base
import re


class Student(Base):
    """
    Student model.
    Represents a student in the system.
    """
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    rfid_uid = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @staticmethod
    def validate_student_name(name_value):
        if not name_value or not isinstance(name_value, str):
            return False, "Name cannot be empty."
        if len(name_value.strip()) < 2:
            return False, "Name must be at least 2 characters."
        if not re.match(r'^[A-Za-z\s.\'-]+$', name_value):
            return False, "Name contains invalid characters."
        return True, ""

    @staticmethod
    def validate_department(dept_value):
        if not dept_value or not isinstance(dept_value, str):
            return False, "Department cannot be empty."
        if len(dept_value.strip()) < 2 or len(dept_value.strip()) > 100:
            return False, "Department must be between 2 and 100 characters."
        # Potentially add more specific character checks if needed
        return True, ""

    @staticmethod
    def validate_rfid_uid(rfid_value):
        if not rfid_value or not isinstance(rfid_value, str):
            return False, "RFID UID cannot be empty."
        if not re.match(r'^[a-zA-Z0-9]+$', rfid_value):  # Basic alphanumeric check
            return False, "RFID UID must be alphanumeric."
        if len(rfid_value) < 4 or len(rfid_value) > 32:  # Example length check
            return False, "RFID UID must be between 4 and 32 characters."
        return True, ""

    @validates('name')
    def _validate_name(self, key, name_value):
        is_valid, message = Student.validate_student_name(name_value)
        if not is_valid:
            raise ValueError(message)
        return name_value

    @validates('department')
    def _validate_department(self, key, dept_value):
        is_valid, message = Student.validate_department(dept_value)
        if not is_valid:
            raise ValueError(message)
        return dept_value

    @validates('rfid_uid')
    def _validate_rfid_uid(self, key, rfid_value):
        is_valid, message = Student.validate_rfid_uid(rfid_value)
        if not is_valid:
            raise ValueError(message)
        return rfid_value

    def __repr__(self):
        return f"<Student {self.name}>"

    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "rfid_uid": self.rfid_uid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
