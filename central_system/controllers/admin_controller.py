import logging
from ..models import Admin, get_db, close_db
from ..models.base import db_operation_with_retry

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdminController:
    """
    Controller for handling admin authentication and management.
    """
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the AdminController."""
        if cls._instance is None:
            cls._instance = cls() # Use cls() to call __init__
        return cls._instance

    def __init__(self):
        """
        Initialize the admin controller.
        """
        # Ensure singleton pattern is respected. 
        # Check if _instance is already set and not self (which happens during initial cls() call by instance())
        if AdminController._instance is not None and AdminController._instance is not self:
            raise RuntimeError("AdminController is a singleton, use AdminController.instance()")
        
        self.current_admin = None
        # If this is the first time instance() is creating it, set _instance here too.
        # Though instance() method already handles setting AdminController._instance = self
        if AdminController._instance is None:
             AdminController._instance = self

    def authenticate(self, username, password):
        """
        Authenticate an admin user.
        Checks for account lockout before password verification.

        Args:
            username (str): Admin username
            password (str): Admin password

        Returns:
            Admin: Admin object if authenticated, None otherwise, or a tuple (None, message) for specific errors.
        """
        db = get_db() # Get session once for all operations in this method
        try:
            # Check if account is locked first using the actual model method
            locked, remaining_time = Admin.is_account_locked(username) # db session is handled by is_account_locked
            if locked:
                message = f"Admin account '{username}' is locked. Try again in {remaining_time:.0f} seconds."
                logger.warning(message)
                # It's good practice to not record another failed attempt if already locked.
                # The Admin.record_login_attempt method itself also has a check for this.
                return None, message # Return a message for the UI

            admin = db.query(Admin).filter(Admin.username == username, Admin.is_active == True).first()

            if not admin:
                logger.warning(f"Admin '{username}' not found or inactive.")
                # Record failed attempt for non-existent user for enumeration resistance
                # Ensure record_login_attempt can handle a db session passed to it, or uses its own get_db/close_db
                # Based on admin.py, record_login_attempt handles its own db session.
                Admin.record_login_attempt(username, 'unknown_ip', False)
                return None, "Invalid username or password."

            if admin.check_password(password):
                logger.info(f"Admin authenticated: {username}")
                self.current_admin = admin
                Admin.record_login_attempt(username, 'unknown_ip', True)
                return admin, "Authentication successful."
            else:
                logger.warning(f"Invalid password for admin: {username}")
                # Record failed attempt for existing user
                locked_after_attempt, remaining_time_after_attempt = Admin.record_login_attempt(username, 'unknown_ip', False)
                if locked_after_attempt:
                    message = f"Invalid password. Account '{username}' is now locked. Try again in {remaining_time_after_attempt:.0f} seconds."
                    return None, message
                return None, "Invalid username or password."
        except Exception as e:
            logger.error(f"Error authenticating admin '{username}': {str(e)}")
            # Avoid leaking detailed error messages to UI if not desired
            return None, "An internal error occurred during authentication."
        finally:
            if db: # Ensure db was successfully acquired before trying to close
                close_db()

    @db_operation_with_retry()
    def create_admin(self, db, username, password):
        """
        Create a new admin user.
        Note: `db` is provided by the decorator.
        Args:
            db: SQLAlchemy session (from decorator)
            username (str): Admin username
            password (str): Admin password

        Returns:
            Admin: New admin object or None if error (decorator handles raising error on persistent failure)
        """
        # Check if username already exists
        existing = db.query(Admin).filter(Admin.username == username).first()
        if existing:
            # Raising an error here will be caught by the decorator, causing rollback & retry
            # If it should not retry, a custom exception could be used and not retried by decorator config
            raise ValueError(f"Admin with username {username} already exists")

        # Hash password
        password_hash, salt = Admin.hash_password(password)

        # Create new admin
        admin = Admin(
            username=username,
            password_hash=password_hash,
            salt=salt,
            is_active=True
        )

        db.add(admin)
        # db.commit() # Decorator handles commit on success

        logger.info(f"Created new admin: {admin.username} (ID: {admin.id})")
        return admin

    def get_all_admins(self):
        """
        Get all admin users.

        Returns:
            list: List of Admin objects
        """
        db = get_db()
        try:
            admins = db.query(Admin).all()
            return admins
        except Exception as e:
            logger.error(f"Error getting admins: {str(e)}")
            return []
        finally:
            close_db()

    @db_operation_with_retry()
    def change_password(self, db, admin_id, old_password, new_password):
        """
        Change an admin user's password.
        Note: `db` is provided by the decorator.
        Args:
            db: SQLAlchemy session
            admin_id (int): Admin ID
            old_password (str): Current password
            new_password (str): New password

        Returns:
            bool: True if successful (decorator raises error on persistent failure)
        """
        admin = db.query(Admin).filter(Admin.id == admin_id).first()

        if not admin:
            raise ValueError(f"Admin not found: {admin_id}") # Let decorator handle this

        if not admin.check_password(old_password):
            logger.warning(f"Invalid old password for admin: {admin.username}")
            return False # Specific business logic failure, don't rely on retry for this

        password_hash, salt = Admin.hash_password(new_password)
        admin.password_hash = password_hash
        admin.salt = salt

        logger.info(f"Changed password for admin: {admin.username}")
        return True

    @db_operation_with_retry()
    def change_username(self, db, admin_id, password, new_username):
        """
        Change an admin user's username.
        Note: `db` is provided by the decorator.
        Args:
            db: SQLAlchemy session
            admin_id (int): Admin ID
            password (str): Current password for verification
            new_username (str): New username

        Returns:
            bool: True if successful
        """
        admin = db.query(Admin).filter(Admin.id == admin_id).first()

        if not admin:
            raise ValueError(f"Admin not found: {admin_id}")

        if not admin.check_password(password):
            logger.warning(f"Invalid password for admin: {admin.username}")
            return False

        existing = db.query(Admin).filter(Admin.username == new_username).first()
        if existing and existing.id != admin_id:
            raise ValueError(f"Admin with username {new_username} already exists")

        old_username = admin.username
        admin.username = new_username

        logger.info(f"Changed username for admin from {old_username} to {new_username}")
        return True

    @db_operation_with_retry()
    def deactivate_admin(self, db, admin_id):
        """
        Deactivate an admin user.
        Note: `db` is provided by the decorator.
        Args:
            db: SQLAlchemy session
            admin_id (int): Admin ID

        Returns:
            bool: True if successful
        """
        admin = db.query(Admin).filter(Admin.id == admin_id).first()

        if not admin:
            raise ValueError(f"Admin not found: {admin_id}")

        active_count = db.query(Admin).filter(Admin.is_active == True).count()
        if active_count <= 1 and admin.is_active:
            # This is a business rule; should not retry if this condition is met.
            # Raise a specific error or return False directly.
            logger.error(f"Cannot deactivate the last active admin: {admin.username}")
            return False 

        admin.is_active = False
        logger.info(f"Deactivated admin: {admin.username}")
        return True

    @db_operation_with_retry()
    def activate_admin(self, db, admin_id):
        """
        Activate an admin user.
        Note: `db` is provided by the decorator.
        Args:
            db: SQLAlchemy session
            admin_id (int): Admin ID

        Returns:
            bool: True if successful
        """
        admin = db.query(Admin).filter(Admin.id == admin_id).first()

        if not admin:
            raise ValueError(f"Admin not found: {admin_id}")

        admin.is_active = True
        logger.info(f"Activated admin: {admin.username}")
        return True

    def is_authenticated(self):
        """
        Check if an admin is currently authenticated.

        Returns:
            bool: True if authenticated, False otherwise
        """
        return self.current_admin is not None

    def logout(self):
        """
        Log out the current admin.
        """
        self.current_admin = None
        logger.info("Admin logged out")

    def ensure_default_admin(self):
        """
        Ensure that at least one admin user exists in the system.
        Relies on init_db() in models.base for initial default admin creation.
        This method primarily serves as a double-check.
        """
        db = get_db()
        try:
            admin_count = db.query(Admin).count()
            if admin_count == 0:
                logger.warning(
                    "No admin users found by AdminController.ensure_default_admin. "
                    "This is unexpected as init_db() should have created one. "
                    "Refer to init_db in models/base.py for default admin credentials."
                )
                # Optionally, one could attempt to create a *different* emergency admin here,
                # but init_db is the primary place for the first default admin.
                return False # Indicates no admin was found by this check
            else:
                logger.info(f"Admin user(s) exist (Count: {admin_count}). Checked by ensure_default_admin.")
                return True
        except Exception as e:
            logger.error(f"Error in ensure_default_admin: {str(e)}")
            return False
        finally:
            close_db()