from Task import Task
from Helper import Level, influx
from Settings import Config

class InfluxToCsv(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("InfluxToCsv", parent, params, logMethod, None)
        self.paramRules = {
            'IdCsv': (None, True),
            'Token': (None, False),
            'Password': (None, False),
            'User': (None, False),
            'Host': (None, False),
            'Port': (None, False),
            'Database': (None, False),
            'Org': (None, False),
            'CustomQuery': (None, True)
        }

    def Run(self):
        config = Config()

        host = self.params.get('Host') or config.InfluxDb.Host
        port = self.params.get('Port') or config.InfluxDb.Port
        url = f"http://{host}:{port}"
        version = influx.InfluxDb.detectInfluxDBVersion(url)

        id_csv = self.params.get('IdCsv')
        influx_dir = self.parent.TempFolder

        token = self.params.get('Token') or config.InfluxDb.Token
        password = self.params.get('Password') or config.InfluxDb.Password
        user = self.params.get('User') or config.InfluxDb.User
        database = self.params.get('Database') or config.InfluxDb.Database
        org = self.params.get('Org') or config.InfluxDb.Org
        custom_query = self.params.get('CustomQuery')

        if not custom_query:
            self.Log(Level.ERROR, "'CustomQuery' must be provided.")
            return

        common_params = {
            "influx_dir": influx_dir,
            "id_csv": id_csv,
            "url": url
        }

        if version == influx.Versions.V1:
            influx.InfluxDb.export_influxdb_v1(
                **common_params,
                database=database,
                user=user,
                password=password,
                custom_query=custom_query
            )
        elif version == influx.Versions.V2:
            influx.InfluxDb.export_influxdb_v2(
                **common_params,
                token=token,
                org=org,
                custom_query=custom_query
            )
        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")
