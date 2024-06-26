from typing import List, ClassVar, Dict, Optional
from Facility import DashboardPanel
from Data import NsInfo


class TaskDefinition:
    def __init__(self):
        self.Task: ClassVar = None
        self.Params: Dict = {}
        self.Label: str = ''
        self.Children: List[TaskDefinition] = []

    def GetTaskInstance(self, logMethod, parent, params):
        taskInstance = self.Task(logMethod, parent, params)
        taskInstance.Label = self.Label
        taskInstance.Children = self.Children
        return taskInstance


class PlatformConfiguration:
    def __init__(self):
        self.PreRunParams = {}
        self.RunParams = {}
        self.PostRunParams = {}
        self.RunTasks: List[TaskDefinition] = []
        self.DashboardPanels: List[DashboardPanel] = []
        self.Requirements: List[str] = []
        self.NetworkServices: List[NsInfo] = []
        self.Nest: Optional[Dict] = None

    def ExpandDashboardPanels(self, experimentRun):
        from Experiment import Expander
        newPanels = []
        for panel in self.DashboardPanels:
            newPanel = DashboardPanel(Expander.ExpandDict(panel.AsDict(), context=experimentRun))
            newPanels.append(newPanel)
        self.DashboardPanels = newPanels