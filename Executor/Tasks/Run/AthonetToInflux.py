from prometheus_api_client import PrometheusConnect
from .prometheus_ToInflux import PrometheusToInflux
from Helper import utils, Level
from datetime import datetime
import requests
import re

class AthonetToInflux(PrometheusToInflux):

    def sanitize_metric_name(self, name):
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return name.rstrip('_')

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
                 
    def __init__(self, logMethod, parent, params):
        athonet_defaults = {
            'Url': "",
            'Port': "",
            'Account': False,
            'Certificates': None,
            'Encryption': False,
        }
        
        params = {**athonet_defaults, **params}
        super().__init__(logMethod, parent, params)

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

    def init_prometheus_session(self):
        athonet_query_url = self.params['AthonetQueryUrl']

        if not self.access_token:
            self.authenticate()

        if not self.access_token:
            self.Log(Level.ERROR, "Failed to obtain access token for Prometheus queries.")
            return None

        try:
            session = requests.Session()
            session.verify = False
            session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            return {'url': athonet_query_url, 'session': session}
        except Exception as e:
            self.Log(Level.ERROR, f"Error initializing Prometheus session: {e}")
            return None

    def Run(self):
        executionId = self.params['ExecutionId']
        queries_range = self.params['QueriesRange']
        queries_custom = self.params['QueriesCustom']
        start_time = datetime.now()
        stop = self.params['Stop'] + "_" + str(executionId)
        step = self.params['Step']
        measurement = self.params['Measurement']

        session = self.init_prometheus_session()
        if session is None:
            self.Log(Level.ERROR, "Failed to initialize Prometheus session")
            return

        prometheus = PrometheusConnect(url=session['url'], session=session['session'])

        if not prometheus.check_prometheus_connection():
            self.Log(Level.ERROR, "Failed to connect to Prometheus")
            self.SetVerdictOnError()
            return

        while stop not in utils.task_list:
            pass
        utils.task_list.remove(stop)
        end_time = datetime.now()

        data_dict = {}

        try:
            if queries_range:
                
                self.process_range_queries(prometheus, queries_range, start_time, end_time, step, data_dict)

            if queries_custom:
                
                self.process_custom_queries(prometheus, queries_custom, data_dict)

            if data_dict:
                self.send_data_to_influx(data_dict, measurement, executionId)

        except Exception as e:
            self.Log(Level.ERROR, f"Unexpected error during Run: {e}")