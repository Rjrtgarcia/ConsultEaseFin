from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
import bcrypt
import os
import logging
import re
import time
from .base import Base, get_db, close_db
from ..config import get_config
import datetime

# Set up logging
logger = logging.getLogger(__name__)
config = get_config()

# Constants for password security - now from config with fallbacks
MIN_PASSWORD_LENGTH = config.get('security.min_password_length', 8)
PASSWORD_LOCKOUT_THRESHOLD = config.get('security.password_lockout_threshold', 5)
PASSWORD_LOCKOUT_DURATION = config.get('security.password_lockout_duration', 15 * 60)  # 15 minutes in seconds

class Admin(Base):
    """
    Admin model.
    Represents an administrator in the system.
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False) # Kept for SHA256 fallback, bcrypt includes its own
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Columns for DB-backed account lockout
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_failed_login_at = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Admin {self.username}>"

    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength.

        Args:
            password (str): Password to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not password or not isinstance(password, str):
            return False, "Password cannot be empty"

        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"

        # Check for complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase letters, lowercase letters, and digits"

        if not has_special:
            return False, "Password must contain at least one special character"

        # Check for common patterns - only reject if they make up most of the password
        common_patterns = ['123', 'abc', 'qwerty', 'password', 'admin']
        for pattern in common_patterns:
            # Only reject if the pattern makes up more than 50% of the password
            if pattern in password.lower() and len(pattern) > len(password) / 2:
                return False, "Password relies too heavily on common patterns that are easy to guess"

        return True, "Password meets strength requirements"

    @staticmethod
    def hash_password(password, salt=None):
        """
        Hash a password using bcrypt with improved security.

        Args:
            password (str): The password to hash
            salt (str, optional): Not used with bcrypt, kept for backward compatibility

        Returns:
            tuple: (password_hash, salt) - salt is included in the hash with bcrypt
                   but we keep a separate salt field for backward compatibility

        Raises:
            ValueError: If password doesn't meet strength requirements
        """
        # Validate password strength
        is_valid, error_message = Admin.validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Generate a salt and hash the password
            password_bytes = password.encode('utf-8')
            salt_bytes = bcrypt.gensalt(rounds=12)  # Increased from default 10
            hashed = bcrypt.hashpw(password_bytes, salt_bytes)
            password_hash = hashed.decode('utf-8')
            salt = salt_bytes.decode('utf-8')

            return password_hash, salt
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            raise ValueError(f"Error processing password: {str(e)}")

    def check_password(self, password):
        """
        Check if a password matches the stored hash using bcrypt.

        Args:
            password (str): The password to check

        Returns:
            bool: True if the password matches, False otherwise
        """
        try:
            # If the hash starts with $2b$, it's a bcrypt hash
            if self.password_hash.startswith('$2b$') or self.password_hash.startswith('$2a$'):
                password_bytes = password.encode('utf-8')
                hash_bytes = self.password_hash.encode('utf-8')
                return bcrypt.checkpw(password_bytes, hash_bytes)
            else:
                # Fallback for old-style hashes (SHA-256)
                import hashlib
                hash_obj = hashlib.sha256()
                hash_obj.update(self.salt.encode('utf-8'))
                hash_obj.update(password.encode('utf-8'))
                password_hash = hash_obj.hexdigest()
                return password_hash == self.password_hash
        except Exception as e:
            logger.error(f"Error checking password: {str(e)}")
            return False

    @classmethod
    def record_login_attempt(cls, username, ip_address, success):
        """
        Record a login attempt. Uses database for persistence.
        Assumes Admin model has: failed_login_attempts, account_locked_until
        """
        db = get_db()
        try:
            admin = db.query(cls).filter(cls.username == username).first()
            if not admin:
                logger.warning(f"Attempt to record login for non-existent admin: {username}")
                return False, 0 # Or handle as per security policy

            current_time = datetime.datetime.utcnow() # Use datetime for comparison with DB

            # Check if currently locked
            if admin.account_locked_until and admin.account_locked_until > current_time:
                remaining_lockout = (admin.account_locked_until - current_time).total_seconds()
                logger.warning(f"Login attempt for already locked account {username}. Locked for {remaining_lockout:.0f} more seconds.")
                # Do not update failed attempts if already locked and lock is still valid
                return True, remaining_lockout
            
            # Reset lock if duration has passed
            if admin.account_locked_until and admin.account_locked_until <= current_time:
                admin.failed_login_attempts = 0 # Renamed from failed_attempts_count
                admin.account_locked_until = None

            if success:
                admin.failed_login_attempts = 0 # Renamed
                admin.account_locked_until = None
                db.commit()
                logger.info(f"Successful login for admin {username}. Lockout reset.")
                return False, 0
            else: # Failed login
                admin.failed_login_attempts = (admin.failed_login_attempts or 0) + 1 # Renamed
                admin.last_failed_login_at = current_time # Use the new column
                logger.warning(f"Failed login attempt for admin {username}. Attempt #{admin.failed_login_attempts}")

                if admin.failed_login_attempts >= PASSWORD_LOCKOUT_THRESHOLD:
                    lock_duration = datetime.timedelta(seconds=PASSWORD_LOCKOUT_DURATION)
                    admin.account_locked_until = current_time + lock_duration
                    logger.warning(f"Account {username} locked due to {admin.failed_login_attempts} failed attempts. Locked until {admin.account_locked_until}.")
                
                db.commit()

                # Re-check lock status after commit
                if admin.account_locked_until and admin.account_locked_until > current_time:
                    remaining_lockout = (admin.account_locked_until - current_time).total_seconds()
                    return True, remaining_lockout
                return False, 0

        except Exception as e:
            logger.error(f"Error recording login attempt for {username}: {e}")
            if db: db.rollback()
            return False, 0 # Default to not locked on error to avoid unintended permanent lock
        finally:
            if db: close_db()

    @classmethod
    def is_account_locked(cls, username):
        """
        Check if an account is currently locked out from the database.
        Assumes Admin model has: account_locked_until
        """
        db = get_db()
        try:
            admin = db.query(cls).filter(cls.username == username).first()
            if not admin or not admin.account_locked_until:
                return False, 0

            current_time = datetime.datetime.utcnow()
            if admin.account_locked_until > current_time:
                remaining_seconds = (admin.account_locked_until - current_time).total_seconds()
                logger.info(f"Account {username} is currently locked. {remaining_seconds:.0f}s remaining.")
                return True, remaining_seconds
            else:
                # Lock has expired, reset it (optional, could be done on next login attempt)
                # For simplicity, we just report it as not locked if time has passed.
                # Consider resetting failed_attempts_count here if desired.
                # admin.account_locked_until = None
                # admin.failed_login_attempts = 0
                # db.commit() # If making changes
                return False, 0
        except Exception as e:
            logger.error(f"Error checking account lock status for {username}: {e}")
            return False, 0 # Default to not locked on error
        finally:
            if db: close_db()

    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            "id": self.id,
            "username": self.username,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }