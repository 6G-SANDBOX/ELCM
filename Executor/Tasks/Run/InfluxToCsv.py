from Task import Task
from Helper import Level, influx
from Settings import Config

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

        common_params = {"influx_dir": influx_dir, "execution_id": execution_id, "url": url}

        if version == influx.Versions.V1:
            influx.InfluxDb.export_influxdb_v1(**common_params, 
                                               database=config.InfluxDb.Database, 
                                               user=config.InfluxDb.User, 
                                               password=config.InfluxDb.Password)

        elif version == influx.Versions.V2:
            influx.InfluxDb.export_influxdb_v2(**common_params, 
                                               bucket=config.InfluxDb.Database, 
                                               token=config.InfluxDb.Token, 
                                               org=config.InfluxDb.Org)
        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")