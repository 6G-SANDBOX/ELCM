from Facility import Facility, ActionInformation, DashboardPanel
from Data import ExperimentDescriptor, ExperimentType, NsInfo, Metal
from .platform_configuration import PlatformConfiguration, TaskDefinition
from importlib import import_module
from Helper import Log
from typing import List, Dict, Optional, Tuple
from Executor.Tasks.Run import Message
from Interfaces import Management


class Composer:
    facility: Facility = None

    @staticmethod
    def getMessageAction(severity: str, message: str) -> ActionInformation:
        action = ActionInformation()
        action.TaskName = "Run.Message"
        action.Order = -9999
        action.Config = {'Severity': severity, 'Message': message}
        return action

    @staticmethod
    def getMessageTask(severity: str, message: str) -> TaskDefinition:
        task = TaskDefinition()
        task.Task = Message
        task.Params = {'Severity': severity, 'Message': message}
        return task

    @classmethod
    def Compose(cls, descriptor: ExperimentDescriptor) -> PlatformConfiguration:
        if cls.facility is None:
            cls.facility = Facility()

        configuration = PlatformConfiguration()
        configuration.RunParams['Report'] = {'ExperimentName': descriptor.Identifier}

        actions: List[ActionInformation] = []
        panels: List[DashboardPanel] = []
        errored = False

        if descriptor.Slice is not None:
            if len(descriptor.NetworkServices) != 0:
                sliceManager = Management.SliceManager()
                nameToLocation = sliceManager.GetVimNameToLocationMapping()
                for ns in descriptor.NetworkServices:
                    nsId, vimName = ns
                    try:
                        nsdName, nsdId, nsdRequirements = sliceManager.GetNsdData(nsId)
                        location = nameToLocation.get(vimName, None)
                        if nsdRequirements is None:
                            raise RuntimeError(f"Could not retrieve NSD information for '{nsId}'")
                        elif location is None:
                            raise RuntimeError(f"Could not retrieve location for VIM '{vimName}'")
                        nsInfo = NsInfo(nsdName, nsdId, location)
                        nsInfo.Requirements = nsdRequirements
                        configuration.NetworkServices.append(nsInfo)
                    except Exception as e:
                        errored = True
                        actions.append(cls.getMessageAction(
                            "ERROR", f"Exception while obtaining information about network service {nsId}: {e}"))

            if not errored:
                nest, error = cls.composeNest(descriptor.Slice, descriptor.Scenario, configuration.NetworkServices)
                if error is None:
                    configuration.Nest = nest
                else:
                    errored = True
                    actions.append(cls.getMessageAction(
                        "ERROR", f'Error while generating NEST data for experiment: {error}'))

        if not errored:
            if descriptor.Type == ExperimentType.MONROE:
                actions.extend(cls.facility.GetMonroeActions())
            else:
                for scenario in descriptor.Scenario:
                    scenarioActions = cls.facility.GetScenarioActions(scenario)
                    for i, scenarioAction in enumerate(scenarioActions):
                        scenarioAction.Label = f"Sce_{i + 1}"
                        scenarioActions[i] = scenarioAction
                    if len(scenarioActions) != 0:
                        actions.extend(scenarioActions)
                    else:
                        actions.append(cls.getMessageAction(  # Notify, but do not cancel execution
                            "WARNING", f'Scenario "{scenario}" did not generate any actions'))

                if descriptor.Automated:
                    for ue in descriptor.UEs:
                        actions.extend(cls.facility.GetUEActions(ue))
                    for testcase in descriptor.TestCases:
                        testcaseActions = cls.facility.GetTestCaseActions(testcase)
                        if len(testcaseActions) != 0:
                            actions.extend(testcaseActions)
                        else:
                            actions.append(cls.getMessageAction(  # Notify, but do not cancel execution
                                "WARNING", f'TestCase "{testcase}" did not generate any actions'))
                        panels.extend(cls.facility.GetTestCaseDashboards(testcase))
                else:
                    delay = ActionInformation()
                    delay.TaskName = "Run.Delay"
                    delay.Config = {'Time': descriptor.Duration * 60}
                    actions.append(delay)

        actions.sort(key=lambda action: action.Order)  # Sort by Order (only those at first level)
        requirements = set()

        for action in actions:
            requirements.update(action.Requirements)
            taskDefinition = cls.getTaskDefinition(action)
            configuration.RunTasks.append(taskDefinition)

        configuration.Requirements = list(requirements)
        configuration.DashboardPanels = panels

        return configuration

    @staticmethod
    def getTaskClass(taskName: str):
        try:
            packageName, className = taskName.split('.')
            package = import_module(f'Executor.Tasks.{packageName}')
            return getattr(package, className)
        except (ModuleNotFoundError, AttributeError, ValueError):
            Log.E(f'Task "{taskName}" not found')
            return None

    @classmethod
    def getTaskDefinition(cls, action: ActionInformation):
        task = cls.getTaskClass(action.TaskName)
        if task is None:
            taskDefinition = cls.getMessageTask("ERROR", f"Could not find task {action.TaskName}")
        else:
            taskDefinition = TaskDefinition()
            taskDefinition.Params = action.Config
            taskDefinition.Task = task
            taskDefinition.Label = action.Label
            taskDefinition.Children = []
            for child in action.Children:
                childDefinition = cls.getTaskDefinition(child)  # Either will be a _real_ task or a message
                taskDefinition.Children.append(childDefinition)
        return taskDefinition

    @classmethod
    def composeNest(cls, baseSlice: str, scenario: str, nss: List[NsInfo]) -> Tuple[Dict, Optional[str]]:
        """Returns the NEST as Dict (possibly empty) and a string indicating the error (None in case of success)"""
        try:
            if baseSlice is None:
                raise RuntimeError("Cannot create NEST without a base slice value")

            sliceDescriptor = {"base_slice_des_ref": baseSlice}

            if scenario is not None:
                scenarioData = Facility.Scenarios().get(scenario, None)
                if scenarioData is None:
                    raise RuntimeError(f"Unrecognized scenario '{scenario}'")
                sliceDescriptor.update(scenarioData)
            # We allow having no scenario, but not having an unrecognized one

            nsList = []
            for ns in nss:
                nsList.append({
                    "nsd-id": ns.Id,
                    "ns-name": ns.Name,
                    "placement": ns.Location,
                    "optional": False  # All network services should be deployed for the test
                })

            nest = {"base_slice_descriptor": sliceDescriptor}
            if len(nsList) != 0:
                nest["service_descriptor"] = {"ns_list": nsList}

            return nest, None
        except Exception as e:
            return {}, str(e)
