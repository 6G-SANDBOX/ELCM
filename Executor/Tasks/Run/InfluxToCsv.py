from Task import Task
from Helper import Level, influx
from Settings import Config

class InfluxToCsv(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("InfluxToCsv", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),
            'Token': (None, False),
            'Password': (None, False),
            'User': (None, False),
            'Url': (None, False),
            'Port': (None, False),
            'Database': (None, False),
            'Measurement': (None, True)
        }

    def Run(self):
        config = Config()

        host = self.params.get('Url') or config.InfluxDb.Host
        port = self.params.get('Port') or config.InfluxDb.Port
        url = f"http://{host}:{port}"
        version = influx.InfluxDb.detectInfluxDBVersion(url)
        execution_id = self.params.get('ExecutionId')
        influx_dir = self.parent.TempFolder

        token = self.params.get('Token') or config.InfluxDb.Token
        password = self.params.get('Password') or config.InfluxDb.Password
        user = self.params.get('User') or config.InfluxDb.User
        database = self.params.get('Database') or config.InfluxDb.Database
        measurement = self.params.get('Measurement')

        common_params = {
            "influx_dir": influx_dir,
            "execution_id": execution_id,
            "url": url,
            "measurement": measurement
        }

        if version == influx.Versions.V1:
            influx.InfluxDb.export_influxdb_v1(
                **common_params,
                database=database,
                user=user,
                password=password
            )
        elif version == influx.Versions.V2:
            influx.InfluxDb.export_influxdb_v2(
                **common_params,
                bucket=database,
                token=token,
                org=config.InfluxDb.Org
            )
        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")
