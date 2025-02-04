from Task import Task
from Helper import Level, influx
from Settings import Config
import time

class InfluxToCsv(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("InfluxToCsv", parent, params, logMethod, None)
        self.paramRules = {'ExecutionId': (None, True)}

    def Run(self):
        config = Config()
        url = f"http://{config.InfluxDb.Host}:{config.InfluxDb.Port}"
        version = influx.InfluxDb.detectInfluxDBVersion(url)
        execution_id = self.params.get('ExecutionId')
        influx_dir = self.parent.TempFolder

        if version == influx.Versions.V1:
            while influx.InfluxDb.is_influxdb_v1_receiving_data(url, config.InfluxDb.Database, config.InfluxDb.User, config.InfluxDb.Password, execution_id):
                time.sleep(1)

            influx.InfluxDb.export_influxdb_v1(
                influx_dir=influx_dir,
                execution_id=execution_id,
                url=url,
                database=config.InfluxDb.Database,
                user=config.InfluxDb.User,
                password=config.InfluxDb.Password
            )

        elif version == influx.Versions.V2:
            while influx.InfluxDb.is_influxdb_v2_receiving_data(url, config.InfluxDb.Database, config.InfluxDb.Token, config.InfluxDb.Org, execution_id):
                time.sleep(1)

            influx.InfluxDb.export_influxdb_v2(
                influx_dir=influx_dir,
                execution_id=execution_id,
                url=url,
                bucket=config.InfluxDb.Database,
                token=config.InfluxDb.Token,
                org=config.InfluxDb.Org
            )

        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")