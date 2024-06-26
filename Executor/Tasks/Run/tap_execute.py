from Task import Task
from Helper import Tap, Level
from Settings import Config
from os.path import exists, join
from datetime import datetime, timezone


class TapExecute(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Tap Execute", parent, params, logMethod, None)
        self.paramRules = {
            'TestPlan': (None, True),
            'Externals': ({}, False),
            'GatherResults': (False, False)
        }

    def Run(self):
        from Helper import IO, Compress
        config = Config().Tap

        if not config.Enabled:
            self.Log(Level.CRITICAL, "Trying to run TapExecute Task while TAP is not enabled")
            self.SetVerdictOnError()
        else:
            tapPlan = self.params['TestPlan']
            externals = self.params['Externals']
            gatherResults = self.params['GatherResults']

            tap = Tap(tapPlan, externals, self.Log)
            tap.Execute()

            if gatherResults:
                self.Log(Level.INFO, "Collecting generated CSV files...")
                path = join(config.Results, str(self.parent.ExecutionId))
                if exists(path):
                    self.Log(Level.DEBUG, f"Searching on path {path}")
                    try:
                        files = IO.GetAllFiles(path)
                        time = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
                        output = join(self.parent.TempFolder, f"Results{time}.zip")
                        if len(files) != 0:
                            Compress.Zip(files, output)
                            self.parent.GeneratedFiles.append(output)
                            self.Log(Level.INFO, f"Saved {len(files)} files to {output}")
                    except Exception as e:
                        self.SetVerdictOnError()
                        self.Log(Level.ERROR, f"Exception while compressing results: {e}")
                else:
                    self.Log(Level.WARNING, f"Results path ({path}) does not exist.")
            else:
                self.Log(Level.INFO, "Results collection disabled, skipping.")

