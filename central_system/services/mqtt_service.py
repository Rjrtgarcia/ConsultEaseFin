import logging
import paho.mqtt.client as mqtt
import json
import ssl
import os
import time
import threading
from threading import Lock, Thread, Event

from central_system.config import get_config
from central_system.utils.mqtt_topics import get_faculty_status_topic, SYSTEM_STATUS_TOPIC

logger = logging.getLogger(__name__)


class MQTTService:
    _instance = None
    _lock = Lock()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.config = get_config()
        self.client = None
        self.is_connected = False
        self.reconnect_delay = 5  # Start with 5 seconds
        self.max_reconnect_delay = 300  # Maximum delay of 5 minutes
        self.connect_thread = None
        self.stop_event = Event()
        self.subscriptions = set()
        self.message_handlers = {}
        self.initialize()

    def initialize(self):
        """Initialize the MQTT client and set up callbacks."""
        logger.info("Initializing MQTT service")

        # Clean up any existing client
        if self.client:
            try:
                self.client.disconnect()
            except BaseException:
                pass

        # Create a new client instance
        client_id = f"consultease_central_{os.getpid()}"
        self.client = mqtt.Client(client_id=client_id, clean_session=True)

        # Set up authentication if configured
        username = self.config.get('mqtt.username')
        password = self.config.get('mqtt.password')
        if username and password:
            self.client.username_pw_set(username, password)

        # Configure TLS if enabled
        if self.config.get('mqtt.use_tls', False):
            self.configure_tls()

        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Set up persistence for QoS > 0 messages
        if self.config.get('mqtt.persistence', False):
            persistence_path = self.config.get('mqtt.persistence_dir', '/tmp/mqtt_consultease')
            os.makedirs(persistence_path, exist_ok=True)
            self.client.enable_logger(logger)

        # Start connection thread
        self.connect_async()

    def configure_tls(self):
        """Configure TLS for the MQTT client."""
        try:
            # Get TLS configuration
            ca_certs = self.config.get('mqtt.tls_ca_certs')
            certfile = self.config.get('mqtt.tls_certfile')
            keyfile = self.config.get('mqtt.tls_keyfile')
            tls_version = self.config.get('mqtt.tls_version')
            cert_reqs = self.config.get('mqtt.tls_cert_reqs', ssl.CERT_REQUIRED)
            ciphers = self.config.get('mqtt.tls_ciphers')
            insecure = self.config.get('mqtt.tls_insecure', False)

            # Map string values to constants if necessary
            if isinstance(tls_version, str):
                tls_versions = {
                    'tlsv1': ssl.PROTOCOL_TLSv1,
                    'tlsv1.1': ssl.PROTOCOL_TLSv1_1,
                    'tlsv1.2': ssl.PROTOCOL_TLSv1_2,
                    'tlsv1.3': getattr(ssl, 'PROTOCOL_TLSv1_3', ssl.PROTOCOL_TLS)
                }
                tls_version = tls_versions.get(tls_version.lower(), ssl.PROTOCOL_TLS)

            if isinstance(cert_reqs, str):
                cert_reqs_map = {
                    'cert_none': ssl.CERT_NONE,
                    'cert_optional': ssl.CERT_OPTIONAL,
                    'cert_required': ssl.CERT_REQUIRED
                }
                cert_reqs = cert_reqs_map.get(cert_reqs.lower(), ssl.CERT_REQUIRED)

            # Configure TLS
            self.client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile,
                cert_reqs=cert_reqs,
                tls_version=tls_version,
                ciphers=ciphers
            )

            if insecure:
                self.client.tls_insecure_set(True)

            logger.info("TLS configured for MQTT client")
        except Exception as e:
            logger.error(f"Failed to configure TLS: {e}")
            raise

    def connect_async(self):
        """Start a background thread to handle connection and reconnection."""
        if self.connect_thread and self.connect_thread.is_alive():
            return

        self.stop_event.clear()
        self.connect_thread = Thread(target=self._connection_worker, daemon=True)
        self.connect_thread.start()

    def _connection_worker(self):
        """Worker thread to handle connection and reconnection."""
        while not self.stop_event.is_set():
            if not self.is_connected:
                try:
                    host = self.config.get('mqtt.broker_host', 'localhost')
                    port = self.config.get('mqtt.broker_port', 1883)

                    logger.info(f"Connecting to MQTT broker at {host}:{port}")
                    self.client.connect_async(host, port)
                    self.client.loop_start()

                    # Wait for connection or timeout
                    for _ in range(30):  # 30 * 0.1 = 3 seconds timeout
                        if self.is_connected:
                            break
                        if self.stop_event.is_set():
                            return
                        time.sleep(0.1)

                    if not self.is_connected:
                        logger.warning("Failed to connect to MQTT broker, will retry")
                        self.client.loop_stop()

                except Exception as e:
                    logger.error(f"Error connecting to MQTT broker: {e}")

                # If still not connected, implement exponential backoff
                if not self.is_connected:
                    logger.info(f"Waiting {self.reconnect_delay} seconds before reconnecting")
                    if self.stop_event.wait(self.reconnect_delay):
                        return

                    # Exponential backoff with jitter
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            else:
                # Reset reconnect delay once connected
                self.reconnect_delay = 5

                # Sleep while connected, check every second
                if self.stop_event.wait(1):
                    return

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.is_connected = True
            self.reconnect_delay = 5  # Reset reconnect delay

            # Resubscribe to all topics
            for topic in self.subscriptions:
                logger.info(f"Resubscribing to {topic}")
                self.client.subscribe(topic)

            # Publish system online status
            self.publish(SYSTEM_STATUS_TOPIC, json.dumps({"status": "online"}), qos=1, retain=True)
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error = error_messages.get(rc, f"Unknown error (code: {rc})")
            logger.error(f"Failed to connect to MQTT broker: {error}")
            self.is_connected = False

    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the server."""
        self.is_connected = False
        if rc == 0:
            logger.info("Disconnected from MQTT broker")
        else:
            logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc})")

    def on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker."""
        try:
            logger.debug(f"Received message on topic {msg.topic}: {msg.payload}")

            # Look for a handler for this specific topic
            if msg.topic in self.message_handlers:
                for handler in self.message_handlers[msg.topic]:
                    try:
                        handler(msg.topic, msg.payload)
                    except Exception as e:
                        logger.error(f"Error in message handler for topic {msg.topic}: {e}")

            # Also check for wildcard topic handlers
            for topic_pattern, handlers in self.message_handlers.items():
                if '+' in topic_pattern or '#' in topic_pattern:
                    if mqtt.topic_matches_sub(topic_pattern, msg.topic):
                        for handler in handlers:
                            try:
                                handler(msg.topic, msg.payload)
                            except Exception as e:
                                logger.error(
                                    f"Error in wildcard message handler for {topic_pattern} (received {msg.topic}): {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def subscribe(self, topic, qos=0, handler=None):
        """Subscribe to a topic and optionally register a message handler."""
        if not self.client:
            logger.error("Cannot subscribe: MQTT client not initialized")
            return False

        logger.info(f"Subscribing to topic: {topic}")
        self.subscriptions.add(topic)

        if handler:
            if topic not in self.message_handlers:
                self.message_handlers[topic] = []
            self.message_handlers[topic].append(handler)

        if self.is_connected:
            result, _ = self.client.subscribe(topic, qos)
            return result == mqtt.MQTT_ERR_SUCCESS
        return False

    def unsubscribe(self, topic, handler=None):
        """Unsubscribe from a topic and optionally remove a specific handler."""
        if not self.client:
            logger.error("Cannot unsubscribe: MQTT client not initialized")
            return False

        logger.info(f"Unsubscribing from topic: {topic}")

        # Remove handler if specified
        if handler and topic in self.message_handlers:
            self.message_handlers[topic] = [h for h in self.message_handlers[topic] if h != handler]
            if not self.message_handlers[topic]:
                del self.message_handlers[topic]

        # Only fully unsubscribe if no handlers remain for this topic
        if handler is None or topic not in self.message_handlers:
            if self.is_connected:
                result, _ = self.client.unsubscribe(topic)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    self.subscriptions.discard(topic)
                return result == mqtt.MQTT_ERR_SUCCESS
            self.subscriptions.discard(topic)

        return True

    def publish(self, topic, payload, qos=0, retain=False):
        """Publish a message to the specified topic."""
        if not self.client:
            logger.error("Cannot publish: MQTT client not initialized")
            return False

        if not self.is_connected:
            logger.warning(f"Cannot publish to {topic}: Not connected to MQTT broker")
            return False

        try:
            logger.debug(f"Publishing to {topic}: {payload}")
            result = self.client.publish(topic, payload, qos, retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
            return False

    def stop(self):
        """Stop the MQTT client and clean up resources."""
        logger.info("Stopping MQTT service")
        self.stop_event.set()

        if self.is_connected:
            try:
                # Publish offline status before disconnecting
                self.publish(SYSTEM_STATUS_TOPIC, json.dumps(
                    {"status": "offline"}), qos=1, retain=True)
                time.sleep(0.5)  # Give a small delay for the message to be sent
            except BaseException:
                pass

        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except BaseException:
                pass

        self.is_connected = False

        if self.connect_thread and self.connect_thread.is_alive():
            self.connect_thread.join(timeout=5)

    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.stop()

# Helper function to get the singleton instance


def get_mqtt_service():
    return MQTTService.instance()
