from prometheus_api_client import PrometheusConnect
from Helper import Level, influx
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from Settings import PROMETHEUSConfig
from .to_influx import ToInfluxBase
import time

class PrometheusToInflux(ToInfluxBase):

    def __init__(self, logMethod, parent, params):
        super().__init__("PROMETHEUS", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),
            'Url': (None, True),
            'Port': (None, True),
            'QueriesRange': (None, False),
            'QueriesCustom': (None, False),
            'Measurement': (None, True),
            'Stop': (None, True),
            'Step': (None, True),
            'Account': (False, True),
            'Certificates': (None, False),
            'Encryption': (False, True)
        }

    def init_prometheus_session(self, URL_host, PORT_host, base_path, encryption, account, user, password):
        try:
            # Validate encryption and account types
            if not isinstance(encryption, bool) or not isinstance(account, bool):
                self.Log(Level.ERROR, "Exception creating PROMETHEUS: Invalid type for encryption or account")
                return
            
            # Construct the base URL
            url = f"{'https' if encryption else 'http'}://{URL_host}:{PORT_host}"
            session = requests.Session()

            # Set up session authentication and certificate paths based on conditions
            session.cert = (base_path + 'client-cert.pem', base_path + 'client-key.pem') if encryption else None
            session.verify = base_path + 'ca.pem' if encryption else None
            session.auth = HTTPBasicAuth(user, password) if account else None
            
            return {'url': url, 'session': session}
        except Exception as e:
            self.Log(Level.ERROR, f"Error initializing Prometheus session: {e}")
            return None

    def process_range_queries(self, prometheus, queries_range, start_time, end_time, step, data_dict):
        for query in queries_range:
            try:
                data = prometheus.custom_query_range(
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                    step=step
                )
                if data:
                    self.Log(Level.INFO, f"Range query executed successfully: {query}")
                    self.store_query_data(data, query, data_dict)
                else:
                    self.Log(Level.WARNING, f"Range query was not executed successfully: {query}")

            except Exception as e:
                self.Log(Level.ERROR, f"Error executing range query '{query}': {e}")
                continue

    def process_custom_queries(self, prometheus, queries_custom, data_dict):
        for query in queries_custom:
            try:
                data = prometheus.custom_query(query=query)
                if data:
                    self.Log(Level.INFO, f"Custom query executed successfully: {query}")
                    self.store_query_data(data, query, data_dict)
                else:
                    self.Log(Level.WARNING, f"Custom query was not executed successfully: {query}")
                    
            except Exception as e:
                self.Log(Level.ERROR, f"Error executing custom query '{query}': {e}")
                continue

    def store_query_data(self, data, query, data_dict):
        for result in data:
            entries = result.get('values') or [result.get('value')]
            if not entries:
                continue  

            for entry in entries:
                timestamp = int(entry[0])
                value = entry[1]

                if timestamp not in data_dict:
                    data_dict[timestamp] = {query: value}
                else:
                    data_dict[timestamp][query] = value

    def send_data_to_influx(self, data_dict, measurement, executionId):
        for timestamp, data in data_dict.items():
            flat_data = self._flatten_prometheus_json(data)
            try:
                self._send_to_influx(measurement, flat_data, timestamp, executionId)
            except Exception as e:
                if isinstance(e, influx.InfluxDBError) and e.response.status == 422:
                    self.Log(Level.WARNING, f"Warning (PROMETHEUS): Unprocessable entity (422). Invalid data: {data}")
                else:
                    self.Log(Level.ERROR, f"Failed to send data to InfluxDB (PROMETHEUS). Exception: {e}")
                    raise RuntimeError(f"Exiting due to unexpected error: {e}")

    def Run(self):
        executionId = self.params['ExecutionId']
        URL_host = self.params['Url']
        PORT_host = self.params['Port']
        queries_range = self.params['QueriesRange']
        queries_custom = self.params['QueriesCustom']
        start_time = datetime.now()
        stop = self.params['Stop']
        step = self.params['Step']
        measurement = self.params['Measurement']
        base_path = self.params.get('Certificates', "")
        encryption = self.params['Encryption']
        prometheus_info = PROMETHEUSConfig()
        info = prometheus_info.user
        user = info.get("User", "")
        password = info.get("Password", "")
        account = self.params['Account']

        # Initialize the Prometheus session
        session = self.init_prometheus_session(URL_host, PORT_host, base_path, encryption, account, user, password)

        if session is None:
            self.Log(Level.ERROR, "Failed to initialize Prometheus session")
            self.SetVerdictOnError()
            return

        prometheus = PrometheusConnect(url=session['url'], session=session['session'])

        if not prometheus.check_prometheus_connection():
            self.Log(Level.ERROR, "Failed to connect to Prometheus")
            self.SetVerdictOnError()
            return
         
        self.Log(Level.INFO, f"Connected to Prometheus at {URL_host}:{PORT_host}")
        
        while not self.parent.ReadMilestone(stop) and not self.parent.stopRequested:
            time.sleep(1)
        end_time = datetime.now()

        # Process both range and custom queries
        data_dict = {}

        if queries_range is not None:
            self.process_range_queries(prometheus, queries_range, start_time, end_time, step, data_dict)

        if queries_custom is not None:
            self.process_custom_queries(prometheus, queries_custom, data_dict)

        if queries_range is not None or queries_custom is not None:
            self.send_data_to_influx(data_dict, measurement, executionId)
