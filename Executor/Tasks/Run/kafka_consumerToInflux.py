from kafka import KafkaConsumer
import json
from Helper import Level, influx
from Settings import KAFKAConfig
from .to_influx import ToInfluxBase
from datetime import datetime

class KafkaConsumerToInflux(ToInfluxBase):
    # Initialize the Task superclass with necessary parameters
    def __init__(self, logMethod, parent, params):
        super().__init__("KAFKA", parent, params, logMethod, None)
        # Define the rules for expected parameters, including which are mandatory
        self.paramRules = {
            'ExecutionId': (None, True), # Unique ID for execution, required
            'Ip': (None, True), # Kafka server IP address, required
            'Port': (None, True), # Kafka server port, required
            'Topic': (None, True), # Kafka topic to subscribe to, required
            'Measurement': (None, True), # InfluxDB measurement name, required
            'Stop': (None, True), # Stop signal key, required
            'Account': (False, True), # Account for authentication, required
            'GroupId': (None, False), # Kafka consumer group ID, optional
            'Certificates': (None, False), # Path to SSL certificates, optional
            'Encryption': (False, True),    # Flag for using SSL/TLS, required
            'Timestamp': ('timestamp', False), # The name of the timestamp for the metrics, optional
            'CSV': (False, False) # Flag to enable CSV export, optional.
        }

    def Run(self):
        # Extract necessary parameters from the params dictionary
        kafka = KAFKAConfig()
        info = kafka.user
        user = info.get("User", "")
        password = info.get("Password", "")
        executionId = self.params['ExecutionId']
        measurement = self.params["Measurement"]
        IP_host = self.params['Ip']
        PORT_host = self.params['Port']
        TOPIC_Host = self.params['Topic']
        stop = self.params['Stop']
        group_id_opt = self.params['GroupId']
        base_path = self.params.get('Certificates', "")
        encryption = self.params['Encryption']
        account = self.params['Account']
        timestamp_init=self.params.get('Timestamp')
        csv_init=self.params.get('CSV')

        # Create common arguments for KafkaConsumer
        consumer_args = {
            'bootstrap_servers': f"{IP_host}:{PORT_host}",
            'group_id': group_id_opt,
            'consumer_timeout_ms': 1000,
            'value_deserializer': (lambda x: json.loads(x.decode('utf-8'))) if not csv_init else (lambda x: x.decode('utf-8'))
        }

        # Initialize KafkaConsumer based on authentication and encryption configuration
        try:
            # Check if encryption and account are boolean values
            if not isinstance(encryption, bool) or not isinstance(account, bool):
                self.Log(Level.ERROR, "Exception creating KAFKA: Invalid type for encryption or account")
                self.SetVerdictOnError()
                return

            # Determine the security protocol and additional arguments based on conditions
            if encryption:
                consumer_args.update({
                    'ssl_check_hostname': True,
                    'ssl_cafile': base_path + "ca-cert.pem",
                    'ssl_certfile': base_path + "client-cert-signed.pem",
                    'ssl_keyfile': base_path + "client-key.pem",
                    'security_protocol': 'SASL_SSL' if account else 'SSL'
                })

            if account:
                consumer_args.update({
                    'sasl_plain_username': user,
                    'sasl_plain_password': password,
                    'sasl_mechanism': 'PLAIN',
                    'security_protocol': 'SASL_PLAINTEXT' if not encryption else consumer_args.get('security_protocol')
                })
            
            # Create the KafkaConsumer only once
            consumer = KafkaConsumer(TOPIC_Host, **consumer_args)
            self.Log(Level.INFO, f"KAFKA CONSUMER successfully connected")

        except Exception as e:
            self.Log(Level.ERROR, f"Exception creating KAFKA Consumer: {e}")
            self.SetVerdictOnError()
            return

        # Main loop for processing Kafka messages
        while not self.parent.ReadMilestone(stop) and not self.parent.stopRequested:
            # Consume messages from Kafka and send them to InfluxDB
            for message in consumer:
                try:
                    if not csv_init:
                        data = message.value
                        flattened_data = self._flatten_json(data,timestamp_key=timestamp_init)
                        for key, value, timestamp in flattened_data:
                            measurement_data = {key: value}
                            if not isinstance(timestamp, (int, float)):
                                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                timestamp = int(dt.timestamp())
                            # Send the flattened data to InfluxDB
                            self._send_to_influx(measurement, measurement_data, timestamp, executionId)
                    else:
                        csv_data = message.value.strip()
                        if not csv_data:
                            continue
                        self._send_to_influx_CSV(measurement,csv_data,executionId)
                    break        
                except Exception as e:
                    if isinstance(e, influx.InfluxDBError) and e.response.status == 422:
                        self.Log(Level.WARNING, f"Warning (KAFKA): Unprocessable entity (422). Invalid data: {data}")
                    else:
                        self.Log(Level.ERROR, f"Failed to send data to InfluxDB (KAFKA). Exception: {e}")
                        self.SetVerdictOnError()
                        raise RuntimeError(f"Exiting due to unexpected error: {e}")
                