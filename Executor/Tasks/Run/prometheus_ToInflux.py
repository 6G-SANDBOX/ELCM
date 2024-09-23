from Task import Task
from prometheus_api_client import PrometheusConnect
from Helper import utils, Level
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from Settings import PROMETHEUSConfig

# Utility function to manage a queue (cola) for handling control messages
cola = utils.cola

class PrometheusToInflux(Task):

    def __init__(self, logMethod, parent, params):
        super().__init__("PROMETHEUS", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),
            'URL': (None, True),
            'PORT': (None, True),
            'QUERIES_RANGE': (None, False),
            'QUERIES_CUSTOM': (None, False),
            'MEASUREMENT': (None, True),
            'STOP': (None, True),
            'STEP': (None, True),
            'ACCOUNT': (False, True),
            'CERTIFICATES': (None, False),
            'ENCRYPTION': (False, True)
        }

    def init_prometheus_session(self, URL_host, PORT_host, base_path, encryption, account, user, password):
        try:

            if not isinstance(encryption, bool):
                self.Log(Level.ERROR, f"Exception prometheus_bool: bool_1")
                return
            if not isinstance(account, bool):
                self.Log(Level.ERROR, f"Exception prometheus_bool: bool_2")
                return

            if encryption and account:
                url = f"https://{URL_host}:{PORT_host}"
                session = requests.Session()
                session.cert = (base_path + 'client-cert.pem', base_path + 'client-key.pem')
                session.verify = base_path + 'ca.pem'
                session.auth = HTTPBasicAuth(user, password)
            elif encryption and not account:
                url = f"https://{URL_host}:{PORT_host}"
                session = requests.Session()
                session.cert = (base_path + 'client-cert.pem', base_path + 'client-key.pem')
                session.verify = base_path + 'ca.pem'
            elif not encryption and account:
                url = f"http://{URL_host}:{PORT_host}"
                session = requests.Session()
                session.auth = HTTPBasicAuth(user, password)
            else:
                url = f"http://{URL_host}:{PORT_host}"
                session = None
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
                self.Log(Level.INFO, f"Range query executed successfully: {query}")
                if data:
                    self.store_query_data(data, query, data_dict)
            except Exception as e:
                self.Log(Level.ERROR, f"Error executing range query '{query}': {e}")

    def process_custom_queries(self, prometheus, queries_custom, data_dict):
        for query in queries_custom:
            try:
                data = prometheus.custom_query(query=query)
                self.Log(Level.INFO, f"Custom query executed successfully: {query}")
                if data:
                    self.store_query_data(data, query, data_dict)
            except Exception as e:
                self.Log(Level.ERROR, f"Error executing custom query '{query}': {e}")
   

    def store_query_data(self, data, query, data_dict):
        
        for result in data:
            
            if 'values' in result:
                entries = result['values']
            elif 'value' in result:
                entries = [result['value']]
            else:
                continue  

            for entry in entries:

                timestamp = int(entry[0])
                value = entry[1]
                
                if isinstance(value, int):
                    value = float(value)

                if timestamp not in data_dict:
                    data_dict[timestamp] = {query: value}
                else:
                    data_dict[timestamp][query] = value

    def send_data_to_influx(self, data_dict, measurement, executionId):

        for timestamp, data in data_dict.items():

            flat_data = utils.flatten_prometheus_json(data)

            try:
                utils.send_to_influx(measurement, flat_data, timestamp, executionId)
            except Exception as e:
                self.Log(Level.ERROR, f"Error sending data to InfluxDB: {e}")
                self.SetVerdictOnError()
                return

    def Run(self):
        executionId = self.params['ExecutionId']
        URL_host = self.params['URL']
        PORT_host = self.params['PORT']
        queries_range = self.params['QUERIES_RANGE']
        queries_custom = self.params['QUERIES_CUSTOM']
        start_time = datetime.now()
        stop = self.params['STOP'] + "_" + str(executionId)
        step = self.params['STEP']
        measurement = self.params['MEASUREMENT']
        base_path = self.params['CERTIFICATES']
        encryption = self.params['ENCRYPTION']
        prometheus_info = PROMETHEUSConfig()
        info = prometheus_info.user
        user = info.get("User", None)
        password = info.get("Password", None)
        account = self.params['ACCOUNT']

        # Initialize the Prometheus session
        session = self.init_prometheus_session(URL_host, PORT_host, base_path, encryption, account, user, password)

        if session is None:
            self.Log(Level.ERROR, "Failed to initialize Prometheus session")
            return

        prometheus = PrometheusConnect(url=session['url'], session=session['session'])

        if not prometheus.check_prometheus_connection():
            self.Log(Level.ERROR, "Failed to connect to Prometheus")
            self.SetVerdictOnError()
            return

        ready = ""
        while ready != stop:
            if not cola.empty():
                ready = cola.get_nowait()
                if ready != stop:
                    cola.put_nowait(ready)

        end_time = datetime.now()

        # Process both range and custom queries
        data_dict = {}

        # Handle range queries
        if queries_range!=None:
            self.process_range_queries(prometheus, queries_range, start_time, end_time, step, data_dict)

        # Handle custom queries (instant queries)
        if queries_custom!=None:
            self.process_custom_queries(prometheus, queries_custom, data_dict)
            
        if queries_range!=None or queries_custom!=None:
            # Send the data to InfluxDB
            self.send_data_to_influx(data_dict, measurement, executionId)