from Task import Task
from Helper import influx
from datetime import timezone, datetime
from typing import Union, Dict, Any

class ToInfluxBase(Task):
    def __init__(self, name, parent, params, logMethod, conditionMethod):
        super().__init__(name, parent, params, logMethod, conditionMethod)

    def _convert(self,value: Any) -> Union[int, float, bool, str, Dict[str, Any]]:
        
        if isinstance(value, str):
            
            try:
                return float(value)
            except ValueError:
                pass

            
            lower_value = value.lower()
            if lower_value in {'true', 'false'}:
                
                if lower_value=='true':
                    return True
                else:
                    return False

            
            return value

        elif isinstance(value, dict):
            
            converted_dict = {}
            for key, val in value.items():
                converted_dict[key] = self._convert(val)  
            return converted_dict

        else:

            return value

    def _send_to_influx(self,measurement,data,timestamp,executionId,convert=True):
    
        if timestamp is None:
            raise Exception("No timestamp")
        
        if convert:
            data=self._convert(data)
        

        influx_point = influx.InfluxPoint(datetime.fromtimestamp(timestamp, tz=timezone.utc))
        influx_point.Fields = data

        influx_payload = influx.InfluxPayload(measurement)
        influx_payload.Tags = {'ExecutionId': str(executionId), **influx.InfluxDb.BaseTags()}
        influx_payload.Points.append(influx_point)


        influx.InfluxDb.Send(influx_payload)


    def _flatten_json(self,nested_json, parent_key='', sep='_', timestamp_key='timestamp', root_timestamp=None):
        data_with_timestamps = []

        if parent_key == '' and root_timestamp==None:
            root_timestamp = nested_json.get(timestamp_key, None)

        for key, value in nested_json.items():
            new_key = parent_key + sep + key if parent_key else key

            if isinstance(value, dict):
                data_with_timestamps.extend(self._flatten_json(value, new_key, sep=sep, timestamp_key=timestamp_key, root_timestamp=root_timestamp))
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    data_with_timestamps.extend(self._flatten_json({f'{new_key}_{i}': v}, '', sep=sep, timestamp_key=timestamp_key, root_timestamp=root_timestamp))
            else:
                if timestamp_key not in new_key:
                    timestamp = nested_json.get(timestamp_key, root_timestamp)
                    data_with_timestamps.append((new_key, value, timestamp))
                
        return data_with_timestamps



    def _flatten_prometheus_json(self,nested_json, parent_key='', sep='_'):
        items = []
        for key, value in nested_json.items():
            new_key = parent_key + sep + key if parent_key else key
            if isinstance(value, dict):
                items.extend(self._flatten_prometheus_json(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    
                    if isinstance(v, list) and len(v) == 2:
                        
                        timestamp_key = f'{new_key}_timestamp_{i}'
                        value_key = f'{new_key}_value_{i}'
                        items.append((timestamp_key, v[0]))
                        items.append((value_key, v[1]))
                    else:
                        items.extend(self._flatten_prometheus_json({f'{new_key}_{i}': v}, '', sep=sep).items())
            else:
                items.append((new_key, value))
        return dict(items)


    def _flatten_telegraf_json(self,nested_json, parent_key='', sep='_'):
        items = []
        
        name = nested_json.get('name', None)
        
        for key, value in nested_json.items():
            if parent_key:
                new_key = parent_key + sep + key
            else:
                new_key = key
            
            if isinstance(value, dict):
                if key == 'fields' and name:
                    for field_key, field_value in value.items():
                        new_field_key = f'{parent_key}{sep}{field_key}_{name}' if parent_key else f'{field_key}_{name}'
                        items.append((new_field_key, field_value))
                else:
                    items.extend(self._flatten_telegraf_json(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    if isinstance(v, dict):
                        items.extend(self._flatten_telegraf_json({f'{new_key}_{i}': v}, '', sep=sep).items())
                    else:
                        items.append((f'{new_key}_{i}', v))
            else:
                items.append((new_key, value))
        
        return dict(items)