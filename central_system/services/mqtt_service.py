import paho.mqtt.client as mqtt
import json
import logging
import threading
import time
import os
import configparser
import pathlib
import random
from datetime import datetime
import ssl

# Import configuration system
from central_system.config import get_config

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # REMOVED
logger = logging.getLogger(__name__)

class MQTTService:
    """
    MQTT Service for communicating with the Faculty Desk Unit.
    """

    def __init__(self):
        # Load settings from settings.ini if available # REMOVED _load_settings call
        # self._load_settings()
        self.config = get_config() # Get central config instance

        # MQTT settings from config.py
        self.broker_host = self.config.get('mqtt.broker_host', 'localhost')
        self.broker_port = int(self.config.get('mqtt.broker_port', 1883))
        # Generate a unique client ID
        base_client_id = self.config.get('mqtt.client_id', 'central_system')
        self.client_id = f"{base_client_id}_{''.join(random.choices('0123456789abcdef', k=6))}"
        self.username = self.config.get('mqtt.username', None)
        self.password = self.config.get('mqtt.password', None)
        self.use_tls = self.config.get('mqtt.use_tls', False)
        self.tls_ca_certs = self.config.get('mqtt.tls_ca_certs', None)
        self.tls_certfile = self.config.get('mqtt.tls_certfile', None)
        self.tls_keyfile = self.config.get('mqtt.tls_keyfile', None)
        self.tls_insecure = self.config.get('mqtt.tls_insecure', False) # For testing, not production
        self.tls_version = self.config.get('mqtt.tls_version', None) # e.g., "TLSv1.2", "TLSv1.3"
        self.tls_cert_reqs = self.config.get('mqtt.tls_cert_reqs', 'CERT_REQUIRED') # e.g., "CERT_NONE", "CERT_OPTIONAL"

        # Log the MQTT broker settings
        logger.info(f"MQTT broker settings: {self.broker_host}:{self.broker_port}")

        # Initialize MQTT client
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # Configure TLS if enabled
        if self.use_tls:
            try:
                logger.info(f"Configuring MQTT with TLS. CA: {self.tls_ca_certs}, Cert: {self.tls_certfile}, Key: {self.tls_keyfile}, Version: {self.tls_version}, CertReqs: {self.tls_cert_reqs}")
                
                # Map string config values to ssl constants if necessary
                parsed_tls_version = None
                if self.tls_version:
                    if self.tls_version == "TLSv1.2":
                        parsed_tls_version = ssl.PROTOCOL_TLSv1_2
                    elif self.tls_version == "TLSv1.3":
                        # Note: Paho MQTT might use PROTOCOL_TLS_CLIENT which auto-negotiates
                        # Check Paho documentation for best way to enforce TLSv1.3 if strictly needed
                        # For now, this illustrates mapping. ssl.PROTOCOL_TLSv1_3 is not standard for client.
                        # Using PROTOCOL_TLS_CLIENT is generally recommended for broadest compatibility.
                        # If specific versions are needed, ensure the library and broker support it.
                        # For example, ssl.PROTOCOL_TLS_CLIENT is often the right choice.
                        # Let's assume config value "TLS_CLIENT" for auto-negotiation, or specific versions.
                        if hasattr(ssl, f"PROTOCOL_{self.tls_version.replace('.', '')}"):
                             parsed_tls_version = getattr(ssl, f"PROTOCOL_{self.tls_version.replace('.', '')}")
                        elif self.tls_version == "CLIENT_DEFAULT": # Add a sensible default
                            parsed_tls_version = ssl.PROTOCOL_TLS_CLIENT 
                        else:
                            logger.warning(f"Unsupported TLS version string: {self.tls_version}. Using library default.")
                            # parsed_tls_version will remain None, letting Paho decide or use its default.

                parsed_cert_reqs = None
                if self.tls_cert_reqs == "CERT_REQUIRED":
                    parsed_cert_reqs = ssl.CERT_REQUIRED
                elif self.tls_cert_reqs == "CERT_OPTIONAL":
                    parsed_cert_reqs = ssl.CERT_OPTIONAL
                elif self.tls_cert_reqs == "CERT_NONE":
                    parsed_cert_reqs = ssl.CERT_NONE
                else:
                    logger.warning(f"Unsupported tls_cert_reqs string: {self.tls_cert_reqs}. Using library default (likely CERT_REQUIRED with CA).")


                self.client.tls_set(
                    ca_certs=self.tls_ca_certs,
                    certfile=self.tls_certfile,
                    keyfile=self.tls_keyfile,
                    cert_reqs=parsed_cert_reqs, # Use parsed value
                    tls_version=parsed_tls_version # Use parsed value
                    # TODO: Add other TLS parameters like ciphers if needed from config
                )
                if self.tls_insecure: # Should only be used for testing with self-signed certs
                    logger.warning("MQTT TLS is configured with tls_insecure=True. Not for production!")
                    self.client.tls_insecure_set(True)
            except Exception as e:
                logger.error(f"Error configuring MQTT TLS: {e}. Proceeding without TLS.")
                self.use_tls = False # Fallback to no TLS if configuration fails

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Topic handlers
        self.topic_handlers = {}

        # Connection management
        self.is_connected = False
        self.reconnect_delay = 5  # seconds
        self.reconnect_thread = None
        self.stop_reconnect = False

        # Message storage for retry
        self._last_message = None
        self._last_raw_message = None

        # Message persistence
        self.message_queue_dir = "mqtt_queue"
        self._ensure_queue_directory()
        self._load_persisted_messages()

        # Set up keep-alive timer
        self.keep_alive_interval = 60  # seconds
        self.last_keep_alive = time.time()

        # Set up automatic reconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=60)

    def connect(self):
        """
        Connect to the MQTT broker.
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()

            # Start keep-alive timer
            self._start_keep_alive_timer()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {str(e)}")
            self.schedule_reconnect()

    def _start_keep_alive_timer(self):
        """
        Start a timer to periodically check the connection and send keep-alive pings.
        """
        # Create a timer thread that runs the keep-alive check
        self.keep_alive_thread = threading.Thread(target=self._keep_alive_worker)
        self.keep_alive_thread.daemon = True
        self.keep_alive_thread.start()
        logger.info("Started MQTT keep-alive timer")

    def _keep_alive_worker(self):
        """
        Worker thread for sending keep-alive pings and checking connection status.
        """
        while True:
            try:
                # Sleep for the keep-alive interval
                time.sleep(self.keep_alive_interval)

                # Check if we're still connected
                if not self.is_connected:
                    logger.warning("Keep-alive check: Not connected to MQTT broker")
                    self.schedule_reconnect()
                    continue

                # Send a ping to the broker
                try:
                    # Publish a small message to a system topic
                    current_time = time.time()
                    self.client.publish(
                        "consultease/system/ping",
                        json.dumps({"timestamp": current_time}),
                        qos=0,
                        retain=False
                    )
                    self.last_keep_alive = current_time
                    logger.debug(f"Sent MQTT keep-alive ping at {current_time}")
                except Exception as e:
                    logger.error(f"Error sending MQTT keep-alive ping: {str(e)}")
                    # If we can't send a ping, we might be disconnected
                    if self.is_connected:
                        logger.warning("Connection may be lost, scheduling reconnect")
                        self.schedule_reconnect()
            except Exception as e:
                logger.error(f"Error in MQTT keep-alive worker: {str(e)}")
                # Sleep a bit to avoid tight loop if there's an error
                time.sleep(5)

    def disconnect(self):
        """
        Disconnect from the MQTT broker and clean up resources.
        """
        logger.info("Disconnecting from MQTT broker")

        # Stop reconnection attempts
        self.stop_reconnect = True

        # Wait for reconnect thread to finish if it's running
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            logger.info("Waiting for reconnect thread to finish...")
            # We don't join the thread as it might be blocked, but we set the flag to stop it

        # Stop the MQTT client loop
        try:
            self.client.loop_stop()
            logger.info("Stopped MQTT client loop")
        except Exception as e:
            logger.error(f"Error stopping MQTT client loop: {str(e)}")

        # Disconnect from broker if connected
        if self.is_connected:
            try:
                self.client.disconnect()
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {str(e)}")

        # Reset connection state
        self.is_connected = False

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback when connected to the MQTT broker.
        """
        if rc == 0:
            self.is_connected = True
            logger.info("Connected to MQTT broker")
            # Subscribe to topics
            for topic in self.topic_handlers.keys():
                self.client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")

            # Process any persisted messages
            self._process_persisted_messages()
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
            self.schedule_reconnect()

    def on_disconnect(self, client, userdata, rc):
        """
        Callback when disconnected from the MQTT broker.
        """
        previous_state = self.is_connected
        self.is_connected = False

        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with code {rc}")
            # Only schedule reconnect if we were previously connected
            # This prevents multiple reconnect attempts
            if previous_state:
                logger.info("Scheduling reconnection attempt...")
                self.schedule_reconnect()
        else:
            logger.info("Disconnected from MQTT broker")

    def on_message(self, client, userdata, msg):
        """
        Callback when message is received.
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"Received message on topic {topic}: {payload}")

            # Process message with registered handler
            if topic in self.topic_handlers:
                try:
                    # Try to parse as JSON
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning(f"Message is not JSON, treating as string: {payload}")
                    data = payload  # Use the raw string as data

                for handler in self.topic_handlers[topic]:
                    try:
                        handler(topic, data)
                    except Exception as e:
                        logger.error(f"Error in message handler for topic {topic}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {str(e)}")

    def register_topic_handler(self, topic, handler):
        """
        Register a handler for a specific topic.

        Args:
            topic (str): MQTT topic to subscribe to
            handler (callable): Function to call when a message is received on this topic
        """
        if topic not in self.topic_handlers:
            self.topic_handlers[topic] = []
            # If already connected, subscribe to the topic
            if self.is_connected:
                self.client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")

        self.topic_handlers[topic].append(handler)
        logger.info(f"Registered handler for topic {topic}")

    def publish(self, topic, data, qos=0, retain=False, max_retries=3):
        """
        Publish a message to a topic with retry logic.

        Args:
            topic (str): MQTT topic to publish to
            data (dict): Data to publish (will be converted to JSON)
            qos (int): Quality of Service level (0, 1, or 2)
            retain (bool): Whether to retain the message on the broker
            max_retries (int): Maximum number of retry attempts if publishing fails

        Returns:
            bool: True if publishing was successful, False otherwise
        """
        # Store the message for potential retry
        self._store_last_message(topic, data, qos, retain)

        # Check connection status
        if not self.is_connected:
            logger.warning(f"Cannot publish to {topic}: Not connected to MQTT broker")
            # Try to reconnect
            self.schedule_reconnect()

            # For important messages, wait briefly for reconnection
            if qos > 0:
                logger.info(f"Waiting briefly for reconnection to send important message (QoS {qos})")
                for _ in range(10):  # Wait up to 5 seconds
                    time.sleep(0.5)
                    if self.is_connected:
                        logger.info("Reconnected, proceeding with publish")
                        break
                else:
                    logger.warning("Reconnection timeout, message will be queued for later delivery")
                    return False
            else:
                return False

        try:
            # Format the payload for the faculty desk unit
            # If this is a consultation request, format it for the faculty desk unit
            if "consultease/faculty/" in topic and "/requests" in topic:
                # Format the message for the faculty desk unit
                formatted_data = self._format_for_faculty_desk_unit(data)
                payload = json.dumps(formatted_data)
            else:
                # Regular JSON payload
                payload = json.dumps(data)

            # Try to publish with retries
            for attempt in range(max_retries):
                try:
                    # Check connection again before each attempt
                    if not self.is_connected and attempt > 0:
                        logger.warning(f"Lost connection during publish attempts to {topic}")
                        self.schedule_reconnect()
                        time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds
                        if not self.is_connected:
                            continue

                    # Publish the message
                    result = self.client.publish(topic, payload, qos=qos, retain=retain)

                    # Check if the publish was successful
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        # For QoS 1 and 2, wait for the message to be delivered
                        if qos > 0:
                            try:
                                # Wait for message to be delivered
                                message_info = result
                                if not message_info.is_published():
                                    message_info.wait_for_publish(timeout=5.0)

                                if message_info.is_published():
                                    logger.debug(f"Published message to {topic} (QoS {qos}) and confirmed delivery")
                                else:
                                    logger.warning(f"Message to {topic} (QoS {qos}) may not have been delivered")
                                    # Try again if we haven't reached max retries
                                    if attempt < max_retries - 1:
                                        continue
                            except Exception as e:
                                logger.error(f"Error waiting for message delivery to {topic}: {str(e)}")
                                # Try again if we haven't reached max retries
                                if attempt < max_retries - 1:
                                    continue
                        else:
                            logger.debug(f"Published message to {topic}")

                        return True
                    else:
                        logger.warning(f"Failed to publish message to {topic} (attempt {attempt+1}/{max_retries}): MQTT error code {result.rc}")

                        # If we're not connected, try to reconnect
                        if not self.is_connected:
                            self.schedule_reconnect()
                            time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds
                except Exception as e:
                    logger.error(f"Error publishing message to {topic} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds

            # If we get here, all retries failed
            logger.error(f"Failed to publish message to {topic} after {max_retries} attempts")
            return False

        except Exception as e:
            logger.error(f"Failed to prepare message for {topic}: {str(e)}")
            return False

    def _store_last_message(self, topic, data, qos, retain):
        """
        Store the last message for potential retry.

        Args:
            topic (str): MQTT topic
            data (dict): Message data
            qos (int): Quality of Service level
            retain (bool): Whether to retain the message
        """
        # Store in instance variable for potential retry
        message = {
            'topic': topic,
            'data': data,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time()
        }
        self._last_message = message

        # For important messages (QoS > 0), also persist to disk
        if qos > 0:
            self._store_message_to_disk(message)

    def publish_raw(self, topic, message, qos=0, retain=False, max_retries=3):
        """
        Publish a raw message to a topic with retry logic.
        This is used for the faculty desk unit which expects a plain string message.

        Args:
            topic (str): MQTT topic to publish to
            message (str): Message to publish (will be sent as-is, not converted to JSON)
            qos (int): Quality of Service level (0, 1, or 2)
            retain (bool): Whether to retain the message on the broker
            max_retries (int): Maximum number of retry attempts if publishing fails

        Returns:
            bool: True if publishing was successful, False otherwise
        """
        # Store the message for potential retry
        self._store_last_raw_message(topic, message, qos, retain)

        # Check connection status
        if not self.is_connected:
            logger.warning(f"Cannot publish raw message to {topic}: Not connected to MQTT broker")
            # Try to reconnect
            self.schedule_reconnect()

            # For important messages, wait briefly for reconnection
            if qos > 0:
                logger.info(f"Waiting briefly for reconnection to send important raw message (QoS {qos})")
                for _ in range(10):  # Wait up to 5 seconds
                    time.sleep(0.5)
                    if self.is_connected:
                        logger.info("Reconnected, proceeding with raw publish")
                        break
                else:
                    logger.warning("Reconnection timeout, raw message will be queued for later delivery")
                    return False
            else:
                return False

        try:
            # Try to publish with retries
            for attempt in range(max_retries):
                try:
                    # Check connection again before each attempt
                    if not self.is_connected and attempt > 0:
                        logger.warning(f"Lost connection during raw publish attempts to {topic}")
                        self.schedule_reconnect()
                        time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds
                        if not self.is_connected:
                            continue

                    # Publish the message
                    result = self.client.publish(topic, message, qos=qos, retain=retain)

                    # Check if the publish was successful
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        # For QoS 1 and 2, wait for the message to be delivered
                        if qos > 0:
                            try:
                                # Wait for message to be delivered
                                message_info = result
                                if not message_info.is_published():
                                    message_info.wait_for_publish(timeout=5.0)

                                if message_info.is_published():
                                    logger.debug(f"Published raw message to {topic} (QoS {qos}) and confirmed delivery")
                                else:
                                    logger.warning(f"Raw message to {topic} (QoS {qos}) may not have been delivered")
                                    # Try again if we haven't reached max retries
                                    if attempt < max_retries - 1:
                                        continue
                            except Exception as e:
                                logger.error(f"Error waiting for raw message delivery to {topic}: {str(e)}")
                                # Try again if we haven't reached max retries
                                if attempt < max_retries - 1:
                                    continue
                        else:
                            logger.debug(f"Published raw message to {topic}")

                        return True
                    else:
                        logger.warning(f"Failed to publish raw message to {topic} (attempt {attempt+1}/{max_retries}): MQTT error code {result.rc}")

                        # If we're not connected, try to reconnect
                        if not self.is_connected:
                            self.schedule_reconnect()
                            time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds
                except Exception as e:
                    logger.error(f"Error publishing raw message to {topic} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds

            # If we get here, all retries failed
            logger.error(f"Failed to publish raw message to {topic} after {max_retries} attempts")
            return False

        except Exception as e:
            logger.error(f"Failed to prepare raw message for {topic}: {str(e)}")
            return False

    def _store_last_raw_message(self, topic, message, qos, retain):
        """
        Store the last raw message for potential retry.

        Args:
            topic (str): MQTT topic
            message (str): Raw message
            qos (int): Quality of Service level
            retain (bool): Whether to retain the message
        """
        # Store in instance variable for potential retry
        raw_message = {
            'topic': topic,
            'message': message,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time(),
            'is_raw': True
        }
        self._last_raw_message = raw_message

        # For important messages (QoS > 0), also persist to disk
        if qos > 0:
            self._store_message_to_disk(raw_message)

    def _ensure_queue_directory(self):
        """
        Ensure the message queue directory exists.
        """
        try:
            os.makedirs(self.message_queue_dir, exist_ok=True)
            logger.debug(f"Ensured message queue directory exists: {self.message_queue_dir}")
        except Exception as e:
            logger.error(f"Error creating message queue directory: {str(e)}")

    def _store_message_to_disk(self, message):
        """
        Store a message to disk for later delivery.

        Args:
            message (dict): Message data including topic, payload, QoS, etc.
        """
        try:
            # Ensure directory exists
            self._ensure_queue_directory()

            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_id = random.randint(1000, 9999)
            filename = f"{self.message_queue_dir}/msg_{timestamp}_{random_id}.json"

            # Write message to file
            with open(filename, 'w') as f:
                json.dump(message, f)

            logger.info(f"Stored message to {filename} for later delivery")
        except Exception as e:
            logger.error(f"Error storing message to disk: {str(e)}")

    def _load_persisted_messages(self):
        """
        Load persisted messages from disk.
        """
        try:
            # Ensure directory exists
            self._ensure_queue_directory()

            # Get list of message files
            message_files = [f for f in os.listdir(self.message_queue_dir) if f.endswith('.json')]

            if message_files:
                logger.info(f"Found {len(message_files)} persisted messages")
                # We'll process these when connected
            else:
                logger.debug("No persisted messages found")
        except Exception as e:
            logger.error(f"Error loading persisted messages: {str(e)}")

    def _process_persisted_messages(self):
        """
        Process persisted messages from disk and attempt to send them.
        """
        if not self.is_connected:
            logger.warning("Cannot process persisted messages: Not connected to MQTT broker")
            return

        try:
            # Ensure directory exists
            self._ensure_queue_directory()

            # Get list of message files
            message_files = [f for f in os.listdir(self.message_queue_dir) if f.endswith('.json')]

            if not message_files:
                logger.debug("No persisted messages to process")
                return

            logger.info(f"Processing {len(message_files)} persisted messages")

            # Process each message file
            for filename in message_files:
                try:
                    filepath = os.path.join(self.message_queue_dir, filename)

                    # Read message from file
                    with open(filepath, 'r') as f:
                        message = json.load(f)

                    # Attempt to send the message
                    success = False
                    if message.get('is_raw', False):
                        # This is a raw message
                        success = self.publish_raw(
                            message['topic'],
                            message['message'],
                            message['qos'],
                            message['retain']
                        )
                    else:
                        # This is a JSON message
                        success = self.publish(
                            message['topic'],
                            message['data'],
                            message['qos'],
                            message['retain']
                        )

                    if success:
                        logger.info(f"Successfully sent persisted message from {filepath}")
                        # Remove the file
                        os.remove(filepath)
                    else:
                        logger.warning(f"Failed to send persisted message from {filepath}, will retry later")
                except Exception as e:
                    logger.error(f"Error processing persisted message {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing persisted messages: {str(e)}")

    def _load_settings(self):
        """
        Load settings from settings.ini file if available.
        """
        # THIS METHOD IS DEPRECATED AND SHOULD NOT BE USED.
        # Configuration is now handled by config.py
        logger.warning("_load_settings in MQTTService is deprecated. MQTT config should come from central config system.")
        self.settings = {}
        return

        # try:
        #     # Get the path to the settings.ini file
        #     settings_path = pathlib.Path(__file__).parent.parent / "settings.ini"
        #
        #     if settings_path.exists():
        #         logger.info(f"Loading settings from {settings_path}")
        #         config = configparser.ConfigParser()
        #         config.read(settings_path)
        #
        #         # Load MQTT settings
        #         if 'MQTT' in config:
        #             self.settings['broker_host'] = config['MQTT'].get('broker_host', 'localhost')
        #             self.settings['broker_port'] = config['MQTT'].get('broker_port', '1883')
        #             logger.info(f"Loaded MQTT settings from file: {self.settings['broker_host']}:{self.settings['broker_port']}")
        #     else:
        #         logger.warning(f"Settings file not found at {settings_path}, using default values")
        # except Exception as e:
        #     logger.error(f"Error loading settings: {str(e)}")
        #     # Continue with default settings

    def _format_for_faculty_desk_unit(self, data):
        """
        Format a consultation request message for the faculty desk unit.

        Args:
            data (dict): The original consultation data

        Returns:
            dict: Formatted data for the faculty desk unit
        """
        try:
            # Extract relevant information
            student_name = data.get('student_name', 'Unknown Student')
            request_message = data.get('request_message', '')
            course_code = data.get('course_code', '')

            # IMPORTANT: Always use the message field if it exists
            # This ensures consistency with the test message format
            if 'message' in data and isinstance(data['message'], str):
                # Use the pre-formatted message
                message = data['message']
                logger.info(f"Using pre-formatted message: {message}")
            else:
                # Format the message for the faculty desk unit display
                message = f"Student: {student_name}\n"
                if course_code:
                    message += f"Course: {course_code}\n"
                message += f"Request: {request_message}"
                logger.info(f"Created formatted message: {message}")

            # Create a simplified payload for the faculty desk unit
            # The faculty desk unit expects a 'message' field that it can display directly
            # IMPORTANT: Keep this format EXACTLY the same as the test message format
            formatted_data = {
                'message': message,  # This is the most important field for the faculty desk unit
                'student_name': student_name,
                'course_code': course_code,
                'consultation_id': data.get('id'),
                'timestamp': data.get('requested_at')
            }

            # Log the formatted data for debugging
            logger.info(f"Formatted data for faculty desk unit: {formatted_data}")

            # Return the formatted data
            return formatted_data
        except Exception as e:
            logger.error(f"Error formatting message for faculty desk unit: {str(e)}")
            # If there's an error, still try to include the message field
            if not 'message' in data and 'request_message' in data:
                data['message'] = f"Student: {data.get('student_name', 'Unknown')}\nRequest: {data.get('request_message', '')}"
            # Return the original data if there's an error
            return data

    def schedule_reconnect(self):
        """
        Schedule a reconnection attempt.
        """
        if self.reconnect_thread is not None and self.reconnect_thread.is_alive():
            return

        self.stop_reconnect = False
        self.reconnect_thread = threading.Thread(target=self._reconnect_worker)
        self.reconnect_thread.daemon = True
        self.reconnect_thread.start()

    def _reconnect_worker(self):
        """
        Worker thread for reconnecting to the MQTT broker.
        Uses exponential backoff for reconnection attempts.
        """
        # Start with initial delay and increase up to a maximum
        current_delay = self.reconnect_delay
        max_delay = 60  # Maximum delay in seconds
        attempt = 1
        max_attempts = 20  # Maximum number of attempts before giving up temporarily

        while not self.stop_reconnect and not self.is_connected:
            logger.info(f"Attempting to reconnect to MQTT broker in {current_delay} seconds (attempt {attempt}/{max_attempts})")

            # Sleep in smaller increments to check stop_reconnect more frequently
            for _ in range(int(current_delay * 2)):
                if self.stop_reconnect:
                    break
                time.sleep(0.5)  # Sleep for 0.5 seconds at a time

            if self.stop_reconnect:
                logger.info("Reconnection attempts stopped by request")
                break

            # Check if we're already connected (might have happened in another thread)
            if self.is_connected:
                logger.info("Already reconnected to MQTT broker")
                break

            try:
                # Try to reconnect
                logger.info(f"Reconnecting to MQTT broker at {self.broker_host}:{self.broker_port}")

                # Instead of just reconnect, we'll do a full disconnect/connect cycle
                try:
                    # First try to disconnect cleanly if we think we're connected
                    self.client.disconnect()
                except Exception:
                    # Ignore errors during disconnect
                    pass

                # Wait a moment for the disconnect to complete
                time.sleep(1)

                # Now try to connect fresh
                self.client.connect(self.broker_host, self.broker_port, 60)

                # If we get here without exception, we're connected
                logger.info("Successfully reconnected to MQTT broker")

                # Resubscribe to all topics
                for topic in self.topic_handlers.keys():
                    self.client.subscribe(topic)
                    logger.info(f"Resubscribed to {topic}")

                # Reset delay for next time
                current_delay = self.reconnect_delay
                attempt = 1

                # Ensure loop is running
                if not self.client.is_connected():
                    self.client.loop_start()

            except Exception as e:
                logger.error(f"Failed to reconnect to MQTT broker (attempt {attempt}/{max_attempts}): {str(e)}")

                # Increase delay with exponential backoff, but cap at max_delay
                current_delay = min(current_delay * 1.5, max_delay)
                attempt += 1

                # If we've tried many times, log a more severe message
                if attempt > 10:
                    logger.critical(
                        f"Multiple failed attempts to connect to MQTT broker. "
                        f"Please check network connectivity and broker status."
                    )

                # If we've reached max attempts, take a longer break before trying again
                if attempt >= max_attempts:
                    logger.critical(f"Reached maximum reconnection attempts ({max_attempts}). Taking a longer break before trying again.")
                    time.sleep(300)  # 5 minute break
                    attempt = 1  # Reset attempt counter

# Singleton instance
mqtt_service = None

def get_mqtt_service():
    """
    Get the singleton MQTT service instance.
    """
    global mqtt_service
    if mqtt_service is None:
        mqtt_service = MQTTService()
    return mqtt_service

def test_mqtt_connection(faculty_id=3, message="Test message from MQTT service"):
    """
    Test the MQTT connection by sending a message to the faculty desk unit.

    Args:
        faculty_id (int): Faculty ID to send the message to
        message (str): Message to send

    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    try:
        # Get the MQTT service
        mqtt_service = get_mqtt_service()

        # Ensure the MQTT service is connected
        if not mqtt_service.is_connected:
            logger.warning("MQTT service is not connected. Attempting to connect...")
            mqtt_service.connect()
            # Wait briefly for connection
            import time
            time.sleep(1)

            if not mqtt_service.is_connected:
                logger.error("Failed to connect to MQTT service.")
                return False

        # Send a test message to the faculty desk unit
        logger.info(f"Sending test message to faculty ID {faculty_id}: {message}")

        # Send to the plain text topic
        success_text = mqtt_service.publish_raw("professor/messages", message)

        # Send to the faculty-specific topic
        topic = f"consultease/faculty/{faculty_id}/requests"
        payload = {
            'id': 0,
            'student_id': 0,
            'student_name': "System Test",
            'student_department': "System",
            'faculty_id': faculty_id,
            'request_message': message,
            'course_code': "TEST",
            'status': "test",
            'requested_at': time.time(),
            'message': message
        }
        success_json = mqtt_service.publish(topic, payload)

        # Send to the faculty-specific plain text topic
        success_faculty = mqtt_service.publish_raw(f"consultease/faculty/{faculty_id}/messages", message)

        # Log the results
        logger.info(f"Test message results: JSON: {success_json}, Text: {success_text}, Faculty: {success_faculty}")

        return success_json or success_text or success_faculty
    except Exception as e:
        logger.error(f"Error testing MQTT connection: {str(e)}")
        return False