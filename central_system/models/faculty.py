from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from .base import Base
import os
import re
import logging

logger = logging.getLogger(__name__)


class Faculty(Base):
    """
    Faculty model.
    Represents a faculty member in the system.
    """
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    ble_id = Column(String, unique=True, index=True)
    image_path = Column(String, nullable=True)  # Path to faculty image
    is_available = Column(Boolean, default=False, index=True)  # False = Unavailable, True = Available
    # If True, faculty is always shown as available
    always_available = Column(Boolean, default=False)
    # New field to track grace period status
    in_grace_period = Column(Boolean, default=False)
    # Remaining time in grace period in milliseconds
    grace_period_remaining = Column(Integer, default=0)
    # Last detected BLE presence time
    last_seen = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @validates('name')
    def _validate_name(self, key, name_value):
        if not Faculty.validate_name(name_value):
            raise ValueError(f"Invalid faculty name: {name_value}")
        return name_value

    @validates('email')
    def _validate_email(self, key, email_value):
        if not Faculty.validate_email(email_value):
            raise ValueError(f"Invalid email format: {email_value}")
        return email_value

    @validates('ble_id')
    def _validate_ble_id(self, key, ble_id_value):
        # Allow ble_id to be None or empty string initially, validation applies if a value is set.
        if ble_id_value and not Faculty.validate_ble_id(ble_id_value):
            raise ValueError(f"Invalid BLE ID format: {ble_id_value}")
        return ble_id_value

    def __repr__(self):
        return f"<Faculty {self.name}>"

    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "email": self.email,
            "ble_id": self.ble_id,
            "image_path": self.image_path,
            "status": self.is_available,
            "always_available": self.always_available,
            "in_grace_period": self.in_grace_period,
            "grace_period_remaining": self.grace_period_remaining,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def get_image_path(self):
        """
        Get the full path to the faculty image.
        If no image is set, returns None.
        """
        if not self.image_path:
            return None

        # Check if the path is absolute
        if os.path.isabs(self.image_path):
            return self.image_path

        # Otherwise, assume it's relative to the images directory
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        images_dir = os.path.join(base_dir, 'images', 'faculty')

        # Create the directory if it doesn't exist
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)

        return os.path.join(images_dir, self.image_path)

    def update_grace_period_status(self, in_grace_period, remaining_ms=0):
        """
        Update the faculty's grace period status.
        
        Args:
            in_grace_period (bool): Whether the faculty is in grace period
            remaining_ms (int): Remaining time in milliseconds if in grace period
        """
        self.in_grace_period = in_grace_period
        
        if in_grace_period:
            self.grace_period_remaining = remaining_ms
            # When in grace period, faculty is still considered available
            self.is_available = True
            logger.info(f"Faculty ID {self.id} ({self.name}) entered grace period: {remaining_ms}ms remaining")
        else:
            self.grace_period_remaining = 0
            logger.info(f"Faculty ID {self.id} ({self.name}) exited grace period")

    @staticmethod
    def validate_name(name):
        """
        Validate faculty name.

        Args:
            name (str): Faculty name to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not name or not isinstance(name, str):
            return False

        # Name should be at least 2 characters and contain only letters, spaces, dots, and hyphens
        if len(name.strip()) < 2:
            return False

        # Check for valid characters (letters, spaces, dots, hyphens, and apostrophes)
        pattern = r'^[A-Za-z\s.\'-]+$'
        return bool(re.match(pattern, name))

    @staticmethod
    def validate_email(email):
        """
        Validate email format.

        Args:
            email (str): Email to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False

        # Basic email validation pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_ble_id(ble_id):
        """
        Validate BLE ID format.

        Args:
            ble_id (str): BLE ID to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not ble_id or not isinstance(ble_id, str):
            return False

        # Check for UUID format
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        # Check for MAC address format
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        # Check for iBeacon format (UUID-Major-Minor)
        ibeacon_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}-\d+-\d+$'

        return bool(re.match(uuid_pattern, ble_id) or re.match(mac_pattern, ble_id) or re.match(ibeacon_pattern, ble_id))
