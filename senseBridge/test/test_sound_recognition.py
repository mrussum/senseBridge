"""
Unit tests for the sound recognition module.
"""

import pytest
import numpy as np
import time
import threading
from src.audio.sound_recognition import SoundRecognition
from src.models.sound_classifier import SoundClassifier


class TestSoundRecognition:
    """Test cases for sound recognition."""

    def test_initialization(self):
        """Test initialization of sound recognition."""
        recognition = SoundRecognition()
        assert recognition is not None
        assert recognition.sensitivity > 0
        assert recognition.min_confidence > 0

    def test_callback(self):
        """Test callback functionality."""
        # Create a flag to track callback execution
        callback_executed = threading.Event()
        result = {}

        def test_callback(sound_type, confidence, audio_data):
            result['sound_type'] = sound_type
            result['confidence'] = confidence
            result['audio_data'] = audio_data
            callback_executed.set()

        # Initialize with test callback
        recognition = SoundRecognition(callback=test_callback)

        # Mock the audio processor and classifier for testing
        recognition.audio_processor.get_audio_data = lambda: np.random.normal(0, 1000, 1024).astype(np.float32)

        # Override classifier to always return "doorbell"
        def mock_classify(self, audio_data):
            return "doorbell", 0.95

        original_classify = SoundClassifier.classify_sound
        SoundClassifier.classify_sound = mock_classify

        try:
            # Start recognition
            recognition.start()

            # Wait for callback to be executed
            callback_executed.wait(timeout=5.0)

            # Stop recognition
            recognition.stop()

            # Check results
            assert callback_executed.is_set(), "Callback was not executed"
            assert result['sound_type'] == "doorbell"
            assert result['confidence'] >= 0.9
            assert isinstance(result['audio_data'], np.ndarray)

        finally:
            # Restore original method
            SoundClassifier.classify_sound = original_classify

    def test_ambient_adjustment(self):
        """Test ambient noise adjustment."""
        recognition = SoundRecognition()

        # Set a known ambient level
        recognition.ambient_level = 0.1

        # Add some samples to the window
        recognition.ambient_samples = [0.1, 0.2, 0.1, 0.12, 0.09]

        # Update with a new level
        recognition._update_ambient_level(0.15)

        # Check that the ambient samples list was updated
        assert len(recognition.ambient_samples) == 6
        assert recognition.ambient_samples[-1] == 0.15

        # Calculate expected median
        expected_median = np.median([0.1, 0.2, 0.1, 0.12, 0.09, 0.15])

        # Check that the ambient level was updated correctly
        assert recognition.ambient_level == expected_median

    def test_detection_threshold(self):
        """Test detection threshold based on sensitivity."""
        recognition = SoundRecognition()

        # Set a known ambient level
        recognition.ambient_level = 0.1

        # Test with different sensitivity levels
        recognition.sensitivity = 0.5
        threshold_low = recognition.ambient_level * (1.0 + 5.0 * recognition.sensitivity)

        recognition.sensitivity = 1.0
        threshold_high = recognition.ambient_level * (1.0 + 5.0 * recognition.sensitivity)

        # Higher sensitivity should result in a lower threshold
        assert threshold_high > threshold_low