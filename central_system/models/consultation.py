from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum
import re
from .base import Base

class ConsultationStatus(enum.Enum):
    """
    Consultation status enum.
    """
    PENDING = "pending"                 # Request made, awaiting faculty action
    ACCEPTED = "accepted"               # Faculty accepted, awaiting start or student confirmation if needed
    REJECTED_BY_FACULTY = "rejected_by_faculty" # Faculty actively rejected the request
    STARTED = "started"                 # Consultation is in progress
    COMPLETED = "completed"             # Consultation finished normally
    CANCELLED_BY_STUDENT = "cancelled_by_student" # Student cancelled their request
    CANCELLED_BY_FACULTY = "cancelled_by_faculty" # Faculty cancelled an accepted/started consultation
    # CANCELLED = "cancelled" # Deprecating generic cancelled in favor of specific ones
    NO_SHOW_STUDENT = "no_show_student"     # Student did not attend an accepted consultation
    NO_SHOW_FACULTY = "no_show_faculty"     # Faculty did not attend or start an accepted consultation (less likely to be set by faculty themselves)
    ERROR = "error"                     # System error or unknown state

class Consultation(Base):
    """
    Consultation model.
    Represents a consultation request between a student and faculty.
    """
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    request_message = Column(String, nullable=False)
    course_code = Column(String, nullable=True)
    status = Column(Enum(ConsultationStatus), default=ConsultationStatus.PENDING, index=True)
    requested_at = Column(DateTime, default=func.now(), index=True)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    @staticmethod
    def validate_request_message(message_value):
        if not message_value or not isinstance(message_value, str):
            return False, "Request message cannot be empty."
        if len(message_value.strip()) == 0:
            return False, "Request message cannot be only whitespace."
        if len(message_value) > 500: # Max length example
            return False, "Request message cannot exceed 500 characters."
        return True, ""

    @staticmethod
    def validate_course_code(code_value):
        if code_value is None: # Course code is nullable
            return True, ""
        if not isinstance(code_value, str):
            return False, "Course code must be a string."
        if len(code_value.strip()) == 0 and len(code_value) > 0: # Non-empty string that is all whitespace
             return False, "Course code cannot be only whitespace if provided."
        if len(code_value) > 20: # Max length example
            return False, "Course code cannot exceed 20 characters."
        if len(code_value) > 0 and not re.match(r'^[a-zA-Z0-9\s\-]+$', code_value): # Alphanumeric, space, hyphen
            return False, "Course code contains invalid characters."
        return True, ""

    @validates('request_message')
    def _validate_request_message(self, key, message_value):
        is_valid, error_msg = Consultation.validate_request_message(message_value)
        if not is_valid:
            raise ValueError(error_msg)
        return message_value

    @validates('course_code')
    def _validate_course_code(self, key, code_value):
        is_valid, error_msg = Consultation.validate_course_code(code_value)
        if not is_valid:
            raise ValueError(error_msg)
        return code_value.strip() if code_value else None # Store stripped or None

    # Relationships
    student = relationship("Student", backref="consultations")
    faculty = relationship("Faculty", backref="consultations")

    def __repr__(self):
        return f"<Consultation {self.id}>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            "id": self.id,
            "student_id": self.student_id,
            "faculty_id": self.faculty_id,
            "request_message": self.request_message,
            "course_code": self.course_code,
            "status": self.status.value,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        } 