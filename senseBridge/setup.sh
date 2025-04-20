#!/bin/bash

echo "Setting up SenseBridge Environment..."

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p config
mkdir -p models/yamnet_model
mkdir -p logs

# Download pre-trained YAMNet model for sound classification
echo "Downloading YAMNet model..."
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/yamnet/yamnet.tflite -O models/yamnet_model/yamnet.tflite
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/yamnet/yamnet_label_list.txt -O models/yamnet_model/yamnet_labels.txt

# Create default configuration files
echo "Creating default configuration files..."
cat > config/device_config.json << EOL
{
    "audio": {
        "sample_rate": 16000,
        "chunk_size": 1024,
        "channels": 1
    },
    "hardware": {
        "haptic_pin": 18,
        "led_pin": 23,
        "button_pin": 24
    },
    "bluetooth": {
        "device_name": "SenseBridge",
        "wearable_mac": ""
    }
}
EOL

cat > config/sound_events.json << EOL
{
    "doorbell": {
        "label": "Doorbell",
        "priority": "high",
        "haptic_pattern": "long_double",
        "visual_pattern": "flash_bright"
    },
    "knock": {
        "label": "Knock, knock",
        "priority": "high",
        "haptic_pattern": "short_triple",
        "visual_pattern": "flash_medium"
    },
    "microwave_beep": {
        "label": "Microwave",
        "priority": "medium",
        "haptic_pattern": "short_double",
        "visual_pattern": "flash_low"
    },
    "alarm": {
        "label": "Alarm",
        "priority": "high",
        "haptic_pattern": "continuous",
        "visual_pattern": "flash_urgent"
    }
}
EOL

cat > config/user_prefs.json << EOL
{
    "notifications": {
        "haptic": true,
        "visual": true,
        "smart_home": false
    },
    "speech_to_text": {
        "enabled": true,
        "continuous_mode": true,
        "display_timeout": 30
    },
    "sound_detection": {
        "sensitivity": 0.7,
        "min_confidence": 0.6,
        "ambient_adjustment": true
    },
    "smart_home": {
        "mqtt_broker": "",
        "mqtt_port": 1883,
        "mqtt_username": "",
        "mqtt_password": "",
        "light_topic": "senseBridge/lights"
    }
}
EOL

echo "SenseBridge setup complete! Activate the environment with:"
echo "source .venv/bin/activate"