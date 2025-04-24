"""
Main entry point for SenseBridge application.
Initializes and coordinates all system components.
"""

import logging
import threading
import time
import os
import signal
import sys
from .utils.logger import setup_logging
from .utils.config import Config
from .audio.sound_recognition import SoundRecognition
from .speech.speech_to_text import SpeechToText
from .notification.notification_manager import NotificationManager
from .hardware.device_control import DeviceController
from .hardware.wearable import WearableDevice
from .gui.app import create_app

# Global flag to signal program exit
running = True


class SenseBridge:
    """Main application class for SenseBridge."""

    def __init__(self, headless=False):
        """Initialize the SenseBridge application.

        Args:
            headless: Run in headless mode (no GUI)
        """
        # Set up logging
        self.logger = setup_logging()
        self.logger.info("Initializing SenseBridge...")

        # Load configuration
        self.config = Config()

        # Initialize components
        self.notification_manager = NotificationManager()
        self.sound_recognition = SoundRecognition(callback=self.on_sound_detected)
        self.speech_to_text = SpeechToText(text_callback=self.on_speech_recognized)
        self.device_controller = DeviceController()
        self.wearable = WearableDevice()

        # Create GUI app
        self.app = create_app(use_gui=not headless)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.logger.info("SenseBridge initialized")

    def start(self):
        """Start all SenseBridge components."""
        self.logger.info("Starting SenseBridge...")

        try:
            # Start notification system first
            self.notification_manager.start()

            # Start wearable device
            self.wearable.start()

            # Register button callback
            self.device_controller.set_button_callback(self.on_button_press)

            # Start speech-to-text
            self.speech_to_text.start()

            # Start sound recognition
            self.sound_recognition.start()

            # Show startup message
            self.app.show_notification("SenseBridge is ready!")
            self.app.update_status_message("System active")

            self.logger.info("SenseBridge started")

            # Start GUI main loop
            if isinstance(self.app.root, tk.Tk):
                self.logger.info("Starting GUI main loop")
                self.app.root.mainloop()
            else:
                # Headless mode - just keep running
                self.logger.info("Running in headless mode")
                while running:
                    time.sleep(1)

        except Exception as e:
            self.logger.error(f"Error starting SenseBridge: {str(e)}")
            self.stop()

    def stop(self):
        """Stop all SenseBridge components."""
        self.logger.info("Stopping SenseBridge...")

        # Stop components in reverse order
        self.sound_recognition.stop()
        self.speech_to_text.stop()
        self.wearable.stop()
        self.notification_manager.stop()

        # Clean up GPIO
        self.device_controller.cleanup()

        self.logger.info("SenseBridge stopped")

    def on_sound_detected(self, sound_type, confidence, audio_data):
        """Callback for when a sound is detected.

        Args:
            sound_type: Type of detected sound
            confidence: Detection confidence
            audio_data: Raw audio data
        """
        self.logger.info(f"Sound detected: {sound_type} (confidence: {confidence:.2f})")

        # Notify through the notification manager
        self.notification_manager.notify(sound_type, confidence, audio_data)

        # Update GUI
        self.app.show_notification(f"Detected: {sound_type.capitalize()}")
        self.app.update_status_message(f"Last event: {sound_type} ({confidence:.2f})")

    def on_speech_recognized(self, text):
        """Callback for when speech is recognized.

        Args:
            text: Recognized speech text
        """
        if text:
            self.logger.info(f"Speech recognized: {text}")

            # Notify through the notification manager
            self.notification_manager.notify("speech", 1.0, text)

            # Update GUI with speech text
            self.app.update_speech_text(text)

    def on_button_press(self):
        """Callback for when the button is pressed."""
        self.logger.info("Button pressed")

        # Trigger a test notification
        self.notification_manager.notify("doorbell", 1.0, None)

        # Update GUI
        self.app.show_notification("Button pressed")

    def signal_handler(self, sig, frame):
        """Handle termination signals for graceful shutdown.

        Args:
            sig: Signal number
            frame: Current stack frame
        """
        global running
        self.logger.info(f"Received signal {sig}, shutting down...")
        running = False

        # Stop all components
        self.stop()

        # Exit program
        sys.exit(0)


def main():
    """Main entry point for SenseBridge application."""
    # Check for headless mode
    headless = "--headless" in sys.argv

    # Create and start SenseBridge
    app = SenseBridge(headless=headless)
    app.start()


# Add to the main() function in src/main.py
def main():
    """Main entry point for SenseBridge application."""
    # Check for headless mode
    headless = "--headless" in sys.argv

    # Check for simulation mode
    simulation = "--simulation" in sys.argv

    # Check for timeout
    timeout = None
    for arg in sys.argv:
        if arg.startswith("--timeout="):
            try:
                timeout = float(arg.split("=")[1])
            except:
                pass

    # Create and start SenseBridge
    app = SenseBridge(headless=headless)

    try:
        app.start()

        # If timeout specified, run only for that duration
        if timeout:
            time.sleep(timeout)
            app.stop()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt")
        app.stop()

if __name__ == "__main__":
    main()