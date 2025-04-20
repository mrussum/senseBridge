"""
Unit tests for the notification module.
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from src.notification.notification_manager import NotificationManager
from src.notification.haptic_feedback import HapticFeedback
from src.notification.visual_notification import VisualNotification


class TestNotification:
    """Test cases for notification system."""

    @patch('src.notification.haptic_feedback.HapticFeedback')
    @patch('src.notification.visual_notification.VisualNotification')
    def test_notification_manager(self, mock_visual, mock_haptic):
        """Test notification manager functionality."""
        # Create mock objects
        haptic_mock = MagicMock()
        visual_mock = MagicMock()

        # Setup mock returns
        mock_haptic.return_value = haptic_mock
        mock_visual.return_value = visual_mock

        # Create notification manager
        manager = NotificationManager()

        # Override internal objects with mocks
        manager.haptic = haptic_mock
        manager.visual = visual_mock

        # Override notification configuration
        manager.haptic_enabled = True
        manager.visual_enabled = True

        # Start manager
        manager.start()

        # Test notification
        manager.notify("doorbell", 0.9)

        # Wait for notification to be processed
        time.sleep(0.5)

        # Check that haptic and visual notifications were triggered
        haptic_mock.send_feedback.assert_called()
        visual_mock.show_notification.assert_called()

        # Stop manager
        manager.stop()

    def test_speech_notification(self):
        """Test speech notification handling."""
        # Create notification manager
        manager = NotificationManager()

        # Create mock for visual notification
        visual_mock = MagicMock()
        manager.visual = visual_mock
        manager.visual_enabled = True

        # Start manager
        manager.start()

        # Test speech notification
        test_text = "This is a test message"
        manager.notify("speech", 1.0, test_text)

        # Wait for notification to be processed
        time.sleep(0.5)

        # Check that text was displayed
        visual_mock.show_text.assert_called_with(test_text)

        # Stop manager
        manager.stop()

    def test_duplicate_suppression(self):
        """Test suppression of duplicate notifications."""
        # Create notification manager
        manager = NotificationManager()

        # Create mock for haptic feedback
        haptic_mock = MagicMock()
        manager.haptic = haptic_mock
        manager.haptic_enabled = True

        # Start manager
        manager.start()

        # Send initial notification
        manager.notify("doorbell", 0.9)

        # Wait for processing
        time.sleep(0.5)

        # Reset mock call count
        haptic_mock.send_feedback.reset_mock()

        # Send duplicate notification
        manager.notify("doorbell", 0.9)

        # Wait for processing
        time.sleep(0.5)

        # Check that duplicate was suppressed (haptic not called)
        haptic_mock.send_feedback.assert_not_called()

        # Wait for deduplication timeout
        time.sleep(3.0)

        # Send notification again
        manager.notify("doorbell", 0.9)

        # Wait for processing
        time.sleep(0.5)

        # Check that notification was sent after timeout
        haptic_mock.send_feedback.assert_called()

        # Stop manager
        manager.stop()

    def test_priority_handling(self):
        """Test priority-based notification handling."""
        # Create notification manager
        manager = NotificationManager()

        # Create mock sound events with different priorities
        manager.sound_events = {
            "doorbell": {
                "label": "Doorbell",
                "priority": "high",
                "haptic_pattern": "long_double",
                "visual_pattern": "flash_bright"
            },
            "microwave_beep": {
                "label": "Microwave",
                "priority": "low",
                "haptic_pattern": "short_double",
                "visual_pattern": "flash_low"
            }
        }

        # Create mock for haptic feedback
        haptic_mock = MagicMock()
        manager.haptic = haptic_mock
        manager.haptic_enabled = True

        # Start manager
        manager.start()

        # Send high priority notification
        manager.notify("doorbell", 0.9)

        # Wait for processing
        time.sleep(0.5)

        # Check haptic pattern for high priority
        call_args = haptic_mock.send_feedback.call_args[0]
        assert call_args[0] == "long_double"
        assert call_args[1] == "high"

        # Reset mock
        haptic_mock.send_feedback.reset_mock()

        # Send low priority notification
        manager.notify("microwave_beep", 0.9)

        # Wait for processing
        time.sleep(0.5)

        # Check haptic pattern for low priority
        call_args = haptic_mock.send_feedback.call_args[0]
        assert call_args[0] == "short_double"
        assert call_args[1] == "low"

        # Stop manager
        manager.stop()