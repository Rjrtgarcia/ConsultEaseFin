"""
Reset the admin password to a secure default value.
This script will find the admin user with username 'admin' and reset its password.
The password will meet all security requirements (uppercase, lowercase, digits, special chars).
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Set environment variables
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = 'consultease.db'

# Import models and controllers
from central_system.models import init_db, Admin, get_db

def reset_admin_password():
    """Reset the admin password to the default value."""
    try:
        # Initialize database if it doesn't exist
        init_db()

        # Get database connection
        db = get_db()

        # Find admin user with username 'admin'
        admin = db.query(Admin).filter(Admin.username == 'admin').first()

        if admin:
            logger.info(f"Found admin user: {admin.username} (ID: {admin.id})")

            # Reset password to a secure default: 'Admin123!'
            password_hash, salt = Admin.hash_password("Admin123!")

            # Update admin
            admin.password_hash = password_hash
            admin.salt = salt

            # Make sure admin is active
            admin.is_active = True

            # Commit changes
            db.commit()

            logger.info(f"Reset password for admin user: {admin.username}")
            logger.warning(
                "Admin password has been reset to 'Admin123!'. "
                "Please change this password after logging in!"
            )
        else:
            logger.warning("No admin user found with username 'admin'")

            # Create admin user if it doesn't exist
            logger.info("Creating new admin user with default credentials")

            # Hash password - use a secure default: 'Admin123!'
            password_hash, salt = Admin.hash_password("Admin123!")

            # Create new admin
            admin = Admin(
                username="admin",
                password_hash=password_hash,
                salt=salt,
                is_active=True
            )

            db.add(admin)
            db.commit()

            logger.info(f"Created new admin user: admin (ID: {admin.id})")
            logger.warning(
                "Created default admin user with username 'admin' and password 'Admin123!'. "
                "Please change this password after logging in!"
            )

        # Close database connection
        db.close()

        print("Admin password has been reset to 'Admin123!'")

    except Exception as e:
        logger.error(f"Error resetting admin password: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    reset_admin_password()
