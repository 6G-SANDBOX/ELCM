from Task import Task
from Helper import Level, influx
from Settings import Config

class InfluxToCsv(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("InfluxToCsv", parent, params, logMethod, None)

        # Define required and optional parameters for both InfluxDB v1 and v2
        self.paramRules = {
            'ExecutionId': (None, True),     
            'Measurement': (None, True)     # Required: InfluxDB measurement to export
        }

    def Run(self):

        config=Config()
        
        url = f"http://{config.InfluxDb.Host}:{config.InfluxDb.Port}"
        version = influx.InfluxDb.detectInfluxDBVersion(url)  # Get the detected version
        execution_id = self.params.get('ExecutionId')
        influx_dir = self.parent.TempFolder
        measurement = self.params.get('Measurement')

        self.Log(Level.INFO, f"Executing the request in the directory: {influx_dir}")

        common_args = {
            'influx_dir': influx_dir,
            'measurement': measurement,
            'execution_id': execution_id,
            'url': url
        }

        if version == influx.Versions.V1:
            influx.InfluxDb.export_influxdb_v1(**common_args, database=config.InfluxDb.Database,user=config.InfluxDb.User,password=config.InfluxDb.Password)
        elif version == influx.Versions.V2:
            influx.InfluxDb.export_influxdb_v2(**common_args, bucket=config.InfluxDb.Database, token=config.InfluxDb.Token, org=config.InfluxDb.Org)
        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")