from Helper import Child, Level
from Settings import Config
from typing import Dict, Optional, List
from Data import ExperimentDescriptor
from Composer import PlatformConfiguration
from datetime import datetime, timezone
from Helper import Serialize
from .enums import Status, Verdict
from tempfile import TemporaryDirectory
from Interfaces import PortalApi


class ExecutorBase(Child):
    portal: PortalApi = None

    def __init__(self, params: Dict, name: str, tempFolder: TemporaryDirectory = None):
        if self.portal is None:
            config = Config()
            self.portal = PortalApi(config.Portal)

        now = datetime.now(timezone.utc)
        super().__init__(f"{name}{now.strftime('%y%m%d%H%M%S%f')}", tempFolder)
        self.Tag = name
        self.params = params
        self.ExecutionId: int = params['ExecutionId']
        self.Created = now
        self.Started = None
        self.Finished = None
        self.GeneratedFiles: List[str] = []
        self.Status = Status.Init
        self.Messages = []
        self.PerCent = 0
        self.Verdict = Verdict.NotSet
        if not self.params.get('Deserialized', False):
            self.AddMessage("Init")

    @property
    def Params(self) -> Dict:
        return self.params

    @property
    def HasFailed(self) -> bool:
        return self.hasFailed

    @property
    def Descriptor(self) -> Optional[ExperimentDescriptor]:
        return self.params.get('Descriptor', None)

    @property
    def Configuration(self) -> Optional[PlatformConfiguration]:
        return self.params.get('Configuration', None)

    @property
    def DeployedSliceId(self) -> Optional[str]:
        return self.params.get('DeployedSliceId', None)


    @property
    def PreviousTaskLog(self) -> List[str]:
        return self.params.get('PreviousTaskLog', [])

    def Run(self):
        raise NotImplementedError()

    def AddMessage(self, msg: str, percent: int = None):
        if percent is not None: self.PerCent = percent
        self.Messages.append(f'[{self.PerCent}%] {msg}')
        self.portal.UpdateExecutionData(self.ExecutionId, percent=self.PerCent, message=msg)

    @property
    def LastMessage(self):
        return self.Messages[-1]

    def LogAndMessage(self, level: Level, msg: str, percent: int = None):
        self.Log(level, msg)
        self.AddMessage(msg, percent)

    def SetStarted(self):
        self.LogAndMessage(Level.INFO, "Started")
        self.Started = datetime.now(timezone.utc)
        self.Status = Status.Running

    def SetFinished(self, status=Status.Finished, percent: int = None):
        self.Finished = datetime.now(timezone.utc)
        if self.Status.value < Status.Cancelled.value:
            self.Status = status
        self.LogAndMessage(Level.INFO, f"Finished (status: {self.Status.name}, verdict: {self.Verdict.name})", percent)

    def findParent(self):  # Only running experiments should be able to use this method
        from Status import ExecutionQueue
        return ExecutionQueue.Find(self.ExecutionId)

    def AddMilestone(self, milestone: str):
        parent = self.findParent()
        if parent is not None:
            parent.Milestones.append(milestone)
            parent.Tasks.append(milestone)

    def ReadMilestone(self, milestone: str) -> bool:
        parent = self.findParent()
        if parent is not None:
            return milestone in parent.Milestones
        return False
    
    def RemoveMilestone(self, milestone: str):
        parent = self.findParent()
        if parent is not None and milestone in parent.Milestones:
            parent.Milestones.remove(milestone)
            parent.Tasks.remove(milestone)

    def TaskList(self):
        parent = self.findParent()
        return parent.Tasks
    
    @property
    def RemoteApi(self):
        parent = self.findParent()
        if parent is not None:
            return parent.RemoteApi
        return None

    @RemoteApi.setter
    def RemoteApi(self, api):
        parent = self.findParent()
        if parent is not None:
            parent.RemoteApi = api

    @property
    def RemoteId(self):
        parent = self.findParent()
        if parent is not None:
            return parent.RemoteId
        return None

    @RemoteId.setter
    def RemoteId(self, peerId):
        parent = self.findParent()
        if parent is not None:
            parent.RemoteId = peerId

    def Serialize(self) -> Dict:
        data = {
            'ExecutionId': self.ExecutionId,
            'Name': self.name,
            'Tag': self.Tag,
            'Created': Serialize.DateToString(self.Created),
            'Started': Serialize.DateToString(self.Started),
            'Finished': Serialize.DateToString(self.Finished),
            'HasStarted': self.hasStarted,
            'HasFinished': self.hasFinished,
            'GeneratedFiles': self.GeneratedFiles,
            'Status': self.Status.name,
            'Log': self.LogFile,
            'Messages': self.Messages,
            'PerCent': self.PerCent,
            'Verdict': self.Verdict.name
        }
        return data

    def Save(self):
        data = self.Serialize()
        path = Serialize.Path(self.Tag, str(self.ExecutionId))
        Serialize.Save(data, path)

    @classmethod
    def Load(cls, tag: str, id: str):
        path = Serialize.Path(tag, id)
        data = Serialize.Load(path)
        tag = data['Tag']
        params = {'ExecutionId': int(id), 'Deserialized': True}
        if tag == 'PreRunner':
            from .pre_runner import PreRunner
            res = PreRunner(params)
        elif tag == 'Executor':
            from .executor import Executor
            res = Executor(params)
        else:
            from .post_runner import PostRunner
            res = PostRunner(params)

        res.ExecutionId = data.get('ExecutionId', data.get('Id'))  # For compatibility with older serialization
        res.Name, res.LogFile, res.Tag = Serialize.Unroll(data, 'Name', 'Log', 'Tag')
        res.hasStarted, res.hasFinished = Serialize.Unroll(data, 'HasStarted', 'HasFinished')
        res.Messages, res.PerCent, res.GeneratedFiles = Serialize.Unroll(data, 'Messages', 'PerCent', "GeneratedFiles")
        res.Created = Serialize.StringToDate(data['Created'])
        res.Started = Serialize.StringToDate(data['Started'])
        res.Finished = Serialize.StringToDate(data['Finished'])
        res.Status = Status[data['Status']]
        res.Verdict = Verdict[data.get('Verdict', 'NotSet')]

        return res
