from prometheus_api_client import PrometheusConnect
from .to_influx import ToInfluxBase
from Helper import Level, influx
from datetime import datetime
import requests
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
        url, session = self.init_prometheus_session()
        if session:
            prometheus = PrometheusConnect(url=url, session=session)
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
                if isinstance(e, influx.InfluxDBError) and e.response.status == 422:
                    self.Log(Level.WARNING, f"Warning (ATHONET): Unprocessable entity (422). Invalid data: {data}")
                else:
                    self.Log(Level.ERROR, f"Failed to send data to InfluxDB (ATHONET). Exception: {e}")
                    raise RuntimeError(f"Exiting due to unexpected error: {e}")

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

                metric_name = self.sanitize_string(metric_name)
                
                if metric_type:
                    metric_type = self.sanitize_string(metric_type)
                    metric_name = f"{metric_name}_{metric_type}"
                
                if metric_cause:
                    metric_cause = self.sanitize_string(metric_cause)
                    metric_name = f"{metric_name}_{metric_cause}"

                if timestamp not in data_dict:
                    data_dict[timestamp] = {metric_name: metric_value}
                else:
                    data_dict[timestamp][metric_name] = metric_value

    def process_range_queries(self, prometheus, queries_range, start_time, end_time, step, data_dict, max_retries=3):
        for query in queries_range:
            attempts = 0
            while attempts < max_retries:
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
                    break
                except Exception as e:
                    attempts += 1
                    self.Log(Level.ERROR, f"Error executing range query '{query}', attempt {attempts}: {e}")
                    if attempts < max_retries:
                        self.Log(Level.WARNING, "Try to reconnect.")
                        prometheus = self.reauthenticate_and_get_prometheus()
                        if not prometheus:
                            self.Log(Level.ERROR, "Could not reauthenticate with Prometheus. Exiting.")
                            return
                    else:
                        self.Log(Level.ERROR, f"Max retries reached for query '{query}'. Skipping this query.")

    def process_custom_queries(self, prometheus, queries_custom, data_dict, max_retries=3):
        for query in queries_custom:
            attempts = 0
            while attempts < max_retries:
                try:
                    data = prometheus.custom_query(query=query)
                    if data:
                        self.Log(Level.INFO, f"Custom query executed successfully: {query}")
                        self.store_query_data(data, query, data_dict)
                    else:
                        self.Log(Level.WARNING, f"Custom query was not executed successfully: {query}")
                    break
                except Exception as e:
                    attempts += 1
                    self.Log(Level.ERROR, f"Error executing custom query '{query}', attempt {attempts}: {e}")
                    if attempts < max_retries:
                        self.Log(Level.WARNING, "Try to reconnect.")
                        prometheus = self.reauthenticate_and_get_prometheus()
                        if not prometheus:
                            self.Log(Level.ERROR, "Could not reauthenticate with Prometheus. Exiting.")
                            return
                    else:
                        self.Log(Level.ERROR, f"Max retries reached for query '{query}'. Skipping this query.")

    def init_prometheus_session(self):
        athonet_query_url = self.params['AthonetQueryUrl']
        self.authenticate()

        if not self.access_token:
            self.Log(Level.ERROR, "Failed to obtain access token for Prometheus queries.")
            return None, None

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
        stop = self.params['Stop']
        step = self.params['Step']
        measurement = self.params['Measurement']

        while not self.parent.ReadMilestone(stop) and not self.parent.stopRequested:
            time.sleep(1)
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
        self.Log(Level.INFO, "Connected to Prometheus")

        try:
            if queries_range:
                self.process_range_queries(prometheus, queries_range, start_time, end_time, step, data_dict)
            if queries_custom:
                self.process_custom_queries(prometheus, queries_custom, data_dict)
            if data_dict:
                self.send_data_to_influx(data_dict, measurement, executionId)
        except Exception:
            self.SetVerdictOnError()
