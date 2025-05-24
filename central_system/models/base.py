from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import os
import urllib.parse
import getpass
import logging
import time
import functools

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # REMOVED
logger = logging.getLogger(__name__)

# Import configuration system
from ..config import get_config

# Get configuration
config = get_config()

# Database connection settings
DB_TYPE = config.get('database.type', 'sqlite')  # Default to SQLite for development

if DB_TYPE.lower() == 'sqlite':
    # Use SQLite for development/testing
    DB_PATH = config.get('database.path', 'consultease.db')
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    logger.info(f"Connecting to SQLite database: {DB_PATH}")
else:
    # Get current username - this will match PostgreSQL's peer authentication on Linux
    current_user = getpass.getuser()

    # PostgreSQL connection settings
    DB_USER = config.get('database.user', current_user)
    DB_PASSWORD = config.get('database.password', '')  # Empty password for peer authentication
    DB_HOST = config.get('database.host', 'localhost')
    DB_PORT = config.get('database.port', 5432)  # Default PostgreSQL port
    DB_NAME = config.get('database.name', 'consultease')

    # Create PostgreSQL connection URL
    if DB_HOST == 'localhost' and not DB_PASSWORD:
        # Use Unix socket connection for peer authentication
        DATABASE_URL = f"postgresql+psycopg2://{DB_USER}@/{DB_NAME}"
        logger.info(f"Connecting to PostgreSQL database: {DB_NAME} as {DB_USER} using peer authentication")
    else:
        # Use TCP connection with password
        encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
        DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        logger.info(f"Connecting to PostgreSQL database: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")

# Configure connection pooling options with sensible defaults
pool_size = config.get('database.pool_size', 5)
max_overflow = config.get('database.max_overflow', 10)
pool_timeout = config.get('database.pool_timeout', 30)
pool_recycle = config.get('database.pool_recycle', 1800)  # Recycle connections after 30 minutes

# Create engine with connection pooling
if DB_TYPE.lower() == 'sqlite':
    # SQLite doesn't support the same level of connection pooling
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Allow SQLite to be used across threads
        echo=True  # <<< ADD THIS FOR SQL DEBUGGING
    )
    logger.info("Created SQLite engine with thread safety enabled")
else:
    # PostgreSQL with full connection pooling
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,  # Check connection validity before using it
        echo=True  # <<< ADD THIS FOR SQL DEBUGGING (if using PostgreSQL too)
    )
    logger.info(f"Created PostgreSQL engine with connection pooling (size={pool_size}, max_overflow={max_overflow})")

# Create session factory with thread safety
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(session_factory)

# Create base class for models
Base = declarative_base()

def get_db(force_new=False):
    """
    Get database session from the connection pool.

    Args:
        force_new (bool): If True, create a new session even if one exists

    Returns:
        SQLAlchemy session: A database session from the connection pool
    """
    try:
        # Get a session from the pool
        db = SessionLocal()

        # If force_new is True, ensure we're getting fresh data
        if force_new:
            # Expire all objects in the session to force a refresh from the database
            db.expire_all()

        # Log connection acquisition for debugging
        logger.debug("Acquired database connection from pool")

        return db
    except Exception as e:
        logger.error(f"Error getting database connection: {str(e)}")
        # If we got a session but there was an error, make sure to close it
        if 'db' in locals():
            db.close()
        raise e

def close_db():
    """
    Remove the current session and return the connection to the pool.
    This should be called when the session is no longer needed.
    """
    try:
        SessionLocal.remove()
        logger.debug("Released database connection back to pool")
    except Exception as e:
        logger.error(f"Error releasing database connection: {str(e)}")

def db_operation_with_retry(max_retries=3, retry_delay=0.5):
    """
    Decorator for database operations with retry logic.

    Args:
        max_retries (int): Maximum number of retry attempts
        retry_delay (float): Initial delay between retries in seconds (will increase exponentially)

    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None

            while retries < max_retries:
                db_session = get_db()
                try:
                    # args[0] is 'self' of the instance whose method is decorated
                    # Pass self, then the db_session, then other *args and **kwargs
                    if not args:
                        # This case should ideally not happen for instance methods
                        # but as a fallback, or for static/classmethods decorated (though less common for this decorator)
                        result = func(db_session, **kwargs)
                    else:
                        result = func(args[0], db_session, *(args[1:]), **kwargs)
                    
                    # Diagnostic: Inspect session before flush
                    if hasattr(db_session, 'new'):
                        logger.debug(f"SESSION STATE BEFORE FLUSH: session.new contains: {list(db_session.new)}")
                    if hasattr(db_session, 'dirty'):
                        logger.debug(f"SESSION STATE BEFORE FLUSH: session.dirty contains: {list(db_session.dirty)}")

                    db_session.flush() 
                    logger.debug(f"ID of result after flush: {getattr(result, 'id', 'N/A') if hasattr(result, '__mapper__') else 'Not a model'}")
                    db_session.commit()
                    logger.debug(f"ID of result after commit: {getattr(result, 'id', 'N/A') if hasattr(result, '__mapper__') else 'Not a model'}")

                    # If the result is a SQLAlchemy model instance, ensure it's refreshed and attached
                    if result is not None and hasattr(result, '__mapper__'):
                        if not getattr(result, 'id', None):
                            # This is a critical failure if an ID was expected (e.g., for a new auto-incremented PK)
                            err_msg = f"CRITICAL: Instance {type(result)} (value: {str(result)}) has no ID after commit. This indicates a problem with primary key generation or its retrieval by SQLAlchemy. The object cannot be reliably refreshed or identified."
                            logger.error(err_msg)
                            # Raising an error here because returning an object without an ID when one is expected
                            # will likely lead to further errors downstream.
                            raise RuntimeError(err_msg)
                        else:
                            # ID is present. The object should be in the session and persistent.
                            # Attempt to refresh to get the most up-to-date state from the database.
                            try:
                                logger.debug(f"Object {type(result)} with ID {result.id} is present. Attempting to refresh.")
                                db_session.refresh(result)
                                logger.debug(f"Successfully refreshed {type(result)} with ID {result.id}.")
                                return result
                            except Exception as e_refresh:
                                logger.warning(f"Failed to refresh {type(result)} with ID {result.id} after commit (Error: {e_refresh}). Attempting to merge as a fallback.")
                                try:
                                    # Ensure the object is associated with the current session and load its current state.
                                    # merge() returns a new instance or the same if already in session.
                                    merged_result = db_session.merge(result, load=True)
                                    logger.info(f"Successfully merged {type(merged_result)} with ID {merged_result.id} after refresh failure.")
                                    return merged_result
                                except Exception as e_merge:
                                    logger.error(f"Failed to merge {type(result)} with ID {result.id} after refresh failure (Error: {e_merge}). Returning the instance as it was post-commit, but it may be stale or detached.")
                                    # Fallback: return the original 'result'. It has an ID, but refresh/merge failed.
                                    # This is risky as the state might not be fully consistent with the DB.
                                    return result
                    
                    return result # Return original result if not a model instance or if no specific handling applied
                except Exception as e:
                    db_session.rollback()
                    last_error = e
                    retries += 1

                    # Log the error
                    if retries < max_retries:
                        logger.warning(f"Database operation failed (attempt {retries}/{max_retries}): {e}")
                        # Exponential backoff
                        sleep_time = retry_delay * (2 ** (retries - 1))
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                finally:
                    close_db()  # Ensures SessionLocal.remove() is called

            # If we've exhausted all retries, raise the last error
            raise last_error

        return wrapper

    return decorator

def init_db():
    """
    Initialize database tables and create default data if needed.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Check if we need to create default data
    db = get_db()
    try:
        # Import models here to avoid circular imports
        from .admin import Admin
        from .faculty import Faculty
        from .student import Student

        # Check if admin table is empty
        admin_count = db.query(Admin).count()
        if admin_count == 0:
            # Create default admin if no admins exist
            logger.info("No admin users found, creating default admin.")
            # Use Admin model's hash_password to create the default admin
            # Ensure the default password meets strength requirements
            default_password = "DefaultAdminP@ss1" # Changed default password
            try:
                hashed_password, salt = Admin.hash_password(default_password)
                admin = Admin(
                    username="admin",
                    password_hash=hashed_password,
                    salt=salt, # Though bcrypt includes salt, schema might still have it
                    is_active=True,
                    failed_login_attempts=0 # Initialize lockout fields
                )
                db.add(admin)
                db.commit()
                logger.info(f"Default admin 'admin' created with a new secure password. PLEASE CHANGE IT.")
            except ValueError as e:
                logger.error(f"Error creating default admin user due to password policy: {e}")
                # If default password fails validation, this is a critical setup error.
                # Consider raising an exception or specific handling.
            except Exception as e:
                logger.error(f"Unexpected error creating default admin user: {e}")
                db.rollback() # Rollback on other errors
        else:
            logger.info(f"Found {admin_count} admin user(s). Default admin creation skipped.")

        # Check if faculty table is empty
        faculty_count = db.query(Faculty).count()
        if faculty_count == 0:
            # Create some sample faculty
            sample_faculty = [
                Faculty(
                    name="Dr. John Smith",
                    department="Computer Science",
                    email="john.smith@university.edu",
                    ble_id="11:22:33:44:55:66",
                    status=True  # Set to True to make Dr. John Smith available for testing
                ),
                Faculty(
                    name="Dr. Jane Doe",
                    department="Mathematics",
                    email="jane.doe@university.edu",
                    ble_id="AA:BB:CC:DD:EE:FF",
                    status=False
                ),
                Faculty(
                    name="Prof. Robert Chen",
                    department="Computer Science",
                    email="robert.chen@university.edu",
                    ble_id="4fafc201-1fb5-459e-8fcc-c5c9c331914b",  # Match the SERVICE_UUID in the faculty desk unit code
                    status=True,  # Set to available for testing
                    always_available=True  # This faculty member is always available (BLE always on)
                )
            ]
            db.add_all(sample_faculty)
            logger.info("Created sample faculty data")

        # Check if student table is empty
        student_count = db.query(Student).count()
        if student_count == 0:
            # Create some sample students
            sample_students = [
                Student(
                    name="Alice Johnson",
                    department="Computer Science",
                    rfid_uid="TESTCARD123"
                ),
                Student(
                    name="Bob Williams",
                    department="Mathematics",
                    rfid_uid="TESTCARD456"
                )
            ]
            db.add_all(sample_students)
            logger.info("Created sample student data")

        db.commit()
    except Exception as e:
        logger.error(f"Error creating default data: {str(e)}")
        db.rollback()
    finally:
        close_db()  # Return the connection to the pool