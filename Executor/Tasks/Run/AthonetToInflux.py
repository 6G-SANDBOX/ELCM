from prometheus_api_client import PrometheusConnect
from .to_influx import ToInfluxBase
from Helper import utils, Level
from datetime import datetime
import requests
import re
import time

class AthonetToInflux(ToInfluxBase):

    def __init__(self, logMethod, parent, params):
        
        super().__init__("ATHONET", parent, params, logMethod, None)

        self.paramRules = {
            'ExecutionId': (None, True),
            'QueriesRange': (None, False),
            'QueriesCustom': (None, False),
            'Measurement': (None, True),
            'Stop': (None, True),
            'Step': (None, True),
            'Username': (None, True),  
            'Password': (None, True),  
            'AthonetLoginUrl': (None, True), 
            'AthonetQueryUrl': (None, True)
        }

        self.access_token = None
        self.Log(Level.INFO, f"{self.name} initialized")

    def sanitize_metric_name(self, name):
        return re.sub(r'[^a-zA-Z0-9_]', '_', name).rstrip('_')

    def authenticate(self):
        login_url = self.params.get('AthonetLoginUrl')
        username = self.params.get('Username')
        password = self.params.get('Password')

        if not login_url or not username or not password:
            self.Log(Level.ERROR, "Login URL, username, or password not provided.")
            return

        try:
            response = requests.post(
                login_url,
                json={"username": username, "password": password},
                verify=False
            )
            response.raise_for_status()
            self.access_token = response.json().get("access_token")
            if not self.access_token:
                raise ValueError("No access token returned.")
            self.Log(Level.INFO, "Authentication successful, access token obtained.")
        except Exception as e:
            self.Log(Level.ERROR, f"Authentication error: {e}")
            self.access_token = None

    def reauthenticate_and_get_prometheus(self):
        self.Log(Level.WARNING, "Token expired. Attempting re-authentication.")
        session = self.init_prometheus_session()
        if session:
            prometheus = PrometheusConnect(url=session['url'], session=session['session'])
            if prometheus.check_prometheus_connection():
                self.Log(Level.INFO, "Re-authentication successful.")
                return prometheus
        self.Log(Level.ERROR, "Failed to re-authenticate or connect to Prometheus.")
        self.SetVerdictOnError()
        return None

    def send_data_to_influx(self, data_dict, measurement, executionId):
        for timestamp, data in data_dict.items():
            try:
                self._send_to_influx(measurement, data, timestamp, executionId)
            except Exception as e:
                self.Log(Level.ERROR, f"Error sending data to InfluxDB: {e}")
                self.SetVerdictOnError()
                return

    def store_query_data(self, data, query, data_dict):
        for result in data:
            entries = result.get('values') or [result.get('value')]
            if not entries:
                continue

            for entry in entries:
                timestamp = int(entry[0])
                metric_value = float(entry[1])

                metric_name = result['metric'].get('name', query)
                metric_type = result['metric'].get('type', None)
                metric_cause = result['metric'].get('cause', None)

                metric_name = self.sanitize_metric_name(metric_name)
                
                if metric_type:
                    metric_type = self.sanitize_metric_name(metric_type)
                    metric_name = f"{metric_name}_{metric_type}"
                
                if metric_cause:
                    metric_cause = self.sanitize_metric_name(metric_cause)
                    metric_name = f"{metric_name}_{metric_cause}"

                if timestamp not in data_dict:
                    data_dict[timestamp] = {metric_name: metric_value}
                else:
                    data_dict[timestamp][metric_name] = metric_value

    def process_range_queries(self, prometheus, queries_range, start_time, end_time, step, data_dict):
        for i, query in enumerate(queries_range):
            try:
                data = prometheus.custom_query_range(
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                    step=step
                )
                self.Log(Level.INFO, f"Range query executed successfully: {query}")
                if data:
                    self.store_query_data(data, query, data_dict)
            except Exception as e:
                self.Log(Level.ERROR, f"Error executing range query '{query}': {e}")
                if not prometheus.check_prometheus_connection():
                    prometheus = self.reauthenticate_and_get_prometheus()
                    if not prometheus:
                        self.Log(Level.ERROR, "Could not reauthenticate with Prometheus. Exiting.")
                        return
                self.Log(Level.WARNING, f"Retrying remaining queries from '{query}'.")
                self.process_range_queries(prometheus, queries_range[i:], start_time, end_time, step, data_dict)

    def process_custom_queries(self, prometheus, queries_custom, data_dict):
        for i, query in enumerate(queries_custom):
            try:
                data = prometheus.custom_query(query=query)
                self.Log(Level.INFO, f"Custom query executed successfully: {query}")
                if data:
                    self.store_query_data(data, query, data_dict)
            except Exception as e:
                self.Log(Level.ERROR, f"Error executing custom query '{query}': {e}")
                if not prometheus.check_prometheus_connection():
                    prometheus = self.reauthenticate_and_get_prometheus()
                    if not prometheus:
                        self.Log(Level.ERROR, "Could not reauthenticate with Prometheus. Exiting.")
                        return
                self.Log(Level.WARNING, f"Retrying remaining queries from '{query}'.")
                self.process_custom_queries(prometheus, queries_custom[i:], data_dict)

    def init_prometheus_session(self):
        athonet_query_url = self.params['AthonetQueryUrl']
        self.authenticate()

        if not self.access_token:
            self.Log(Level.ERROR, "Failed to obtain access token for Prometheus queries.")
            return None

        try:
            session = requests.Session()
            session.verify = False
            session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            return athonet_query_url, session
        except Exception as e:
            self.Log(Level.ERROR, f"Error initializing Prometheus session: {e}")
            return None, None

    def Run(self):
        executionId = self.params['ExecutionId']
        queries_range = self.params['QueriesRange']
        queries_custom = self.params['QueriesCustom']
        start_time = datetime.now()
        stop = self.params['Stop'] + "_" + str(executionId)
        step = self.params['Step']
        measurement = self.params['Measurement']

        while stop not in utils.task_list:
            time.sleep(1)
            pass
        utils.task_list.remove(stop)
        end_time = datetime.now()

        data_dict = {}

        url, session = self.init_prometheus_session()
        if session is None:
            self.Log(Level.ERROR, "Failed to initialize Prometheus session")
            return

        prometheus = PrometheusConnect(url=url, session=session)

        if not prometheus.check_prometheus_connection():
            self.Log(Level.ERROR, "Failed to connect to Prometheus")
            self.SetVerdictOnError()
            return

        try:
            if queries_range:
                self.process_range_queries(prometheus, queries_range, start_time, end_time, step, data_dict)

            if queries_custom:
                self.process_custom_queries(prometheus, queries_custom, data_dict)

            if data_dict:
                self.send_data_to_influx(data_dict, measurement, executionId)

        except Exception as e:
            self.Log(Level.ERROR, f"Unexpected error during Run: {e}")