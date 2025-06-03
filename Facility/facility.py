import os
from .action_information import ActionInformation
from .dashboard_panel import DashboardPanel
from .resource import Resource
from Helper import Log, Level
from typing import Dict, List, Tuple, Optional
from threading import Lock
from Utils import synchronized
from .Loader import Loader, ResourceLoader, ScenarioLoader, UeLoader, TestCaseLoader


class Facility:
    lock = Lock()
    requesters: Dict[str, List[str]] = {}
    activeExperiments: List[str] = []
    activeExclusive: Optional[str] = None

    TESTCASE_FOLDER = os.path.abspath('TestCases')
    UE_FOLDER = os.path.abspath('UEs')
    RESOURCE_FOLDER = os.path.abspath('Resources')
    SCENARIO_FOLDER = os.path.abspath('Scenarios')

    ues: Dict[str, List[ActionInformation]] = {}
    testCases: Dict[str, List[ActionInformation]] = {}
    extra: Dict[str, Dict[str, object]] = {}
    dashboards: Dict[str, List[DashboardPanel]] = {}
    kpis: Dict[str, List[Tuple[str, str, str, str]]] = {}
    resources: Dict[str, Resource] = {}
    scenarios: Dict[str, List[ActionInformation]] = {}

    Validation: List[Tuple[Level, str]] = []

    @classmethod
    def testcase_folder(cls, user_id: str) -> str:
        
        try:
            user_id_int = int(user_id)
            if user_id_int < 0:
                raise ValueError
            sub = str(user_id_int)
        except (ValueError, TypeError):
            raise ValueError("user_id must be a non-negative integer")

        path = os.path.join(cls.TESTCASE_FOLDER, sub)
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def ue_folder(cls, user_id: str) -> str:
        
        try:
            user_id_int = int(user_id)
            if user_id_int < 0:
                raise ValueError
            sub = str(user_id_int)
        except (ValueError, TypeError):
            raise ValueError("user_id must be a non-negative integer")

        path = os.path.join(cls.UE_FOLDER, sub)
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def Reload(cls):
        cls.Validation.clear()

        # Generate missing folders
        for folder in [cls.TESTCASE_FOLDER, cls.UE_FOLDER, cls.RESOURCE_FOLDER, cls.SCENARIO_FOLDER]:
            v = Loader.EnsureFolder(folder)
            cls.Validation.extend(v)

        resources = cls.resources
        if len(cls.BusyResources()) != 0:
            cls.Validation.append((Level.WARNING, "Resources in use, skipping reload"))
        else:
            ResourceLoader.Clear()
            v = ResourceLoader.LoadFolder(cls.RESOURCE_FOLDER, "Resource")
            cls.Validation.extend(v)
            resources = ResourceLoader.GetCurrentResources()

        # Load TestCases from all subfolders (users)
        TestCaseLoader.Clear()
        if os.path.isdir(cls.TESTCASE_FOLDER):
            for sub in os.listdir(cls.TESTCASE_FOLDER):
                sub_path = os.path.join(cls.TESTCASE_FOLDER, sub)
                if os.path.isdir(sub_path):
                    v = TestCaseLoader.LoadFolder(sub_path, "TestCase")
                    cls.Validation.extend(v)

        # Load UEs from all subfolders (users)
        UeLoader.Clear()
        if os.path.isdir(cls.UE_FOLDER):
            for sub in os.listdir(cls.UE_FOLDER):
                sub_path = os.path.join(cls.UE_FOLDER, sub)
                if os.path.isdir(sub_path):
                    v = UeLoader.LoadFolder(sub_path, "UE")
                    cls.Validation.extend(v)

        ScenarioLoader.Clear()
        v = ScenarioLoader.LoadFolder(cls.SCENARIO_FOLDER, "Scenario")
        cls.Validation.extend(v)

        cls.resources = resources
        cls.testCases = TestCaseLoader.GetCurrentTestCases()
        cls.extra = TestCaseLoader.GetCurrentTestCaseExtras()
        cls.dashboards = TestCaseLoader.GetCurrentDashboards()
        cls.kpis = TestCaseLoader.GetCurrentTestCaseKPIs()
        cls.ues = UeLoader.GetCurrentUEs()
        cls.scenarios = ScenarioLoader.GetCurrentScenarios()

        for collection, name in [(cls.testCases, "TestCases"), (cls.ues, "UEs"),
                                 (cls.dashboards, "DashBoards"), (cls.resources, "Resources"),
                                 (cls.scenarios, "Scenarios")]:
            keys = collection.keys()
            if len(keys) == 0:
                cls.Validation.append((Level.WARNING, f'No {name} defined on the facility.'))
            else:
                cls.Validation.append((Level.INFO, f'{len(keys)} {name} defined on the facility: {(", ".join(keys))}.'))

    @classmethod
    def GetUEActions(cls, id: str) -> List[ActionInformation]:
        return cls.ues.get(id, [])

    @classmethod
    def GetTestCaseActions(cls, id: str) -> List[ActionInformation]:
        return cls.testCases.get(id, [])

    @classmethod
    def GetScenarioActions(cls, id: str) -> List[ActionInformation]:
        return cls.scenarios.get(id, [])

    @classmethod
    def GetMonroeActions(cls) -> List[ActionInformation]:
        return cls.testCases.get("MONROE_Base", [])

    @classmethod
    def GetTestCaseDashboards(cls, id: str) -> List[DashboardPanel]:
        return cls.dashboards.get(id, [])

    @classmethod
    def GetTestCaseExtra(cls, id: str) -> Dict[str, object]:
        return cls.extra.get(id, {})

    @classmethod
    def GetTestCaseKPIs(cls, id: str) -> List[Tuple[str, str, str, str]]:
        return cls.kpis.get(id, [])

    @classmethod
    def BusyResources(cls) -> List[Resource]:
        return [res for res in cls.resources.values() if res.Locked]

    @classmethod
    def IdleResources(cls) -> List[Resource]:
        return [res for res in cls.resources.values() if not res.Locked]

    @classmethod
    def Resources(cls):
        return cls.resources

    @classmethod
    def Scenarios(cls):
        return cls.scenarios

    @classmethod
    @synchronized(lock)
    def TryLockResources(cls, ids: List[str], owner: 'ExecutorBase', exclusive: bool) -> bool:
        executor = owner.ExecutionId
        resources: List[Resource] = list(filter(None, [cls.resources.get(id, None) for id in ids]))
        resourceIds = [resource.Id for resource in resources]
        lockedResources: List[str] = []

        if owner.ExecutionId not in cls.requesters.keys():
            cls.requesters[executor] = resourceIds

        # For exclusive experiments check if something else is running
        if exclusive and len(cls.activeExperiments) != 0:
            Log.D(f"Resources denied to {executor}: Requests exclusive execution ({len(cls.activeExperiments)} active)")
            return False

        # For non exclusive experiments check if an exclusive experiment is running
        if not exclusive and cls.activeExclusive is not None:
            Log.D(f"Resources denied to {executor}: Exclusive execution {cls.activeExclusive} in progress")
            return False

        # Check if some of the required resources are already locked
        for resource in resources:
            if resource.Locked:
                Log.D(f"Resources denied to {executor}: {resource.Id} already locked by {resource.Owner.ExecutionId}")
                return False

        # Check if some earlier experiment is requesting the same resources
        for key, values in cls.requesters.items():
            if key < executor:  # Check only older executors
                intersect = list(set(values) & set(resourceIds))
                if len(intersect) != 0:
                    Log.D(f"Resources denied to {executor} due to conflict with {key} ({intersect})")
                    return False

        # Try to lock all the required resources
        for id in resourceIds:
            success = cls.LockResource(id, owner)
            if success:
                lockedResources.append(id)
            if not success:
                Log.W(f"Could not lock resource '{id}'. Rolling back.")
                cls._releaseResources(lockedResources)
                return False

        if exclusive:
            cls.activeExclusive = owner.ExecutionId
        cls.activeExperiments.append(owner.ExecutionId)

        return True

    @classmethod
    @synchronized(lock)
    def ReleaseResources(cls, ids: List[str], owner: 'ExecutorBase'):
        execution = owner.ExecutionId
        _ = cls.requesters.pop(execution, None)
        cls._releaseResources(ids)

        if execution == cls.activeExclusive:
            cls.activeExclusive = None
        try:
            cls.activeExperiments.remove(execution)
        except ValueError: pass

    @classmethod
    def _releaseResources(cls, ids: List[str]):
        for resource in ids:
            cls.ReleaseResource(resource)

    @classmethod
    def LockResource(cls, id: str, owner: 'ExecutorBase') -> bool:
        resource = cls.resources.get(id, None)
        if resource is not None:
            if not resource.Locked:
                resource.Owner = owner
                Log.I(f"Resource '{resource.Name}'({resource.Id}) locked by {resource.Owner.ExecutionId}")
                return True
            else:
                Log.E(f"Unable to lock resource '{resource.Name}'({resource.Id}) for run {owner.ExecutionId}, "
                      f"locked by '{resource.Owner.ExecutionId}")
        else:
            Log.E(f"Resource id {id} not found")
        return False

    @classmethod
    def ReleaseResource(cls, id: str) -> bool:
        resource = cls.resources.get(id, None)
        if resource is not None:
            if resource.Locked:
                Log.I(f"Releasing '{resource.Name}'({resource.Id}) "
                      f"(locked by '{resource.Owner.ExecutionId}'))")
                resource.Owner = None
                return True
            else:
                Log.W(f"Tried to release resource {id} while idle")
        else:
            Log.E(f"Resource id {id} not found")
        return False
