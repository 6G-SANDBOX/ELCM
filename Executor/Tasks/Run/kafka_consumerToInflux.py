from Task import Task
from kafka import KafkaConsumer
import json
from Helper import utils, Level
from Settings import KAFKAConfig

class KafkaConsummerToInflux(Task):
    # Initialize the Task superclass with necessary parameters
    def __init__(self, logMethod, parent, params):
        super().__init__("KAFKA", parent, params, logMethod, None)
        # Define the rules for expected parameters, including which are mandatory
        self.paramRules = {
            'ExecutionId': (None, True), # Unique ID for execution, required
            'IP': (None, True), # Kafka server IP address, required
            'PORT': (None, True), # Kafka server port, required
            'TOPIC': (None, True), # Kafka topic to subscribe to, required
            'MEASUREMENT': (None, True), # InfluxDB measurement name, required
            'STOP': (None, True), # Stop signal key, required
            'ACCOUNT': (False, True), # Account for authentication, required
            'GROUP_ID': (None, False), # Kafka consumer group ID, optional
            'CERTIFICATES': (None, False), # Path to SSL certificates, optional
            'ENCRYPTION': (False, True)    # Flag for using SSL/TLS, required
        }

    def Run(self):
        # Extract necessary parameters from the params dictionary
        kafka = KAFKAConfig()
        info = kafka.user
        user = info.get("User", None)
        password = info.get("Password", None)
        executionId = self.params['ExecutionId']
        measurement = self.params["MEASUREMENT"]
        IP_host = self.params['IP']
        PORT_host = self.params['PORT']
        TOPIC_Host = self.params['TOPIC']
        stop = self.params['STOP'] + "_" + str(executionId)
        group_id_opt = self.params['GROUP_ID']
        base_path = self.params['CERTIFICATES']
        encryption = self.params['ENCRYPTION']
        account = self.params['ACCOUNT']

        # Create common arguments for KafkaConsumer
        consumer_args = {
            'bootstrap_servers': f"{IP_host}:{PORT_host}",
            'group_id': group_id_opt,
            'consumer_timeout_ms': 1000,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8'))
        }

        # Initialize KafkaConsumer based on authentication and encryption configuration
        try:
            # Check if encryption and account are boolean values
            if not isinstance(encryption, bool) or not isinstance(account, bool):
                self.Log(Level.ERROR, "Exception creating KAFKA: Invalid type for encryption or account")
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
        while stop not in utils.task_list:
            # Consume messages from Kafka and send them to InfluxDB
            for message in consumer:
                try:
                    data = message.value
                    flattened_data = utils.flatten_json(data)
                    for key, value, timestamp in flattened_data:
                        # Convert integer values to float
                        if isinstance(value, int):
                            value = float(value)
                        measurement_data = {key: value}
                        # Send the flattened data to InfluxDB
                        utils.send_to_influx(measurement, measurement_data, timestamp, executionId)
                    break
                except Exception as e:
                    self.Log(Level.ERROR, f"Exception consuming KAFKA messages: {e}")
                    self.SetVerdictOnError()
                    return
        utils.task_list.remove(stop)