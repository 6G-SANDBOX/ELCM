import paho.mqtt.client as mqtt
import json
from Helper import utils, Level
from Settings import MQTTConfig
from .to_influx import ToInfluxBase
import time
class MqttToInflux(ToInfluxBase):

    def __init__(self, logMethod, parent, params):
        # Initialize the Task superclass with necessary parameters
        super().__init__("MQTT", parent, params, logMethod, None)
        # Define the rules for expected parameters, including which are mandatory
        self.paramRules = {
            'ExecutionId': (None, True),   # Unique ID for execution, required
            'Broker': (None, True),         # MQTT broker address, required
            'Port': (None, True),           # MQTT broker port, required
            'Account': (False, True),       # Account for authentication, required
            'Topic': (None, True),          # MQTT topic to subscribe to, required
            'Stop': (None, True),           # Stop signal key, required
            'Measurement': (None, True),    # InfluxDB measurement name, required
            'Certificates': (None, False),  # Path to SSL certificates, optional
            'Encryption': (False, True)     # Flag for using SSL/TLS, required
        }

    def save_to_influx(self, message):
        # Decode and parse the MQTT message payload
        data = json.loads(message.payload.decode('utf-8'))
        measurement = self.params['Measurement']
        # Flatten the data before sending to InfluxDB
        flattened_data = self._flatten_json(data)

        for key, value, timestamp in flattened_data:
            # Convert integer values to float
            if isinstance(value, int):
                value = float(value)
            measurement_data = {key: value}

            try:
                # Send the flattened data to InfluxDB
                self._send_to_influx(measurement, measurement_data, timestamp, self.params['ExecutionId'])
            except Exception as e:
                self.Log(Level.ERROR, f"Exception consuming MQTT messages: {e}")
                self.SetVerdictOnError()
                raise SystemExit("Terminating the program due to a critical error.")

    # Callback function when the client successfully connects to the MQTT broker
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.Log(Level.INFO, f"Successfully connected to the broker")
            client.subscribe(self.params['Topic'])
        else:
            self.Log(Level.INFO, f"Connection failed, return code: {rc}")

    # Callback function when a message is received from the MQTT broker
    def on_message(self, client, userdata, msg):
        self.save_to_influx(msg)  # Save the message to InfluxDB

    def Run(self):
        client = mqtt.Client()
        # Extract necessary parameters from the params dictionary
        mqtt_info = MQTTConfig()
        info = mqtt_info.user
        user = info.get("User", None)
        password = info.get("Password", None)
        executionId = self.params['ExecutionId']
        broker = self.params['Broker']
        port = int(self.params['Port'])
        stop = self.params['Stop'] + "_" + str(executionId)
        base_path = self.params['Certificates']
        encryption = self.params['Encryption']
        account = self.params['Account']

        # Configure TLS/SSL and authentication if required
        if not isinstance(encryption, bool) or not isinstance(account, bool):
            self.Log(Level.ERROR, "Exception creating MQTT: Invalid type for encryption or account")
            return

        # Prepare MQTT client for connection based on encryption and account conditions
        tls_args = {
            'ca_certs': base_path + "ca.pem",
            'certfile': base_path + "client-cert.pem",
            'keyfile': base_path + "client-key.pem"
        } if encryption else {}

        if account:
            client.username_pw_set(user, password)

        if encryption:
            client.tls_set(**tls_args)

        # Set the callback methods for connection and message events
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        try:
            client.connect(broker, port, 60)
            self.Log(Level.INFO, f"MQTT successfully connected")
        except Exception as e:
            self.Log(Level.ERROR, f"Exception connecting to MQTT: {e}")
            self.SetVerdictOnError()
            return
        
        # Start the MQTT client's network loop
        client.loop_start()
        
        # Main loop to check for a stop signal from the control queue
        while stop not in utils.task_list:
            time.sleep(1)
        utils.task_list.remove(stop)
        # Stop the MQTT client's network loop and disconnect
        client.loop_stop()
        client.disconnect()