""" 
MQTTBuzz is a user-friendly application that allows you to connect to multiple MQTT brokers 
and receive notifications based on the messages published to specific topics. 
"""

# pylint: disable=import-error, too-many-instance-attributes, invalid-sequence-index, broad-exception-caught, unused-argument, unused-variable, too-many-arguments

# System Libraries
import json
import os
import threading
import time

# Third Party Libraries
import paho.mqtt.client as mqtt
import rumps

# Path to the configuration and help files
CONFIG_FILE = "config.json"
HELP_FILE = "help.txt"

class MQTTBuzzApp(rumps.App):
    """ 
    The main Ridiculously Uncomplicated macOS Python Statusbar apps (rumps) class
    This allows a Python script to present as a simple dropdown menu in the OSX toolbar
    For further details see: https://github.com/jaredks/rumps
    """

    def __init__(self):
        """
        Initialize variables and configuration options then connect
        """

        # Define the application name
        self.app_name = "MQTTBuzz"
        super().__init__(self.app_name)

        # Load the configuration
        self.config = self.load_config()

        # Store MQTT clients for potential disconnect
        self.mqtt_clients = []

        # Store connection state
        self.connected = False

        # Store the last messages and timestamps for filtering
        self.last_messages = {}       # To store last message per broker
        self.last_message_times = {}  # To store last message time per broker

        # Create the toolbar menu
        self.menu = ["Connect to MQTT", "Help", "Settings",  "Sound On/Off"]

        # Set initial state for sound
        self.sounds_enabled = self.config.get("sounds_enabled", True)

        # Initialize sound toggle menu
        self.menu["Sound On/Off"].state = self.sounds_enabled

        # Read help text from file
        self.help_text = self.load_help_text()

        # Connect to MQTT brokers at startup

        # Start MQTT clients
        self.connect_to_mqtt()
        self.connected = True
        self.menu["Connect to MQTT"].title = "Disconnect from MQTT"

    def load_config(self):
        """ 
        Read the configuration file if it exists
        If it doesn't then create a default file and use that instead
        """

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as file:
                return json.load(file)
        else:
            default_config = {
                "mqtt_servers": [
                    {
                        "mqtt_broker": "broker1_address",
                        "mqtt_port": 1883,
                        "mqtt_topic": "topic1",
                        "username": "your_username",
                        "password": "your_password",
                        "header": None,  # Default to broker name if not specified
                        "subheader": None,  # Default to topic if not specified
                        "broker_enabled": True,  # Default broker to enabled
                        "sounds_enabled": True,  # Default broker to enabled
                        "filter": "none",  # No filtering by default
                        "filter_time": 0  # No filter time by default
                    }
                ],
                "sounds_enabled": True,  # Default sound setting to enabled
                "max_message_length": 256 # Maximum message legth
            }
            self.save_config(default_config)
            return default_config

    def save_config(self, config_data):
        """
        Write out an updated version of the config file
        """

        with open(CONFIG_FILE, 'w', encoding="utf-8") as file:
            json.dump(self.config, file, indent=4)

    def load_help_text(self):
        """
        Load the help text from the help.txt file.
        """

        if os.path.exists(HELP_FILE):
            with open(HELP_FILE, 'r', encoding="utf-8") as file:
                return file.read()
        else:
            default_help_text = "This is the MQTTBuzz app. Configure your MQTT settings."
            with open(HELP_FILE, 'w', encoding="utf-8") as file:
                file.write(default_help_text)
            return default_help_text

    def toggle_connect(self, sender):
        """
        Toggle the connection state between connect and disconnect.
        """

        if self.connected:
            self.disconnect_mqtt_clients()
            sender.title = "Connect to MQTT"
            self.connected = False
        else:
            self.connect_to_mqtt()
            sender.title = "Disconnect from MQTT"
            self.connected = True

    def toggle_sound(self, sender):
        """
        Toggle the sound setting on or off.
        """

        self.sounds_enabled = not self.sounds_enabled
        self.config["sounds_enabled"] = self.sounds_enabled
        sender.state = self.sounds_enabled
        self.save_config(self.config)
        self.notify_with_sound(self.app_name,
            f"Sounds {'enabled' if self.sounds_enabled else 'disabled'}.")

    def connect_to_mqtt(self):
        """
        Connect to all enabled MQTT brokers.
        """

        # Disconnect any existing MQTT clients
        self.disconnect_mqtt_clients()

        # Start new MQTT clients based on the current configuration
        for server in self.config["mqtt_servers"]:
            # Check if the server is enabled
            if server.get("broker_enabled", False):
                mqtt_thread = threading.Thread(target=self.start_mqtt_client, args=(server,))
                mqtt_thread.daemon = True
                mqtt_thread.start()

        self.notify_with_sound(self.app_name, "Attempting to connect to MQTT brokers")

    def disconnect_mqtt_clients(self):
        """
        Disconnect from all MQTT brokers.
        """

        for client in self.mqtt_clients:
            client.disconnect()
        self.mqtt_clients = []

    def start_mqtt_client(self, server):
        """ 
        Start a new client for each broker
        """

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        # Set username and password if provided
        if "username" in server and "password" in server:
            client.username_pw_set(server["username"], server["password"])

        # Assigning userdata so that we can access server configuration in callbacks
        client.user_data_set(server)

        # Assigning callbacks using the new API
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            client.connect(server["mqtt_broker"], server["mqtt_port"], 60)
            client.loop_start()  # Use loop_start instead of loop_forever to allow disconnects
            self.mqtt_clients.append(client)
        except Exception as e:
            self.notify_with_sound(f"MQTT Connection Failed ({server['mqtt_broker']})", str(e))

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """ 
        Connect to a broker and topic 
        """

        header = userdata.get("header", userdata["mqtt_broker"])
        subheader = userdata.get("subheader", userdata["mqtt_topic"])

        if rc == 0:
            self.notify_with_sound(self.app_name,
                f"Successfully connected to {header}:{subheader}")
            client.subscribe(userdata["mqtt_topic"])
        else:
            self.notify_with_sound(self.app_name,
                f"Failed to connect to {header}:{subheader} with result code {rc}")

    def on_message(self, client, userdata, msg):
        """
        When a message is received send to notifications
        """

        broker = userdata["mqtt_broker"]
        topic = userdata["mqtt_topic"]
        message = msg.payload.decode()
        filter_type = userdata.get("filter", "none")
        filter_time = userdata.get("filter_time", 0)

        current_time = time.time()

        # Handle filtering logic
        if filter_type == "none":
            # No filtering, always send notification
            self.send_notification(userdata, message)
        elif filter_type == "dedup":
            # Deduplicate messages
            last_message = self.last_messages.get(broker)
            last_time = self.last_message_times.get(broker, 0)
            if last_message != message or (current_time - last_time) > filter_time:
                self.send_notification(userdata, message)
                self.last_messages[broker] = message
                self.last_message_times[broker] = current_time
        elif filter_type == "throttle":
            # Throttle messages
            last_time = self.last_message_times.get(broker, 0)
            if (current_time - last_time) > filter_time:
                self.send_notification(userdata, message)
                self.last_message_times[broker] = current_time

    def send_notification(self, userdata, message):
        """
        Format payload message
        """

        header = userdata.get("header", userdata["mqtt_broker"])
        subheader = userdata.get("subheader", userdata["mqtt_topic"])
        
        # Truncate the message if it's longer than the configured max length
        if len(message) > self.config.get("max_message_length",256):
            message = message[:self.config["max_message_length"]] 

        self.notify_with_sound(header, message, subheader=subheader,
            sounds=userdata.get("sounds_enabled", True))

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        """ 
        Handle disconnection from brokers and topics
        """

        header = userdata.get("header", userdata["mqtt_broker"])
        subheader = userdata.get("subheader", userdata["mqtt_topic"])

        self.notify_with_sound(self.app_name, f"Disconnected from {header}:{subheader}")

    def notify_with_sound(self, header, message, subheader=None, sounds=True):
        """
        Call the Apple Notification sub-ssutem
        """

        # Send notification with an optional sound and subheader
        subtitle = subheader if subheader else ""
        sounds = sounds and self.sounds_enabled
        rumps.notification(title=header, subtitle=subtitle, message=message, sound=sounds)

    @rumps.clicked("Settings")
    def settings(self, _):
        """
        Handle user defined settings
        """

        response = rumps.Window(
            message="Edit MQTT Settings",
            title="Settings",
            default_text=json.dumps(self.config, indent=4),
            dimensions=(480, 400)
        ).run()

        if response.clicked:
            try:
                new_config = json.loads(response.text)
                self.config = new_config
                self.save_config(self.config)
                self.notify_with_sound(self.app_name, "The configuration has been updated.")
                # Reconnect with the new configuration
                self.connect_to_mqtt()
            except json.JSONDecodeError:
                self.notify_with_sound(self.app_name,
                    "The settings you entered are not valid JSON.")
            except Exception as e:
                self.notify_with_sound(self.app_name, str(e))

    @rumps.clicked("Help")
    def help(self, _):
        """
        Show a help dialog with text from the help.txt file
        """

        rumps.Window(
            title="Help",
            message=self.help_text,
            dimensions=(0, 0)
        ).run()

if __name__ == "__main__":
    app = MQTTBuzzApp()
    # Modify the Connect to MQTT menu item to act as a toggle
    app.menu["Connect to MQTT"].set_callback(app.toggle_connect)
    # Modify the Sound On/Off menu item to act as a toggle
    app.menu["Sound On/Off"].set_callback(app.toggle_sound)
    app.run()
