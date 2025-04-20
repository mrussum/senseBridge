"""
Wearable device communication for SenseBridge.
Manages Bluetooth communication with wearable devices.
"""

import logging
import threading
import time
import json
import queue
from ..utils.config import Config

logger = logging.getLogger(__name__)

# Check if Bluetooth is available
try:
    import bluetooth

    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False
    logger.warning("Bluetooth module not available - running in simulation mode")


class WearableDevice:
    """Manages communication with wearable Bluetooth devices."""

    def __init__(self):
        """Initialize the wearable device manager."""
        self.config = Config()
        self.device_config = self.config.get_device_config()
        self.bluetooth_config = self.device_config["bluetooth"]

        self.device_name = self.bluetooth_config["device_name"]
        self.wearable_mac = self.bluetooth_config.get("wearable_mac", "")

        self.socket = None
        self.connected = False
        self.running = False

        # Command queue for sending commands to wearable
        self.command_queue = queue.Queue()

        # Threads for communication
        self.send_thread = None
        self.receive_thread = None

        # Callback for received messages
        self.message_callback = None

        logger.info("WearableDevice initialized")

    def start(self):
        """Start wearable device communication."""
        if self.running:
            logger.warning("Wearable device already running")
            return False

        self.running = True

        # Start communication threads if Bluetooth is available
        if BLUETOOTH_AVAILABLE and self.wearable_mac:
            # Start connection thread
            connect_thread = threading.Thread(target=self._connect_and_start_threads)
            connect_thread.daemon = True
            connect_thread.start()
            logger.info("Wearable device communication started")
            return True
        else:
            logger.warning("Bluetooth not available or no wearable MAC configured")
            return False

    def stop(self):
        """Stop wearable device communication."""
        if not self.running:
            return

        self.running = False

        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        # Wait for threads to stop
        if self.send_thread:
            self.send_thread.join(timeout=2.0)

        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)

        self.connected = False
        logger.info("Wearable device communication stopped")

    def send_command(self, command, params=None):
        """Send a command to the wearable device.

        Args:
            command: Command name
            params: Command parameters

        Returns:
            True if command was queued, False otherwise
        """
        if not self.running:
            logger.warning("Cannot send command - wearable device not running")
            return False

        # Create command message
        message = {
            "cmd": command,
            "params": params or {}
        }

        # Add to command queue
        self.command_queue.put(message)
        logger.debug(f"Command queued: {command}")
        return True

    def set_message_callback(self, callback):
        """Set callback function for received messages.

        Args:
            callback: Function to call when a message is received
        """
        self.message_callback = callback
        logger.debug("Message callback set")

    def _connect_and_start_threads(self):
        """Connect to wearable device and start communication threads."""
        # Try to connect
        if self._connect():
            # Start send and receive threads
            self.send_thread = threading.Thread(target=self._send_loop)
            self.send_thread.daemon = True
            self.send_thread.start()

            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            logger.info("Wearable device communication threads started")
        else:
            # Retry connection after delay
            if self.running:
                logger.debug("Retrying connection in 10 seconds")
                threading.Timer(10.0, self._connect_and_start_threads).start()

    def _connect(self):
        """Connect to the wearable device.

        Returns:
            True if connected, False otherwise
        """
        if not BLUETOOTH_AVAILABLE or not self.wearable_mac:
            return False

        try:
            logger.info(f"Connecting to wearable at {self.wearable_mac}...")

            # Scan for nearby devices (to check if wearable is available)
            nearby_devices = bluetooth.discover_devices(duration=2, lookup_names=True)
            device_found = any(addr == self.wearable_mac for addr, name in nearby_devices)

            if not device_found:
                logger.warning(f"Wearable device {self.wearable_mac} not found nearby")
                return False

            # Create socket and connect
            self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.socket.connect((self.wearable_mac, 1))  # RFCOMM channel 1

            self.connected = True
            logger.info("Connected to wearable device")
            return True

        except Exception as e:
            logger.error(f"Error connecting to wearable: {str(e)}")
            self.socket = None
            self.connected = False
            return False

    def _send_loop(self):
        """Main loop for sending commands to wearable."""
        while self.running and self.connected:
            try:
                # Get next command from queue with timeout
                try:
                    message = self.command_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Send command
                if self.socket and self.connected:
                    self._send_message(message)
                else:
                    # Re-queue command
                    self.command_queue.put(message)
                    break  # Exit thread if not connected

            except Exception as e:
                logger.error(f"Error in send loop: {str(e)}")
                self.connected = False
                break

    def _receive_loop(self):
        """Main loop for receiving messages from wearable."""
        while self.running and self.connected:
            try:
                if self.socket:
                    # Set socket timeout
                    self.socket.settimeout(1.0)

                    # Receive data
                    data = self.socket.recv(1024)

                    if data:
                        # Process received data
                        self._process_received_data(data)
                    else:
                        # Empty data means disconnection
                        logger.warning("Wearable device disconnected")
                        self.connected = False
                        break
                else:
                    break  # Exit thread if socket is None

            except bluetooth.btcommon.BluetoothError as e:
                # Ignore timeout errors
                if "timed out" not in str(e):
                    logger.error(f"Bluetooth error: {str(e)}")
                    self.connected = False
                    break

            except Exception as e:
                logger.error(f"Error in receive loop: {str(e)}")
                self.connected = False
                break

    def _send_message(self, message):
        """Send a message to the wearable device.

        Args:
            message: Message to send (will be converted to JSON)

        Returns:
            True if sent, False otherwise
        """
        try:
            # Convert message to JSON
            json_data = json.dumps(message) + "\n"

            # Send data
            self.socket.send(json_data.encode())
            logger.debug(f"Sent: {message['cmd']}")
            return True

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            self.connected = False
            return False

    def _process_received_data(self, data):
        """Process data received from wearable device.

        Args:
            data: Received data
        """
        try:
            # Decode data
            data_str = data.decode().strip()

            # Parse JSON
            message = json.loads(data_str)

            logger.debug(f"Received: {data_str}")

            # Call callback if set
            if self.message_callback:
                self.message_callback(message)

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {data}")

        except Exception as e:
            logger.error(f"Error processing received data: {str(e)}")