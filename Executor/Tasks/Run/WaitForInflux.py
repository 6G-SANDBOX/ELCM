from Task import Task
from Helper import Level, influx
from Settings import Config
import time

class WaitForInflux(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("WaitForInflux", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),
            'CheckInterval': (30, False),
            'TimeWindow': (30, False)
        }

    def Run(self):
        config = Config()
        url = f"http://{config.InfluxDb.Host}:{config.InfluxDb.Port}"
        version = influx.InfluxDb.detectInfluxDBVersion(url)
        execution_id = self.params.get('ExecutionId')
        check_interval = self.params.get('CheckInterval')
        time_window = self.params.get('TimeWindow')

        if version == influx.Versions.V1:
            while influx.InfluxDb.is_influxdb_v1_receiving_data(
                url, config.InfluxDb.Database, config.InfluxDb.User, 
                config.InfluxDb.Password, execution_id, time_window
            ):
                time.sleep(check_interval)

        elif version == influx.Versions.V2:
            while influx.InfluxDb.is_influxdb_v2_receiving_data(
                url, config.InfluxDb.Database, config.InfluxDb.Token, 
                config.InfluxDb.Org, execution_id, time_window
            ):
                time.sleep(check_interval)

        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")
