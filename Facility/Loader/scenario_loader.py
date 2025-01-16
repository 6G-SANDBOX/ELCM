from Helper import Level
from .loader_base import Loader
from .testcase_loader import TestCaseLoader, TestCaseData
from ..action_information import ActionInformation
from typing import Dict, List


class ScenarioLoader(TestCaseLoader):
    scenarios: Dict[str, List[ActionInformation]] = {}

    @classmethod
    def ProcessData(cls, data: Dict) -> [(Level, str)]:
        version = str(data.pop('Version', 1))

        match version:
            case '1':
                return cls.processV1ScenarioData(data)
            case '2':
                return cls.processV2ScenarioData(data)
            case _:
                raise RuntimeError(f"Unknown scenario version '{version}'.")

    @classmethod
    def processV1ScenarioData(cls, data: Dict) -> [(Level, str)]:
        validation = []
        defs = TestCaseData(data)

        if defs.Dashboard is None:
            validation.append((Level.WARNING, f'Dashboard not defined. Keys: {defs.AllKeys}'))

        validation.extend(
            cls.handleExperimentType(defs))

        keys = list(data.keys())

        if len(keys) > 1:
            validation.append((Level.ERROR, f'Multiple Scenarios defined on a single file: {list(keys)}'))

        for key in keys:
            cls.scenarios[key], v = cls.GetActionList(data[key])
            validation.extend(v)

            cls.createExtra(key, defs)

            validation.extend(
                cls.createDashboard(key, defs))

            validation.extend(
                cls.validateParameters(defs))

        return validation

    @classmethod
    def processV2ScenarioData(cls, data: Dict) -> [(Level, str)]:
        validation = []
        defs = TestCaseData(data)

        validation.extend(
            cls.handleExperimentType(defs))

        cls.scenarios[defs.Name], v = cls.GetActionList(defs.Sequence)
        validation.extend(v)

        cls.createExtra(defs.Name, defs)

        validation.extend(
            cls.createDashboard(defs.Name, defs))

        validation.extend(
            cls.validateKPIs(defs.Name, defs))

        validation.extend(
            cls.validateParameters(defs))

        return validation

    @classmethod
    def Clear(cls):
        cls.scenarios = {}

    @classmethod
    def GetCurrentScenarios(cls):
        return cls.scenarios
