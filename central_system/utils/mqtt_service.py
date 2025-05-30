import paho.mqtt.client as mqtt
import time
import json
import threading
import queue
import logging
import os
from typing import Callable, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


class MQTTService:
    """
    Enhanced MQTT Service with improved error handling, message acknowledgment,
    automatic reconnection with exponential backoff, and message queuing.
    """

    def __init__(
            self,
            client_id: str,
            broker_host: str,
            broker_port: int = 1883):
        """
        Initialize the MQTT service.

        Args:
            client_id: Unique client identifier
            broker_host: MQTT broker hostname or IP
            broker_port: MQTT broker port (default: 1883)
        """
        self.client_id = client_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(client_id=client_id)

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish

        # Topic subscriptions and callbacks
        self.topic_callbacks: Dict[str, Callable] = {}

        # Message queue for offline operation
        self.message_queue = queue.Queue()
        self.is_connected = False
        self.reconnect_delay = 1  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 120  # Maximum reconnect delay in seconds

        # Message acknowledgment tracking
        self.pending_messages: Dict[int, Dict[str, Any]] = {}
        self.message_lock = threading.Lock()

        # Start the message processing thread
        self.stop_event = threading.Event()
        self.queue_processor = threading.Thread(
            target=self._process_message_queue)
        self.queue_processor.daemon = True
        self.queue_processor.start()

        # Start the acknowledgment timeout checker
        self.ack_checker = threading.Thread(target=self._check_ack_timeouts)
        self.ack_checker.daemon = True
        self.ack_checker.start()

    def connect(self) -> bool:
        """
        Connect to the MQTT broker with automatic reconnection.

        Returns:
            bool: True if connection attempt was initiated
        """
        try:
            logger.info(
                f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect_async(self.broker_host, self.broker_port)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            # Schedule reconnection
            threading.Timer(self.reconnect_delay, self._reconnect).start()
            return False

    def _reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        if not self.is_connected:
            try:
                logger.info(
                    f"Attempting to reconnect to MQTT broker (delay: {self.reconnect_delay}s)")
                self.client.connect_async(self.broker_host, self.broker_port)
                # Don't need to call loop_start() again as it should still be
                # running
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                # Increase reconnect delay with exponential backoff
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, self.max_reconnect_delay)
                threading.Timer(self.reconnect_delay, self._reconnect).start()

    def disconnect(self):
        """Disconnect from the MQTT broker and stop background threads."""
        self.stop_event.set()
        self.client.loop_stop()
        self.client.disconnect()

    def subscribe(self, topic: str, callback: Callable):
        """
        Subscribe to an MQTT topic and register a callback.

        Args:
            topic: MQTT topic to subscribe to
            callback: Function to call when a message is received on this topic
        """
        self.topic_callbacks[topic] = callback
        if self.is_connected:
            self.client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")

    def publish(
            self,
            topic: str,
            payload: Any,
            qos: int = 1,
            retain: bool = False,
            timeout: int = 30,
            retry_count: int = 3) -> int:
        """
        Publish a message to an MQTT topic with acknowledgment tracking.

        Args:
            topic: MQTT topic to publish to
            payload: Message payload (will be converted to JSON if not a string)
            qos: Quality of Service (0, 1, or 2)
            retain: Whether to retain the message on the broker
            timeout: Acknowledgment timeout in seconds
            retry_count: Number of retries if acknowledgment fails

        Returns:
            int: Message ID if published, -1 if queued for later
        """
        # Convert payload to JSON string if it's not already a string
        if not isinstance(payload, str):
            payload = json.dumps(payload)

        if self.is_connected:
            try:
                message_info = self.client.publish(
                    topic, payload, qos=qos, retain=retain)
                message_id = message_info.mid

                # Track message for acknowledgment if QoS > 0
                if qos > 0:
                    with self.message_lock:
                        self.pending_messages[message_id] = {
                            'topic': topic,
                            'payload': payload,
                            'qos': qos,
                            'retain': retain,
                            'timestamp': time.time(),
                            'timeout': timeout,
                            'retry_count': retry_count,
                            'retries_left': retry_count
                        }

                return message_id
            except Exception as e:
                logger.error(f"Failed to publish message to {topic}: {e}")
                # Queue the message for later
                self.message_queue.put({
                    'topic': topic,
                    'payload': payload,
                    'qos': qos,
                    'retain': retain,
                    'timeout': timeout,
                    'retry_count': retry_count
                })
                return -1
        else:
            # Queue the message for when we're connected
            logger.info(f"Not connected, queueing message to {topic}")
            self.message_queue.put({
                'topic': topic,
                'payload': payload,
                'qos': qos,
                'retain': retain,
                'timeout': timeout,
                'retry_count': retry_count
            })
            return -1

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.is_connected = True
            self.reconnect_delay = 1  # Reset reconnect delay

            # Subscribe to all registered topics
            for topic in self.topic_callbacks:
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
            self.is_connected = False
            # Schedule reconnection
            threading.Timer(self.reconnect_delay, self._reconnect).start()

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker."""
        self.is_connected = False
        if rc != 0:
            logger.warning(
                f"Unexpected disconnection from MQTT broker with code: {rc}")
            # Schedule reconnection
            threading.Timer(self.reconnect_delay, self._reconnect).start()
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            # Check if this is an acknowledgment message
            if topic.endswith('/ack'):
                self._handle_acknowledgment(payload)
                return

            # Find the callback for this topic
            for registered_topic, callback in self.topic_callbacks.items():
                # Check for exact match or wildcard match
                if registered_topic == topic or self._topic_matches_subscription(
                        registered_topic, topic):
                    try:
                        # Try to parse as JSON
                        try:
                            payload_data = json.loads(payload)
                        except json.JSONDecodeError:
                            payload_data = payload

                        # Call the callback
                        callback(topic, payload_data)
                    except Exception as e:
                        logger.error(
                            f"Error in callback for topic {topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _topic_matches_subscription(self, subscription, topic):
        """
        Check if a topic matches a subscription with wildcards.

        Args:
            subscription: Subscription topic pattern (may contain wildcards)
            topic: Actual topic to check

        Returns:
            bool: True if the topic matches the subscription
        """
        # Split both into parts
        sub_parts = subscription.split('/')
        topic_parts = topic.split('/')

        # If the lengths don't match and there's no multi-level wildcard
        if len(sub_parts) != len(topic_parts) and '#' not in sub_parts:
            return False

        # Check each part
        for i, sub_part in enumerate(sub_parts):
            # Multi-level wildcard matches everything
            if sub_part == '#':
                return True

            # Single-level wildcard matches anything at this level
            if sub_part == '+':
                # Make sure we're not at the end of the topic
                if i >= len(topic_parts):
                    return False
                continue

            # If we've reached the end of the topic but not the subscription
            if i >= len(topic_parts):
                return False

            # Exact match required
            if sub_part != topic_parts[i]:
                return False

        # If we've processed all parts successfully
        return True

    def _process_message_queue(self):
        """Background thread that processes the message queue."""
        while not self.stop_event.is_set():
            try:
                # Wait for a message in the queue or a stop event
                try:
                    message = self.message_queue.get(timeout=1.0)

                    # Try to publish the message
                    if self.is_connected:
                        self.publish(
                            message['topic'],
                            message['payload'],
                            qos=message.get('qos', 1),
                            retain=message.get('retain', False),
                            timeout=message.get('timeout', 30),
                            retry_count=message.get('retry_count', 3)
                        )
                    else:
                        # If still not connected, put it back in the queue
                        self.message_queue.put(message)
                except queue.Empty:
                    # No message in the queue, just continue
                    pass
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                # Sleep a bit to avoid tight loop if there's a persistent error
                time.sleep(1.0)

    def _check_ack_timeouts(self):
        """Background thread that checks for message acknowledgment timeouts."""
        while not self.stop_event.is_set():
            try:
                with self.message_lock:
                    # Get current time
                    now = time.time()

                    # Check each pending message
                    for message_id in list(self.pending_messages.keys()):
                        message = self.pending_messages[message_id]
                        elapsed = now - message['timestamp']

                        # Check if the message has timed out
                        if elapsed > message['timeout']:
                            # Check if we should retry
                            if message['retries_left'] > 0:
                                # Retry the message
                                logger.warning(
                                    f"Message {message_id} timed out, retrying ({message['retries_left']} retries left)")
                                message['retries_left'] -= 1
                                message['timestamp'] = now

                                # Republish the message
                                self.client.publish(
                                    message['topic'],
                                    message['payload'],
                                    qos=message['qos'],
                                    retain=message['retain']
                                )
                            else:
                                # No more retries, remove the message
                                logger.error(
                                    f"Message {message_id} failed after all retries")
                                del self.pending_messages[message_id]

                # Sleep to avoid tight loop
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Error checking acknowledgment timeouts: {e}")
                # Sleep a bit to avoid tight loop if there's a persistent error
                time.sleep(1.0)

    def _handle_acknowledgment(self, payload):
        """Handle an acknowledgment message."""
        try:
            data = json.loads(payload)
            message_id = data.get('message_id')

            if message_id:
                with self.message_lock:
                    if message_id in self.pending_messages:
                        # Remove the message from pending
                        del self.pending_messages[message_id]
                        logger.debug(
                            f"Received acknowledgment for message {message_id}")
        except Exception as e:
            logger.error(f"Error handling acknowledgment: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback for when a message has been published."""
        logger.debug(f"Message {mid} published")

        # For QoS 0, we won't get an acknowledgment, so remove from pending
        with self.message_lock:
            if mid in self.pending_messages and self.pending_messages[mid]['qos'] == 0:
                del self.pending_messages[mid]
