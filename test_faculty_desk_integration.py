#!/usr/bin/env python3
"""
ConsultEase - Faculty Desk Unit Integration Test

This script tests the communication between the central system and faculty desk unit
by simulating faculty presence status updates and consultation requests.
"""

import sys
import json
import time
import paho.mqtt.client as mqtt
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_BROKER = "localhost"
DEFAULT_PORT = 1883
DEFAULT_USERNAME = "faculty_desk"
DEFAULT_PASSWORD = "desk_password"
DEFAULT_FACULTY_ID = 1

# Topics
BASE_TOPIC = "consultease"
FACULTY_STATUS_TOPIC = lambda id: f"{BASE_TOPIC}/faculty/{id}/status"
FACULTY_REQUEST_TOPIC = lambda id: f"{BASE_TOPIC}/faculty/{id}/request"
FACULTY_RESPONSE_TOPIC = lambda id: f"{BASE_TOPIC}/faculty/{id}/response"
FACULTY_HEARTBEAT_TOPIC = lambda id: f"{BASE_TOPIC}/faculty/{id}/heartbeat"

# Legacy topics
LEGACY_STATUS_TOPIC = "faculty/1/status"
LEGACY_MESSAGES_TOPIC = "faculty/1/messages"
LEGACY_RESPONSES_TOPIC = "faculty/1/responses"
LEGACY_HEARTBEAT_TOPIC = "faculty/1/heartbeat"

# Message templates
STATUS_AVAILABLE = {
    "faculty_id": DEFAULT_FACULTY_ID,
    "faculty_name": "Test Faculty",
    "present": True,
    "status": "AVAILABLE",
    "department": "Test Department",
    "timestamp": str(int(time.time() * 1000)),
    "in_grace_period": False
}

STATUS_GRACE_PERIOD = {
    "faculty_id": DEFAULT_FACULTY_ID,
    "faculty_name": "Test Faculty",
    "present": True,
    "status": "AVAILABLE",
    "department": "Test Department",
    "timestamp": str(int(time.time() * 1000)),
    "in_grace_period": True,
    "grace_period_remaining": 45000
}

STATUS_UNAVAILABLE = {
    "faculty_id": DEFAULT_FACULTY_ID,
    "faculty_name": "Test Faculty",
    "present": False,
    "status": "AWAY",
    "department": "Test Department",
    "timestamp": str(int(time.time() * 1000)),
    "in_grace_period": False
}

CONSULTATION_REQUEST = {
    "consultation_id": 1,
    "student_id": 1,
    "student_name": "Test Student",
    "course_code": "CS101",
    "request_message": "Need help with assignment",
    "message": "Student: Test Student\nCourse: CS101\nRequest: Need help with assignment",
    "timestamp": str(int(time.time() * 1000))
}

RESPONSE_ACKNOWLEDGE = {
    "faculty_id": DEFAULT_FACULTY_ID,
    "faculty_name": "Test Faculty",
    "response_type": "ACKNOWLEDGE",
    "message_id": f"{int(time.time() * 1000)}_1234",
    "original_message": "Student: Test Student\nCourse: CS101\nRequest: Need help with assignment",
    "timestamp": str(int(time.time() * 1000)),
    "status": "Professor acknowledges the request and will respond accordingly"
}

RESPONSE_BUSY = {
    "faculty_id": DEFAULT_FACULTY_ID,
    "faculty_name": "Test Faculty",
    "response_type": "BUSY",
    "message_id": f"{int(time.time() * 1000)}_1234",
    "original_message": "Student: Test Student\nCourse: CS101\nRequest: Need help with assignment",
    "timestamp": str(int(time.time() * 1000)),
    "status": "Professor is currently busy and cannot cater to this request"
}

class FacultyDeskTester:
    def __init__(self, broker, port, username, password, faculty_id):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.faculty_id = faculty_id
        self.client = None
        self.connected = False
        self.received_messages = []
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            
            # Subscribe to response topics
            client.subscribe(FACULTY_RESPONSE_TOPIC(self.faculty_id))
            client.subscribe(LEGACY_RESPONSES_TOPIC)
            
            # Subscribe to request topics (to see our own messages for testing)
            client.subscribe(FACULTY_REQUEST_TOPIC(self.faculty_id))
            client.subscribe(LEGACY_MESSAGES_TOPIC)
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
            
    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            data = json.loads(payload)
            logger.info(f"Received message on topic {msg.topic}:")
            logger.info(json.dumps(data, indent=2))
            self.received_messages.append({
                'topic': msg.topic,
                'payload': data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(f"Raw payload: {msg.payload}")
            
    def connect(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
            
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Wait for connection
            for _ in range(10):
                if self.connected:
                    return True
                time.sleep(0.5)
                
            logger.error("Failed to connect to MQTT broker after timeout")
            return False
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False
            
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
            
    def publish_message(self, topic, message):
        if not self.connected:
            logger.error("Not connected to MQTT broker")
            return False
            
        try:
            result = self.client.publish(topic, json.dumps(message))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published message to {topic}")
                return True
            else:
                logger.error(f"Failed to publish message to {topic}, result code: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
            
    def simulate_availability_sequence(self):
        """Simulate a faculty becoming available, entering grace period, then becoming unavailable."""
        # 1. Faculty becomes available
        logger.info("\n=== TEST: Faculty Becomes Available ===")
        self.publish_message(FACULTY_STATUS_TOPIC(self.faculty_id), STATUS_AVAILABLE)
        time.sleep(2)
        
        # 2. Faculty enters grace period
        logger.info("\n=== TEST: Faculty Enters Grace Period ===")
        self.publish_message(FACULTY_STATUS_TOPIC(self.faculty_id), STATUS_GRACE_PERIOD)
        time.sleep(2)
        
        # 3. Faculty becomes unavailable
        logger.info("\n=== TEST: Faculty Becomes Unavailable ===")
        self.publish_message(FACULTY_STATUS_TOPIC(self.faculty_id), STATUS_UNAVAILABLE)
        time.sleep(2)
        
    def simulate_consultation_request(self):
        """Simulate a consultation request and response."""
        # 1. Faculty is available
        logger.info("\n=== TEST: Setting Faculty Available ===")
        self.publish_message(FACULTY_STATUS_TOPIC(self.faculty_id), STATUS_AVAILABLE)
        time.sleep(2)
        
        # 2. Send consultation request
        logger.info("\n=== TEST: Sending Consultation Request ===")
        self.publish_message(FACULTY_REQUEST_TOPIC(self.faculty_id), CONSULTATION_REQUEST)
        time.sleep(2)
        
        # 3. Simulate faculty acknowledging request
        logger.info("\n=== TEST: Faculty Acknowledges Request ===")
        self.publish_message(FACULTY_RESPONSE_TOPIC(self.faculty_id), RESPONSE_ACKNOWLEDGE)
        time.sleep(2)
        
    def simulate_legacy_topics(self):
        """Test compatibility with legacy topics."""
        # 1. Publish to legacy status topic
        logger.info("\n=== TEST: Legacy Status Topic ===")
        self.publish_message(LEGACY_STATUS_TOPIC, STATUS_AVAILABLE)
        time.sleep(2)
        
        # 2. Publish to legacy messages topic
        logger.info("\n=== TEST: Legacy Messages Topic ===")
        self.publish_message(LEGACY_MESSAGES_TOPIC, CONSULTATION_REQUEST)
        time.sleep(2)
        
    def run_all_tests(self):
        """Run all test scenarios."""
        if not self.connect():
            return False
            
        try:
            logger.info("\n=== STARTING INTEGRATION TESTS ===\n")
            
            # Run test sequences
            self.simulate_availability_sequence()
            self.simulate_consultation_request()
            self.simulate_legacy_topics()
            
            logger.info("\n=== TESTS COMPLETED ===\n")
            
            # Print summary
            logger.info(f"Received {len(self.received_messages)} messages during testing")
            
            return True
        except Exception as e:
            logger.error(f"Error during tests: {e}")
            return False
        finally:
            self.disconnect()

def main():
    parser = argparse.ArgumentParser(description="ConsultEase Faculty Desk Integration Test")
    parser.add_argument("--broker", default=DEFAULT_BROKER, help=f"MQTT broker address (default: {DEFAULT_BROKER})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT broker port (default: {DEFAULT_PORT})")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help=f"MQTT username (default: {DEFAULT_USERNAME})")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help=f"MQTT password (default: {DEFAULT_PASSWORD})")
    parser.add_argument("--faculty-id", type=int, default=DEFAULT_FACULTY_ID, help=f"Faculty ID to use (default: {DEFAULT_FACULTY_ID})")
    
    args = parser.parse_args()
    
    tester = FacultyDeskTester(
        args.broker, args.port, args.username, args.password, args.faculty_id)
    
    if tester.run_all_tests():
        logger.info("All tests completed successfully")
        return 0
    else:
        logger.error("Tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 