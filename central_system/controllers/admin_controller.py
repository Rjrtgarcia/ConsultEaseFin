import logging
import shutil
import subprocess
import os
import json  # Added for saving settings
from ..models.admin import Admin
from ..models.base import get_db, close_db, db_operation_with_retry
from ..config import get_config  # Import get_config
import datetime

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
            cls._instance = cls()  # Use cls() to call __init__
        return cls._instance

    def __init__(self):
        """
        Initialize the admin controller.
        """
        # Ensure singleton pattern is respected.
        # Check if _instance is already set and not self (which happens during
        # initial cls() call by instance())
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

        Args:
            username (str): Admin username
            password (str): Admin password

        Returns:
            Admin: Admin object if authentication is successful, None otherwise
        """
        if not username or not password:
            logger.error("Authentication failed: Missing username or password")
            return None

        db = get_db()
        try:
            # Get admin by username
            admin = db.query(Admin).filter(Admin.username == username).first()

            if not admin:
                logger.warning(f"Authentication failed: Admin not found for username '{username}'")
                return None

            # Check if account is locked
            if admin.is_locked():
                remaining_time = admin.get_lockout_remaining_time()
                logger.warning(f"Authentication attempt for locked account '{username}'. " +
                               f"Account is locked for another {remaining_time} seconds.")
                return None

            # Verify password
            if self._verify_password(admin, password):
                # Reset failed login attempts on successful login
                admin.failed_login_attempts = 0
                admin.account_locked_until = None
                db.commit()
                logger.info(f"Admin authenticated: {username}")
                return admin
            else:
                # Increment failed login attempts
                admin.failed_login_attempts += 1

                # Check if we should lock the account
                max_attempts = get_config().get('security.max_failed_attempts', 5)
                if admin.failed_login_attempts >= max_attempts:
                    # Lock account for increasing periods based on number of failures beyond
                    # the threshold
                    # Exponential backoff, max 60 minutes
                    lockout_minutes = min(2 ** (admin.failed_login_attempts - max_attempts), 60)
                    admin.account_locked_until = datetime.datetime.now() + datetime.timedelta(minutes=lockout_minutes)
                    logger.warning(
                        f"Account '{username}' locked for {lockout_minutes} minutes after {admin.failed_login_attempts} failed attempts")

                db.commit()
                logger.warning(f"Authentication failed: Invalid password for username '{username}'. " +
                               f"Failed attempts: {admin.failed_login_attempts}")
                return None
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return None
        finally:
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
        # Validate username
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")

        # Validate password strength
        config = get_config()
        min_length = config.get('security.min_password_length', 8)
        if len(password) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters")

        # Check for password complexity
        if not any(c.isupper() for c in password) or \
           not any(c.islower() for c in password) or \
           not any(c.isdigit() for c in password):
            raise ValueError("Password must contain uppercase, lowercase and numeric characters")

        # Check if username already exists
        existing = db.query(Admin).filter(Admin.username == username).first()
        if existing:
            # Raising an error here will be caught by the decorator, causing rollback & retry
            # If it should not retry, a custom exception could be used and not retried
            # by decorator config
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
            list: List of Admin objects with selected fields
        """
        db = get_db()
        try:
            # Only fetch necessary fields instead of entire objects
            admins = db.query(
                Admin.id,
                Admin.username,
                Admin.is_active,
                Admin.created_at,
                Admin.updated_at,
                Admin.failed_login_attempts,
                Admin.account_locked_until
            ).all()

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
            raise ValueError(f"Admin not found: {admin_id}")  # Let decorator handle this

        if not admin.check_password(old_password):
            logger.warning(f"Invalid old password for admin: {admin.username}")
            return False  # Specific business logic failure, don't rely on retry for this

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
        Ensure a default admin user exists.
        """
        db = get_db()
        try:
            default_username = "admin"
            # Check if admin user exists
            admin = db.query(Admin).filter(Admin.username == default_username).first()
            if not admin:
                logger.info(f"Default admin user '{default_username}' not found. Creating...")
                # Use create_admin, but it requires a password and handles its own db session.
                # Temporarily create directly here to avoid issues with decorator in this context.
                # Or, make ensure_default_admin call a modified create_admin that can take a session.
                # For now, direct creation:
                config = get_config()
                password = config.get(
                    'security.default_admin_password',
                    os.environ.get('DEFAULT_ADMIN_PASSWORD'))
                if not password:
                    password = "DefaultAdminP@ss1"  # Fallback only if not in config or env var
                password_hash, salt = Admin.hash_password(password)
                default_admin = Admin(
                    username=default_username,
                    password_hash=password_hash,
                    salt=salt,
                    is_active=True
                )
                db.add(default_admin)
                db.commit()
                logger.info(f"Default admin user '{default_admin.username}' created.")
            else:
                logger.info(f"Default admin user '{admin.username}' already exists.")
        except Exception as e:
            logger.error(f"Error ensuring default admin: {str(e)}")
            db.rollback()  # Rollback on error
        finally:
            close_db()

    def backup_database(self, backup_file_path: str) -> tuple[bool, str]:
        """
        Back up the application database.

        Args:
            backup_file_path (str): The full path where the backup file should be saved.

        Returns:
            tuple[bool, str]: (True, "Success message") or (False, "Error message")
        """
        config = get_config()
        db_type = config.get('database.type', 'sqlite')
        # Used for SQLite filename & PG DB name
        db_name = config.get('database.db_name', 'consultease.db')

        logger.info(f"Starting database backup. Type: {db_type}, Backup Path: {backup_file_path}")

        try:
            # Ensure backup directory exists
            backup_dir = os.path.dirname(backup_file_path)
            if backup_dir:  # Only create if backup_dir is not empty (i.e. not root)
                os.makedirs(backup_dir, exist_ok=True)
                logger.info(f"Ensured backup directory exists: {backup_dir}")

            if db_type == 'sqlite':
                # Usually db_name for SQLite if path is not set
                db_path = config.get('database.path', db_name)
                if not os.path.isabs(db_path):
                    # Assuming it's relative to a project root or a known location.
                    # For simplicity, let's assume it's in the main project directory if not absolute.
                    # This might need adjustment based on actual project structure.
                    # For now, let's try to construct a path assuming it's in CWD if relative.
                    # A better approach would be to have a configured base path for data.
                    project_root = config.get(
                        'system.project_root',
                        os.getcwd())  # Example: get from config
                    db_path = os.path.join(project_root, db_path)

                if not os.path.exists(db_path):
                    msg = f"SQLite database file not found at {db_path}"
                    logger.error(msg)
                    return False, msg

                shutil.copy2(db_path, backup_file_path)
                logger.info(f"SQLite database backed up successfully to {backup_file_path}")
                return True, f"SQLite database backed up successfully to {os.path.basename(backup_file_path)}."

            elif db_type == 'postgresql':
                db_user = config.get('database.user')
                db_password = config.get('database.password')
                db_host = config.get('database.host')
                # Ensure port is a string for pg_dump
                db_port = str(config.get('database.port', 5432))
                pg_dump_path = config.get(
                    'database.pg_dump_path',
                    'pg_dump')  # Allow configuring pg_dump path

                if not all([db_user, db_password, db_host, db_port, db_name]):
                    msg = "PostgreSQL connection details missing in configuration for backup."
                    logger.error(msg)
                    return False, msg

                # Set PGPASSWORD environment variable for pg_dump
                env = os.environ.copy()
                env['PGPASSWORD'] = db_password

                # Construct pg_dump command
                # Use --format=custom for a compressed, portable backup
                # Use --no-password to prevent pg_dump from prompting if PGPASSWORD isn't
                # picked up (should not happen)
                command = [
                    pg_dump_path,
                    '--host=' + db_host,
                    '--port=' + db_port,
                    '--username=' + db_user,
                    '--dbname=' + db_name,
                    '--format=custom',  # Creates a .dump file usually, or .backup if preferred by path
                    '--file=' + backup_file_path,
                    '--no-password'
                ]

                logger.info(f"Executing pg_dump command: {' '.join(command)}")
                process = subprocess.Popen(
                    command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    logger.info(f"PostgreSQL database backed up successfully to {backup_file_path}")
                    return True, f"PostgreSQL database backed up successfully to {os.path.basename(backup_file_path)}."
                else:
                    error_message = stderr.decode().strip()
                    msg = f"PostgreSQL backup failed. Return code: {process.returncode}. Error: {error_message}"
                    logger.error(msg)
                    # Attempt to delete partial backup file if it exists
                    if os.path.exists(backup_file_path):
                        try:
                            os.remove(backup_file_path)
                            logger.info(f"Deleted partial backup file: {backup_file_path}")
                        except Exception as e_del:
                            logger.error(
                                f"Failed to delete partial backup file {backup_file_path}: {e_del}")
                    return False, f"PostgreSQL backup failed: {error_message}"
            else:
                msg = f"Unsupported database type for backup: {db_type}"
                logger.error(msg)
                return False, msg
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during database backup: {str(e)}",
                exc_info=True)
            return False, f"An unexpected error occurred: {str(e)}"

    def restore_database(self, restore_file_path: str) -> tuple[bool, str]:
        """
        Restore the application database from a backup file.
        WARNING: This is a destructive operation and will overwrite the current database.

        Args:
            restore_file_path (str): The full path to the backup file.

        Returns:
            tuple[bool, str]: (True, "Success message") or (False, "Error message")
        """
        config = get_config()
        db_type = config.get('database.type', 'sqlite')
        # Used for SQLite filename & PG DB name
        db_name = config.get('database.db_name', 'consultease.db')

        logger.info(
            f"Starting database restore. Type: {db_type}, Restore From: {restore_file_path}")

        if not os.path.exists(restore_file_path):
            msg = f"Restore failed: Backup file not found at {restore_file_path}"
            logger.error(msg)
            return False, msg

        try:
            # It might be prudent to stop services that use the DB or close active connections before restore.
            # For now, we proceed directly, but this is a consideration for robustness.
            # logger.info("Attempting to close active database connections before restore...")
            # close_db() # Close any globally managed session, if applicable and safe.
            # Or, more advanced: notify other parts of the app to release DB resources.

            if db_type == 'sqlite':
                db_path = config.get('database.path', db_name)
                if not os.path.isabs(db_path):
                    project_root = config.get('system.project_root', os.getcwd())
                    db_path = os.path.join(project_root, db_path)

                # Ensure the directory for the database file exists
                db_dir = os.path.dirname(db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)

                # For SQLite, restore is typically replacing the file.
                # Ensure no active connections are holding onto the old file if possible.
                # (This is hard to manage perfectly without app restart or dedicated offline mode for restore)
                shutil.copy2(restore_file_path, db_path)
                logger.info(
                    f"SQLite database restored successfully from {restore_file_path} to {db_path}")
                # Application might need a restart for changes to take full effect with
                # SQLite file replacement.
                return True, f"SQLite database restored from {os.path.basename(restore_file_path)}.\nApplication may need a restart."

            elif db_type == 'postgresql':
                db_user = config.get('database.user')
                db_password = config.get('database.password')
                db_host = config.get('database.host')
                db_port = str(config.get('database.port', 5432))
                pg_restore_path = config.get('database.pg_restore_path', 'pg_restore')

                if not all([db_user, db_password, db_host, db_port, db_name]):
                    msg = "PostgreSQL connection details missing in configuration for restore."
                    logger.error(msg)
                    return False, msg

                env = os.environ.copy()
                env['PGPASSWORD'] = db_password

                # For pg_restore, typically you drop and recreate the database, or restore into a clean one.
                # The --clean option with pg_restore handles dropping objects before recreating them.
                # The --create option would try to create the database itself (requires permissions).
                # Using --dbname with --clean is common for restoring into an existing
                # (but to-be-cleaned) DB.
                command = [
                    pg_restore_path,
                    '--host=' + db_host,
                    '--port=' + db_port,
                    '--username=' + db_user,
                    '--dbname=' + db_name,  # Target database to restore into
                    '--clean',             # Drop database objects before recreating
                    '--if-exists',         # Add if-exists clauses to drop commands
                    # '--create',            # Option to create the database first (careful with permissions)
                    '--no-password',
                    restore_file_path      # The backup file to restore from
                ]

                logger.info(f"Executing pg_restore command: {' '.join(command)}")
                process = subprocess.Popen(
                    command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    logger.info(
                        f"PostgreSQL database restored successfully from {restore_file_path}")
                    return True, f"PostgreSQL database restored from {os.path.basename(restore_file_path)}."
                else:
                    error_message = stderr.decode().strip()
                    msg = f"PostgreSQL restore failed. Return code: {process.returncode}. Error: {error_message}"
                    logger.error(msg)
                    return False, f"PostgreSQL restore failed: {error_message}"
            else:
                msg = f"Unsupported database type for restore: {db_type}"
                logger.error(msg)
                return False, msg
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during database restore: {str(e)}",
                exc_info=True)
            return False, f"An unexpected error occurred: {str(e)}"

    def save_system_settings(self, settings_to_update: dict) -> tuple[bool, str]:
        """
        Save system settings to the configuration file (config.json).

        Args:
            settings_to_update (dict): A dictionary where keys are dot-separated paths
                                       (e.g., 'ui.theme', 'logging.level') and values are the new settings.

        Returns:
            tuple[bool, str]: (True, "Success message") or (False, "Error message")
        """
        logger.info(f"Attempting to save system settings: {settings_to_update}")
        config_manager = get_config()  # Use the existing global config manager/object
        config_file_path = config_manager.config_file_path  # Assuming this attribute exists or a getter

        if not config_file_path or not os.path.exists(config_file_path):
            # Fallback to trying to determine it if not directly available from config object
            # This logic should ideally be robustly part of the config module itself.
            # For now, assuming it might be found relative to current execution or a known path.
            # A common pattern is config.json in the project root or a 'config' subdir.
            # Let's assume the config module itself knows its source file path.
            # If config_manager.config_file_path isn't reliable, this part needs hardening.
            # This is a placeholder for finding the config.json if not directly
            # exposed by get_config()
            potential_paths = ['config.json', 'central_system/config.json']
            found_path = None
            for p_path in potential_paths:
                if os.path.exists(p_path):
                    found_path = p_path
                    break
            if not found_path:
                msg = "Configuration file (config.json) path could not be determined or file does not exist."
                logger.error(msg)
                return False, msg
            config_file_path = found_path
            logger.warning(
                f"Config file path was not directly available, inferred as: {config_file_path}")

        try:
            # Read the existing config.json content
            with open(config_file_path, 'r') as f:
                current_config_json = json.load(f)
            logger.debug(f"Successfully read current config from {config_file_path}")

            # Update the configuration dictionary
            updated_config_json = current_config_json.copy()  # Work on a copy
            for key_path, value in settings_to_update.items():
                keys = key_path.split('.')
                d = updated_config_json
                for i, key_part in enumerate(keys[:-1]):
                    d = d.setdefault(key_part, {})
                    if not isinstance(d, dict):  # If a non-dict is found where a dict is expected
                        msg = f"Error updating config: Key '{key_part}' in path '{key_path}' is not a dictionary."
                        logger.error(msg)
                        return False, msg
                d[keys[-1]] = value
            logger.debug(f"Configuration dictionary updated in memory: {updated_config_json}")

            # Write the updated configuration back to config.json
            with open(config_file_path, 'w') as f:
                json.dump(updated_config_json, f, indent=4)
            logger.info(f"Successfully saved updated settings to {config_file_path}")

            # IMPORTANT: The application's in-memory config (from get_config()) is NOT automatically updated yet.
            # The config module would need a method to reload itself, or the app needs a restart.
            # For now, we'll return a message indicating a restart might be needed.

            # Optionally, try to trigger a live reload if the config module supports it.
            # if hasattr(config_manager, 'reload_config') and callable(config_manager.reload_config):
            #     config_manager.reload_config()
            #     logger.info("Attempted to reload configuration in memory.")
            # else:
            #     logger.warning("Config module does not support live reload. Restart may be needed.")

            return True, "Settings saved successfully. Application may need a restart for all changes to take effect."

        except FileNotFoundError:
            msg = f"Configuration file ({config_file_path}) not found during save attempt."
            logger.error(msg)
            return False, msg
        except json.JSONDecodeError as e:
            msg = f"Error decoding JSON from configuration file ({config_file_path}): {str(e)}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while saving system settings: {str(e)}",
                exc_info=True)
            return False, f"An unexpected error occurred: {str(e)}"

    # Add other controller methods here if needed
