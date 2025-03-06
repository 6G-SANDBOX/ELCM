import subprocess
import re
import platform

from Executor import PreRunner, Executor, PostRunner, ExecutorBase, Verdict
from Data import ExperimentDescriptor
from typing import Dict, Optional, List
from enum import Enum, unique
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from Helper import Serialize, Log
from Settings import Config
from Interfaces import PortalApi
from Composer import Composer, PlatformConfiguration
from os.path import join, abspath
from Helper import Cli


@unique
class CoarseStatus(Enum):
    Init, PreRun, Run, PostRun, Finished, Cancelled, Errored = range(7)


class ExperimentRun:
    portal: PortalApi = None
    grafana = None

    def __init__(self, id: int, params: Dict):
        self.Id = id
        self.Params = params
        self.Params['ExecutionId'] = self.Id
        self.Params['Configuration'] = Composer.Compose(self.Descriptor)
        self.TempFolder = TemporaryDirectory(dir=Config().TempFolder)
        self.PreRunner = PreRunner(self.Params, tempFolder=self.TempFolder)
        self.Executor = Executor(self.Params, tempFolder=self.TempFolder)
        self.PostRunner = PostRunner(self.Params, tempFolder=self.TempFolder)
        self._coarseStatus = CoarseStatus.Init
        self._dashboardUrl = None
        self.Cancelled = False
        self.Milestones = []
        self.RemoteApi = None
        self.RemoteId = None
        self.Created = datetime.now(timezone.utc)

        if ExperimentRun.portal is None or ExperimentRun.grafana is None:
            from Helper import DashboardGenerator  # Delayed to avoid cyclic imports
            config = Config()
            ExperimentRun.portal = PortalApi(config.Portal)
            ExperimentRun.grafana = DashboardGenerator(config.Grafana.Enabled, config.Grafana.Host,
                                                       config.Grafana.Port, config.Grafana.Bearer,
                                                       config.Grafana.ReportGenerator)

    def __str__(self):
        return f'[ID: {self.Id} ({self.ExperimentIdentifier})]'

    @property
    def ExecutionId(self):
        return self.Id

    @property
    def IsRemoteMaster(self) -> bool:
        return (self.Descriptor.RemoteDescriptor is not None) if self.Descriptor is not None else False

    @property
    def GeneratedFiles(self):
        return list(filter(None,
                           [self.PreRunner.LogFile, self.Executor.LogFile, self.PostRunner.LogFile,
                            *self.PreRunner.GeneratedFiles, *self.Executor.GeneratedFiles,
                            *self.PostRunner.GeneratedFiles]))

    @property
    def ExperimentIdentifier(self):
        return self.Descriptor.Identifier if self.Descriptor is not None else None

    @property
    def CoarseStatus(self):
        return self._coarseStatus

    @CoarseStatus.setter
    def CoarseStatus(self, value: CoarseStatus):
        if value != self._coarseStatus:
            self._coarseStatus = value
            ExperimentRun.portal.UpdateExecutionData(self.Id, status=value.name)
            if value.name not in self.Milestones:
                self.Milestones.append(value.name)

    @property
    def DashboardUrl(self):
        return self._dashboardUrl

    @DashboardUrl.setter
    def DashboardUrl(self, value: str):
        if value != self._dashboardUrl:
            self._dashboardUrl = value
            ExperimentRun.portal.UpdateExecutionData(self.Id, dashboardUrl=value)

    @property
    def Status(self) -> str:
        if self.CoarseStatus == CoarseStatus.PreRun:
            return f'PreRun: {self.PreRunner.Status.name}'
        elif self.CoarseStatus == CoarseStatus.Run:
            return f'Run: {self.Executor.Status.name}'
        elif self.CoarseStatus == CoarseStatus.PostRun:
            return f'PostRun: {self.PostRunner.Status.name}'
        else:
            return self.CoarseStatus.name

    @property
    def PerCent(self) -> int:
        current = self.CurrentChild
        return current.PerCent if current is not None else 0

    @property
    def Verdict(self) -> Verdict:
        return self.Executor.Verdict  # Pre/PostRun do not modify the verdict

    @property
    def LastMessage(self) -> str:
        current = self.CurrentChild
        return current.LastMessage if current is not None else 'No active child'

    @property
    def Messages(self) -> [str]:
        current = self.CurrentChild
        return current.Messages if current is not None else []

    @property
    def Active(self) -> bool:
        return self.CoarseStatus.value < CoarseStatus.Finished.value

    @property
    def Descriptor(self) -> Optional[ExperimentDescriptor]:
        return self.Params.get('Descriptor', None)

    @property
    def JsonDescriptor(self) -> Dict:
        return self.Descriptor.Json

    @property
    def Configuration(self) -> Optional[PlatformConfiguration]:
        return self.Params.get('Configuration', None)

    @property
    def CurrentChild(self) -> Optional[ExecutorBase]:
        if self.CoarseStatus == CoarseStatus.PreRun: return self.PreRunner
        if self.CoarseStatus == CoarseStatus.Run: return self.Executor
        if self.CoarseStatus == CoarseStatus.PostRun: return self.PostRunner
        return None

    def Cancel(self):
        current = self.CurrentChild
        if current is not None:
            current.RequestStop()
        self.CoarseStatus = CoarseStatus.Cancelled

        device = self.Params.get("DeviceId", None)
        if device is not None:
            self.AppEviction(device)
            self.TapEviction()
        if not self.PostRunner.hasStarted:
            self.PostRunner.Start()  

    def PreRun(self):
        self.CoarseStatus = CoarseStatus.PreRun
        self.PreRunner.Start()

    def Run(self):
        self.CoarseStatus = CoarseStatus.Run
        self.Executor.Start()

    def PostRun(self):
        self.CoarseStatus = CoarseStatus.PostRun
        self.PostRunner.Start()

    def Advance(self):
        if not self.Active:
            return
        elif self.CoarseStatus == CoarseStatus.Init:
            self.PreRun()
        elif self.CoarseStatus == CoarseStatus.PreRun:
            if self.PreRunner.HasFailed:
                self.CoarseStatus = CoarseStatus.Errored
                Log.I(f'Execution {self.Id} has failed on PreRun')
                self.handleExecutionEnd()
                return
            if self.PreRunner.Finished:
                self.Run()
        elif self.CoarseStatus == CoarseStatus.Run:
            if self.Executor.HasFailed:
                self.CoarseStatus = CoarseStatus.Errored
                Log.I(f'Execution {self.Id} has failed on Run')
                self.handleExecutionEnd()
                return
            if self.Executor.Finished:
                self.PostRun()
        elif self.CoarseStatus == CoarseStatus.PostRun:
            if self.PostRunner.HasFailed or self.PostRunner.Finished:
                if self.PostRunner.HasFailed:
                    Log.I(f'Execution {self.Id} has failed on Run')
                self.CoarseStatus = CoarseStatus.Errored if self.PostRunner.HasFailed else CoarseStatus.Finished
                self.handleExecutionEnd()

    def handleExecutionEnd(self):
        allFiles = self.GeneratedFiles

        # Handle results from the remote side
        if self.RemoteId is not None and self.IsRemoteMaster:
            if Config().InfluxDb.Enabled:
                from Helper import InfluxDb, InfluxPayload
                influx = InfluxDb()
                Log.I(f'Trying to retrieve results from remote side database.')
                results: List[InfluxPayload] = self.RemoteApi.GetResults(self.RemoteId)
                Log.D(f'Retrieved {len(results)} payloads: {([p.Measurement for p in results])}')
                for payload in results:
                    payload.Measurement = f"Remote_{payload.Measurement}"
                    payload.Tags['ExecutionId'] = str(self.ExecutionId)
                    influx.Send(payload)
                    Log.D(f"Sent '{payload.Measurement}' payload to database")

            Log.I(f'Trying to retrieve remote side files.')
            file = self.RemoteApi.GetFiles(self.RemoteId, self.TempFolder.name)
            if file is not None:
                allFiles.append(file)
            else:
                Log.W("Could not retrieve remote side files.")

        # Compress all generated files
        try:
            from Helper import Compress, IO
            Log.I(f"Experiment generated files: {allFiles}")
            folder = abspath(Config().ResultsFolder)
            IO.EnsureFolder(folder)
            path = join(folder, f"{self.Id}.zip")
            Compress.Zip(allFiles, path, flat=True)
        except Exception as e:
            Log.E(f"Exception while compressing experiment files ({self.Id}): {e}")

        # Try to create the dashboard even in case of error, there might be results to display
        try:
            Log.D(f"Automatically generating panels from log (AutoGraph) {self.Id}")
            from Helper import AutoGraph
            generated = AutoGraph.GeneratePanels(self.Configuration.DashboardPanels, self.Executor.RetrieveLogInfo())
            self.Configuration.DashboardPanels.extend(generated)

            if self.Executor.Started is not None:
                Log.D(f"Trying to generate dashboard for execution {self.Id}")
                self.Configuration.ExpandDashboardPanels(self)
                url = ExperimentRun.grafana.Create(self)
                self.DashboardUrl = url
            else:
                Log.D(f"Execution {self.Id} aborted during Pre-Run, skipping dashboard generation")
        except Exception as e:
            Log.E(f"Exception while handling execution end ({self.Id}): {e}")
        finally:
            Log.D(f"Clearing temp folder for execution {self.Id}")
            self.TempFolder.cleanup()

    def Serialize(self) -> Dict:
        data = {
            'Id': self.Id,
            'Created': Serialize.DateToString(self.Created),
            'CoarseStatus': self.CoarseStatus.name,
            'Cancelled': self.Cancelled,
            'JsonDescriptor': self.Descriptor.Json,
            'Milestones': self.Milestones,
            'RemoteId': self.RemoteId,
            'Verdict': self.Verdict.name
        }
        return data

    def Save(self):
        self.PreRunner.Save()
        self.Executor.Save()
        self.PostRunner.Save()
        data = self.Serialize()
        path = Serialize.Path('Execution', str(self.Id))
        Serialize.Save(data, path)

    @classmethod
    def Digest(cls, id: str) -> Dict:
        return Serialize.Load(Serialize.Path('Execution', id))

    @staticmethod
    def AppEviction(device_id):
        commands = f'adb -s {device_id} shell pm list packages'
        pattern = r"(.*)(com.uma.(.*))"
        process = subprocess.Popen(commands.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='.')
        pipe = process.stdout

        for line in iter(pipe.readline, b''):
            try:
                result = re.search(pattern, line.decode('utf-8'))
                if result:
                    app_stop_command = f'adb -s {device_id} shell am force-stop {result.group(2)}'
                    subprocess.Popen(app_stop_command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='.')
                    Log.I(f"Package {result.group(2)} stopped.")
            except Exception as e:
                Log.E(f"DECODING EXCEPTION: {e}")

    @staticmethod
    def TapEviction():
        if platform.system() == 'Linux':
            pass
        elif platform.system() == 'Windows':
            tap_stop_command = f'taskkill /IM "tap.exe" /F'
            subprocess.run(tap_stop_command, shell=True)
