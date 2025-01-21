import subprocess
from Task import Task
from Helper import Level, influx
from Settings import Config
import os

class InfluxToCsv(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("InfluxToCsv", parent, params, logMethod, None)

        # Define required and optional parameters for both InfluxDB v1 and v2
        self.paramRules = {
            'ExecutionId': (None, True),     
            'Measurement': (None, True)     # Required: InfluxDB measurement to export
        }

    def export_influxdb_v1(self, influx_dir, database, measurement, execution_id, url, user, password):
        
        output_file = f"csv_{execution_id}.csv"
        command = f"""curl -G "{url}/query" \
            --data-urlencode "db={database}" \
            --data-urlencode "q=SELECT * FROM \\"{measurement}\\" WHERE \\"ExecutionId\\" = '{execution_id}'" \
            -H "Accept: application/csv" \
            --user {user}:{password} > {output_file}"""
        try:
            subprocess.run(command, shell=True, cwd=influx_dir, check=True)
            self.Log(Level.INFO, f"Data successfully exported to {output_file} from InfluxDB v1.x")
        except subprocess.CalledProcessError as e:
            self.Log(Level.ERROR, f"Error exporting data from InfluxDB v1.x: {e}")

    def export_influxdb_v2(self, influx_dir, bucket, measurement, token, org, execution_id, url):
        output_file = f"csv_{execution_id}.csv"
        flux_query = (
            f'from(bucket: "{bucket}") '
            f'|> range(start: 0) '
            f'|> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["ExecutionId"] == "{execution_id}")'
        )
        
        command = [
            "curl", "-X", "POST", f"{url}/api/v2/query?org={org}",
            "-H", f"Authorization: Token {token}",
            "-H", "Content-Type: application/vnd.flux",
            "--data", flux_query,
            "--output", output_file
        ]

        try:
            subprocess.run(command, shell=True, cwd=influx_dir, check=True)
            self.Log(Level.INFO, f"Data successfully exported to {output_file} from InfluxDB v2.x")
        except subprocess.CalledProcessError as e:
            self.Log(Level.ERROR, f"Error exporting data from InfluxDB v2.x: {e}")

    def Run(self):

        config=Config()
        
        url = f"http://{config.InfluxDb.Host}:{config.InfluxDb.Port}"
        version = influx.InfluxDb.detectInfluxDBVersion(url)  # Get the detected version
        execution_id = self.params.get('ExecutionId')
        influx_dir = "C:/elcm/CSV/" if os.name == 'nt' else "/elcm/CSV/"
        measurement = self.params.get('Measurement')

        try:
            os.makedirs(influx_dir, exist_ok=True)
            self.Log(Level.INFO, f"Directory created or already exists: {influx_dir}")
        except Exception as e:
            self.Log(Level.ERROR, f"Failed to create directory {influx_dir}: {e}")
            return

        self.Log(Level.INFO, f"Executing the command in the directory: {influx_dir}")

        common_args = {
            'influx_dir': influx_dir,
            'measurement': measurement,
            'execution_id': execution_id,
            'url': url
        }

        if version == influx.Versions.V1:
            self.export_influxdb_v1(**common_args, database=config.InfluxDb.Database,user=config.InfluxDb.User,password=config.InfluxDb.Password)
        elif version == influx.Versions.V2:
            self.export_influxdb_v2(**common_args, bucket=config.InfluxDb.Database, token=config.InfluxDb.Token, org=config.InfluxDb.Org)
        else:
            self.Log(Level.ERROR, "Invalid InfluxDB version. Must be '1' or '2'.")