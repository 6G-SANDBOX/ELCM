from Task import Task
from Interfaces import Management
from Helper import Level
from time import sleep
from datetime import datetime


class SingleSliceCreationTime(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Single Slice Creation Time Measurement", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),
            'WaitForRunning': (None, True),
            'SliceId': (None, True),
            'Timeout': (None, False)
        }

    def Run(self):
        executionId = self.params['ExecutionId']
        waitForRunning = self.params['WaitForRunning']
        timeout = self.params['Timeout']
        sliceId = self.params['SliceId']
        count = 0

        if waitForRunning:
            self.Log(Level.INFO, f"Waiting for slice to be running. Timeout: {timeout}")
            while True:
                count += 1
                status = Management.SliceManager().CheckSlice(sliceId).get('status', '<SliceManager check error>')
                self.Log(Level.DEBUG, f'Slice {sliceId} status: {status} (retry {count})')
                if status == 'Running' or (timeout is not None and count >= timeout): break
                else: sleep(1)

        self.Log(Level.INFO, f"Reading deployment times for slice {sliceId}")
        times = Management.SliceManager().SliceCreationTime(sliceId)
        self.Log(Level.DEBUG, f"Received times: {times}")

        self.Log(Level.INFO, f"Generating results payload")
        from Helper import InfluxDb, InfluxPayload, InfluxPoint  # Delayed to avoid cyclic imports

        payload = InfluxPayload("Single Slice Creation Time")
        payload.Tags = {'ExecutionId': str(executionId)}
        point = InfluxPoint(datetime.utcnow())

        for key in ["Slice_Deployment_Time", "Placement_Time", "Provisioning_Time"]:
            value = times.get(key, "N/A")
            if value != "N/A":
                try:
                    point.Fields[key] = float(value)
                except ValueError as e:
                    self.Log(Level.DEBUG, f"Unable to parse {key} ({value}): {e}")

        payload.Points.append(point)
        self.Log(Level.DEBUG, f"Payload: {payload}")
        self.Log(Level.INFO, f"Sending results to InfluxDb")
        InfluxDb.Send(payload)

        # TODO: Artificial wait until the slice is 'configured'
        # TODO: In the future the slice manager should also report this status
        sleep(60)
