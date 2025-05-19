from influxdb import InfluxDBClient as InfluxDBClient_v1
from influxdb_client import InfluxDBClient as InfluxDBClient_v2
from influxdb_client import Point
from requests import RequestException
from influxdb_client.client.exceptions import InfluxDBError
from threading import local, RLock
from Settings import Config
from typing import Dict, List, Union
from datetime import datetime, timezone
from csv import DictWriter, DictReader, Dialect, QUOTE_NONE
import re
import requests
import enum
from Helper import Log
import os
import pandas as pd
from dateutil.parser import isoparse

class BatchingCallback(object):

    def __init__(self):
        self.last_error = None

    def error(self, conf: (str, str, str), data: str, exception: InfluxDBError):
        self.last_error = exception

class ThreadLocalBatchingCallback:

    def __init__(self):
        self._storage = local()

    def get_callback(self):
        if not hasattr(self._storage, 'callback'):
            self._storage.callback = BatchingCallback()
        return self._storage.callback

class Versions(enum.Enum):
    V1 = "1"
    V2 = "v2"

class InfluxPoint:
    def __init__(self, time: datetime):
        self.Time = time
        self.Fields: Dict[str, object] = {}

    def __str__(self):
        return f"<{self.Time} {self.Fields}>"

class InfluxPayload:
    def __init__(self, measurement: str):
        self.Measurement = re.sub(r'\W+', '_', measurement)  # Replace spaces and non-alphanumeric characters with _
        self.Tags: Dict[str, str] = {}
        self.Points: List[InfluxPoint] = []
        self.Version = None

    @property
    def Serialized(self):
        data = []

        if self.Version == Versions.V1:
            for point in self.Points:
                data.append(
                    {'measurement': self.Measurement,
                     'tags': self.Tags,
                     'time': point.Time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                     'fields': point.Fields}
                )
        elif self.Version == Versions.V2:
            for point in self.Points:
                p = Point(self.Measurement)
                for k, v in self.Tags.items():
                    p.tag(k, v)
                for k, v in point.Fields.items():
                    p.field(k, v)
                p.time(point.Time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                data.append(p)
        return data

    def __str__(self):
        return f"InfluxPayload['{self.Measurement}' - Tags: {self.Tags} - " + \
            f"Points: [{', '.join(str(p) for p in self.Points)}]]"

    @classmethod
    def FromEastWestData(cls, measurement: str, tags: Dict[str, str], header: List[str], points: List):
        res = InfluxPayload(measurement)
        res.Tags = tags
        for point in points:
            timestamp, values = point
            influxPoint = InfluxPoint(datetime.fromtimestamp(timestamp))
            for key, value in zip(header, values):
                influxPoint.Fields[key] = value
            res.Points.append(influxPoint)
        return res

class baseDialect(Dialect):
    delimiter = ','
    escapechar = None
    doublequote = False
    skipinitialspace = False
    lineterminator = '\r\n'
    quotechar = '"'
    quoting = QUOTE_NONE

class InfluxDb:
    _lock = RLock()
    thread_callbacks = ThreadLocalBatchingCallback()
    _thread_local = local()

    @staticmethod
    def detectInfluxDBVersion(url):
        try:
            response = requests.get(f"{url}/ping")
            header = response.headers.get('X-Influxdb-Version', 'Unknown version')
            if header.startswith(Versions.V2.value):
                return Versions.V2
            elif header.startswith(Versions.V1.value):
                return Versions.V1
            else:
                raise Exception("Unknown influxDB version")
        except requests.exceptions.RequestException as e:
            raise RequestException("Can't connect to InfluxDB server")

    @classmethod
    def initialize(cls):
        config = Config()
        influx = config.InfluxDb
        influxdb_url = f"http://{influx.Host}:{influx.Port}"
        cls.version = cls.detectInfluxDBVersion(influxdb_url)

        if hasattr(cls._thread_local, 'client'):
            cls.cleanup()

        try:
            if cls.version == Versions.V1:
                cls._thread_local.client = InfluxDBClient_v1(influx.Host, influx.Port,
                                                             influx.User, influx.Password, influx.Database)
            elif cls.version == Versions.V2:
                cls._thread_local.client = InfluxDBClient_v2(url=influxdb_url,
                                                             token=influx.Token,
                                                             org=influx.Org)
        except Exception as e:
            raise Exception(f"Exception while creating Influx client, please review configuration: {e}") from e

        metadata = config.Metadata
        cls.baseTags = {
            "appname": "ELCM",
            "facility": metadata.Facility,
            "host": metadata.HostIp,
            "hostname": metadata.HostName
        }
        cls.database = influx.Database

    @classmethod
    def cleanup(cls):
        if hasattr(cls._thread_local, 'client'):
            try:
                cls._thread_local.client.close()
                Log.I(f"InfluxDB client closed successfully for the thread.")
            except Exception as e:
                Log.I(f"Error closing InfluxDB client: {e}.")
            finally:
                del cls._thread_local.client

    @classmethod
    def BaseTags(cls) -> Dict[str, object]:
        if not hasattr(cls, 'baseTags') or cls.baseTags == {}:
            config = Config()
            metadata = config.Metadata
            cls.baseTags = {
                "appname": "ELCM",
                "facility": metadata.Facility,
                "host": metadata.HostIp,
                "hostname": metadata.HostName
            }
        return cls.baseTags

    @classmethod
    def Send(cls, payload: InfluxPayload):
        with cls._lock:
            if not hasattr(cls._thread_local, 'client'):
                cls.initialize()

            payload.Tags.update(cls.BaseTags())
            payload.Version = cls.version

            callback = cls.thread_callbacks.get_callback()

            if cls.version == Versions.V1:
                cls._thread_local.client.write_points(payload.Serialized)
            elif cls.version == Versions.V2:
                write_api = cls._thread_local.client.write_api(error_callback=callback.error)
                write_api.write(bucket=cls.database, org=Config().InfluxDb.Org, record=payload.Serialized)
                write_api.close()
            if callback.last_error:
                tmp = callback.last_error
                callback.last_error = None
                cls.cleanup()
                raise InfluxDBError(tmp.response) 

    @classmethod
    def PayloadToCsv(cls, payload: InfluxPayload, outputFile: str):
        allKeys = {'Datetime', 'Timestamp'}
        for point in payload.Points:
            allKeys.update(point.Fields.keys())
        allKeys = sorted(list(allKeys))
        allKeys.extend(sorted(payload.Tags.keys()))

        # https://stackoverflow.com/a/3348664 (newline)
        with open(os.path.abspath(outputFile), 'w', encoding='utf-8', newline='') as output:
            csv = DictWriter(output, fieldnames=allKeys, restval='')
            csv.writeheader()
            for point in payload.Points:
                data = {'Datetime': point.Time, 'Timestamp': point.Time.timestamp()}
                data.update(point.Fields)
                data.update(payload.Tags)
                csv.writerow(data)

    @classmethod
    def CsvToPayload(cls, measurement: str, csvFile: str, delimiter: str, timestampKey: str,
                    tryConvert: bool = True, keysToRemove: List[str] = None) -> InfluxPayload:
        
        from Executor.Tasks.Run.to_influx import ToInfluxBase

        def _convert(value: str) -> Union[int, float, bool, str]:
            try:
                return float(value)
            except ValueError:
                pass
            return {'true': True, 'false': False}.get(value.lower(), value)

        def parse_timestamp(timestamp_str: str) -> datetime:
            try:
                ts = float(timestamp_str)
            except ValueError:
                raise RuntimeError(f"Invalid timestamp: {timestamp_str}")

            if ts > 1e17:
                return datetime.fromtimestamp(ts / 1e9, tz=timezone.utc)
            elif ts > 1e12:
                return datetime.fromtimestamp(ts / 1e3, tz=timezone.utc)
            else:
                return datetime.fromtimestamp(ts, tz=timezone.utc)

        keysToRemove = keysToRemove or []

        if not hasattr(cls._thread_local, 'client'):
            cls.initialize()

        with open(csvFile, 'r', encoding='utf-8', newline='') as file:
            header = file.readline()
            keys = [k.strip() for k in header.split(delimiter)]

            if timestampKey not in keys:
                raise RuntimeError(f"CSV file does not seem to contain timestamp ('{timestampKey}'). "
                                f"Found keys: {keys}")

            dialect = baseDialect()
            dialect.delimiter = str(delimiter.strip())
            csv = DictReader(file, fieldnames=keys, restval=None, dialect=dialect)

            payload = InfluxPayload(measurement)

            for row in csv:
                ts_str = row.pop(timestampKey)
                try:
                    timestamp = parse_timestamp(ts_str)
                except Exception:
                    try:
                        timestamp = isoparse(ts_str)
                    except Exception as e:
                        raise RuntimeError(f"Error parsing timestamp: {ts_str}") from e

                point = InfluxPoint(timestamp)

                field_name = row.pop("_field", None)
                raw_value = row.pop("_value", None)
                csv_measurement = row.pop("_measurement", None)

                if field_name is not None:
                    clean_field = ToInfluxBase.sanitize_string(field_name)
                    clean_measurement = ToInfluxBase.sanitize_string(csv_measurement) if csv_measurement else None
                    full_field_name = f"{clean_measurement}_{clean_field}" if clean_measurement else clean_field
                    value = _convert(raw_value) if tryConvert else raw_value
                    point.Fields[full_field_name] = value

                for key, value in row.items():
                    if key in keysToRemove or value is None:
                        continue
                    if tryConvert:
                        value = _convert(value)
                    clean_key = ToInfluxBase.sanitize_string(key)
                    point.Fields[clean_key] = value

                payload.Points.append(point)

        return payload

    @classmethod
    def GetExecutionMeasurements(cls, executionId: int) -> List[str]:
        if not hasattr(cls._thread_local, 'client'):
            cls.initialize()

        if cls.version == Versions.V1:
            reply = cls._thread_local.client.query(f'SHOW measurements WHERE ExecutionId =~ /^{executionId}$/')
            return [e['name'] for e in reply['measurements']]

        elif cls.version == Versions.V2:
            reply = cls._thread_local.client.query_api().query(f'''
            from(bucket: "{cls.database}")
            |> range(start: 0)
            |> filter(fn: (r) => r["ExecutionId"] == "{executionId}")
            |> keep(columns: ["_measurement"])
            |> distinct(column: "_measurement")
            ''', org=Config().InfluxDb.Org)

            return [record.get_value() for table in reply for record in table.records]

    @classmethod
    def GetMeasurement(cls, executionId: int, measurement: str) -> List[InfluxPayload]:
        def _getTagSet(point, tags):
            values = [str(point[tag]) for tag in tags]
            return ','.join(values)

        def _getDateTime(value):
            try:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")

        if not hasattr(cls._thread_local, 'client'):
            cls.initialize()

        pointsPerTagSet = {}
        tags = []
        if cls.version == Versions.V1:
            # Retrieve the list of tags from the server, to separate from fields
            reply = cls._thread_local.client.query(f'show tag keys on "{cls.database}" from "{measurement}"')
            tags = sorted([t['tagKey'] for t in reply.get_points()])

            # Retrieve all points, separated depending on the tags
            reply = cls._thread_local.client.query(f'SELECT * FROM "{measurement}" WHERE ExecutionId =~ /^{executionId}$/')
            for point in reply.get_points():
                tagSet = _getTagSet(point, tags)
                if tagSet not in pointsPerTagSet.keys():
                    pointsPerTagSet[tagSet] = []
                pointsPerTagSet[tagSet].append(point)

        elif cls.version == Versions.V2:
            # Retrieve the list of tags from the server, to separate from fields
            reply = cls._thread_local.client.query_api().query(f'''
            import "influxdata/influxdb/schema"
            schema.tagKeys(
            bucket: "{cls.database}",
            predicate: (r) => r["_measurement"] == "{measurement}",
            start: 0)
            ''', org=Config().InfluxDb.Org)
            tags = sorted([record.get_value() for table in reply for record in table.records])

            # Retrieve all points, separated depending on the tags
            reply = cls._thread_local.client.query_api().query(f'''
            from(bucket: "{cls.database}")
            |> range(start: 0)
            |> filter(fn: (r) => r._measurement == "{measurement}")
            ''', org=Config().InfluxDb.Org)
            for table in reply:
                for point in table.records:
                    tagSet = _getTagSet(point, tags)
                    if tagSet not in pointsPerTagSet.keys():
                        pointsPerTagSet[tagSet] = []
                    pointsPerTagSet[tagSet].append(point)

        res = []

        # Process each set of points as a separate InfluxPayload
        for points in pointsPerTagSet.values():
            payload = InfluxPayload(f'Remote_{measurement}')
            for tag in tags:
                payload.Tags[tag] = points[0][tag]

            for point in points:
                if cls.version == Versions.V2:
                    point = {"measurement": point.get_measurement(), "field": point.get_field(),
                             "value": point.get_value(), "time": point.get_time(), **point.values}
                    timestamp = point.pop('time')
                    influxPoint = InfluxPoint(timestamp)
                elif cls.version == Versions.V1:
                    timestamp = point.pop('time')
                    influxPoint = InfluxPoint(_getDateTime(timestamp))
                for key in [f for f in point.keys() if f not in tags]:
                    influxPoint.Fields[key] = point[key]
                payload.Points.append(influxPoint)

            res.append(payload)

        return res
    
    def export_influxdb_v1(influx_dir, database, id_csv, url, user, password, custom_query):
        output_file = os.path.join(influx_dir, f"csv_query_{id_csv}.csv")

        if not custom_query:
            Log.I("No custom query provided for InfluxDB v1 export.")
            return

        params = {"db": database, "q": custom_query}
        headers = {"Accept": "application/csv"}
        try:
            response = requests.get(f"{url}/query", params=params, headers=headers, auth=(user, password))
            response.raise_for_status()
            with open(output_file, "w", encoding="utf-8", newline='') as f:
                f.write(response.text)
            Log.I(f"Data successfully exported to {output_file} from InfluxDB v1.x")
        except requests.exceptions.RequestException as e:
            Log.I(f"Error exporting data from InfluxDB v1.x: {e}")

    def export_influxdb_v2(influx_dir, token, org, id_csv, url, custom_query):
        output_file = os.path.join(influx_dir, f"csv_query_{id_csv}.csv")

        if not custom_query:
            Log.I("No custom query provided for InfluxDB v2 export.")
            return

        headers = {
            "Authorization": f"Token {token}",
            "Accept": "text/csv",
            "Content-Type": "application/vnd.flux"
        }
        try:
            response = requests.post(f"{url}/api/v2/query?org={org}", headers=headers, data=custom_query)
            response.raise_for_status()
            if not response.text.strip():
                Log.I("InfluxDB returned an empty response. No data to write.")
                return
            with open(output_file, "w", encoding="utf-8", newline='') as f:
                f.write(response.text)
            if os.path.getsize(output_file) == 0:
                Log.I("CSV file is empty after saving. Skipping parsing.")
                return
            df = pd.read_csv(output_file)
            df.dropna(axis=1, how='all', inplace=True)
            columns_to_drop = ["_start", "_stop", "result", "table"]
            df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)
            df.to_csv(output_file, index=False)

            with open(output_file, 'r', encoding='utf-8') as infile:
                lines = infile.readlines()
            with open(output_file, 'w', encoding='utf-8') as outfile:
                for line in lines:
                    if line.strip().strip(','):
                        outfile.write(line)
            Log.I(f"Data successfully exported and processed to {output_file} from InfluxDB v2.x")
        except requests.exceptions.RequestException as e:
            Log.I(f"Error exporting data from InfluxDB v2.x: {e}")

    def is_influxdb_v1_receiving_data(url, database, user, password, execution_id, time_window):

        query_params = {
            "db": database,
            "q": f"SELECT * FROM /.*/ WHERE time > now() - {time_window}s AND ExecutionId = '{execution_id}' LIMIT 1"
        }

        headers = {"Accept": "application/csv"}

        try:
            response = requests.get(f"{url}/query", params=query_params, headers=headers, auth=(user, password))
            response.raise_for_status()
            return bool(response.text.strip())
        except requests.exceptions.RequestException:
            return False

    def is_influxdb_v2_receiving_data(url, bucket, token, org, execution_id, time_window):
        
        flux_query = f"""
        from(bucket: "{bucket}")
        |> range(start: -{time_window}s)
        |> filter(fn: (r) => r["ExecutionId"] == "{execution_id}")
        |> limit(n: 1)
        """
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/vnd.flux"
        }

        try:
            response = requests.post(f"{url}/api/v2/query?org={org}", headers=headers, data=flux_query)
            response.raise_for_status()
            return bool(response.text.strip())
        except requests.exceptions.RequestException:
            return False
