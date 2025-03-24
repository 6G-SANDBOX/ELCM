from Task import Task
from Helper import Level
from time import sleep


class Delay(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Delay", parent, params, logMethod, None)
        self.paramRules = {'Time': (60, False)}

    def Run(self):
        value = self.params['Time']
        try:
            time = int(value)
            if time < 0:
                raise ValueError
        except ValueError:
            self.Log(Level.ERROR, f"{value} is not a valid number of seconds")
            self.SetVerdictOnError()
            return

        self.Log(Level.INFO, f'Waiting for {time} seconds')
        for _ in range(time):
            sleep(1)
            if self.parent.stopRequested:
                break
