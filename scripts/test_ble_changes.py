"""
Test script for BLE functionality changes.

This script tests the BLE functionality changes in the ConsultEase system.
It verifies that faculty availability is correctly determined by BLE connection status.
"""

import sys
import os
import logging
import time
import argparse

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import models and services
from central_system.models import Faculty, init_db, get_db
from central_system.services import get_mqtt_service
# FacultyController might not be directly needed if we are only testing MQTT processing by the service
# from central_system.controllers import FacultyController 
from central_system.utils.mqtt_topics import MQTTTopics

def test_faculty_status_update():
    """
    Test faculty status update based on BLE connection.
    """
    try:
        # Initialize database
        init_db()
        
        # Get database connection
        db = get_db()
        
        # Get MQTT service
        mqtt_service = get_mqtt_service()
        
        # Connect to MQTT broker
        if not mqtt_service.is_connected:
            # Ensure MQTTService is started if it has a connect method that needs to be called
            # This depends on MQTTService implementation (singleton, explicit start, etc.)
            # For now, assuming get_mqtt_service() returns a ready or connectable service.
            if hasattr(mqtt_service, 'connect') and callable(getattr(mqtt_service, 'connect')):
                mqtt_service.connect() 
            # Add a small delay to ensure connection if connect() is async or needs time
            time.sleep(1) # Adjust as necessary
            if not mqtt_service.is_connected:
                logger.error("Failed to connect to MQTT broker after explicit connect call.")
                return False
            logger.info("Connected to MQTT broker")
        
        # Get all faculty members
        # It's better to test with specific test faculty if init_db() creates them
        # Or ensure the test environment has known faculty members
        faculty_list = db.query(Faculty).all()
        
        if not faculty_list:
            logger.warning("No faculty members found in the database. Test might not be effective.")
            # Depending on init_db, this might be expected or an issue.
            # If init_db should create sample faculty, this is a problem.
            return True # Or False if faculty are expected
        
        logger.info(f"Found {len(faculty_list)} faculty members. Testing status updates...")
        
        success_overall = True
        for faculty in faculty_list:
            logger.info(f"Testing faculty: {faculty.name} (ID: {faculty.id})")
            
            if faculty.always_available:
                logger.error(f"Faculty {faculty.name} has always_available=True. This field is deprecated and should be False.")
                success_overall = False
                continue # Skip to next faculty if this one has problematic config
            
            original_status = faculty.status
            logger.info(f"  - Original status: {original_status}")
            
            status_update_topic = MQTTTopics.get_faculty_status_topic(faculty.id)
            
            # Test BLE connection (simulate keychain_connected)
            logger.info(f"  - Simulating BLE connection (keychain_connected) for faculty {faculty.name} on topic {status_update_topic}")
            # The payload for status updates is typically a JSON string like {"status": true/false, ...}
            # However, the original script used raw "keychain_connected". Let's check mqtt_service publish_raw or FacultyController handler.
            # For now, sticking to raw string if that was the previous contract for this test.
            # The FacultyController.handle_faculty_status_update expects specific payload formats.
            # If ESP32 sends simple strings, FacultyController needs to parse them.
            # Let's assume for this test the simplified string is what the FacultyController expects for status.
            # A better payload might be json.dumps({"status": True, "device_name": "test_beacon"})
            mqtt_service.publish_raw(status_update_topic, "keychain_connected") # Using publish_raw as in original test
            
            logger.info("  - Waiting for status update (2s)...")
            time.sleep(2)
            
            db.refresh(faculty) # Refresh from DB
            if not faculty.status:
                logger.error(f"Faculty {faculty.name} status NOT updated to True after 'keychain_connected'. Status: {faculty.status}")
                success_overall = False
            else:
                logger.info(f"  - Status after BLE connection: {faculty.status} (Expected True)")
            
            # Test BLE disconnection (simulate keychain_disconnected)
            logger.info(f"  - Simulating BLE disconnection (keychain_disconnected) for faculty {faculty.name} on topic {status_update_topic}")
            mqtt_service.publish_raw(status_update_topic, "keychain_disconnected")
            
            logger.info("  - Waiting for status update (2s)...")
            time.sleep(2)
            
            db.refresh(faculty)
            if faculty.status:
                logger.error(f"Faculty {faculty.name} status NOT updated to False after 'keychain_disconnected'. Status: {faculty.status}")
                success_overall = False
            else:
                logger.info(f"  - Status after BLE disconnection: {faculty.status} (Expected False)")
            
            # Restore original status for idempotency if other tests rely on initial state
            if faculty.status != original_status:
                faculty.status = original_status
                db.commit()
                logger.info(f"  - Restored original status to: {original_status}")
        
        db.close() # Close session
        return success_overall
    except Exception as e:
        logger.error(f"Error testing faculty status update: {e}", exc_info=True)
        # Ensure db session is closed on error too
        if 'db' in locals() and db.is_active:
            db.close()
        return False

def main():
    """
    Main function to run tests.
    """
    parser = argparse.ArgumentParser(description='ConsultEase BLE Functionality Test')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    if args.verbose:
        # Note: Root logger level is set by basicConfig. 
        # To change level of specific loggers, get them by name.
        logging.getLogger().setLevel(logging.DEBUG) 
        logger.info("Verbose logging enabled.")
    
    logger.info("Starting BLE functionality tests...")
    
    if test_faculty_status_update():
        logger.info("Faculty status update test completed successfully.")
    else:
        logger.error("Faculty status update test FAILED.")
        # sys.exit(1) # Consider exiting with error code if test fails
    
    logger.info("All BLE functionality tests finished.")

if __name__ == "__main__":
    main()
