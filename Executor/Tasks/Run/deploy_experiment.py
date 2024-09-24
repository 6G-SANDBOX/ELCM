from Task import Task
from Helper import Cli
from Helper import Level
from enum import Enum


class HelmAction(Enum):
    DEPLOY = "deploy"
    DELETE = "delete"
    ROLLBACK = "rollback"


class DeployExperiment(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Deploy Experiment", parent, params, logMethod)

        self.paramRules = {
            'HelmChartPath': (None, False),
            'ReleaseName': (None, True),
            'Action': (None, True),
            'Namespace': ('Default', False)
        }

        self.helm_chat_path = self.params['HelmChartPath']
        self.release_name = self.params['ReleaseName']
        self.action = self.params['Action'].lower()
        self.namespace = self.params['Namespace']
        command = ""
        action = None

        # Check for valid action
        try:
            action = HelmAction(self.action)
        except ValueError:
            self.Log(Level.ERROR, f"Invalid Helm Action {self.action}")
            self.SetVerdictOnError()

        if action == HelmAction.DEPLOY:
            command = f'helm upgrade --install {self.release_name} {self.helm_chat_path} --namespace {self.namespace} --wait --timeout 3m'
        elif action == HelmAction.DELETE:
            command = f'helm uninstall {self.release_name} --namespace {self.namespace}'
        elif action == HelmAction.ROLLBACK:
            command = f'helm rollback {self.release_name} --namespace {self.namespace} --wait --timeout 3m'

        self.cli = Cli(command, self.params['CWD'], self.Log)

    # Check for correct params format
    def inDepthSanitizeParams(self):
        if self.action == HelmAction.DEPLOY.value and self.params['HelmChartPath'] == self.paramRules['HelmChartPath'][0]:
            self.Log(Level.ERROR, f"Parameter HelmChartPath is mandatory if the Action parameter is Deploy "
                                  f"but was not configured for the task.")
            self.SetVerdictOnError()
            return False
        else:
            return True

    def Run(self):
        self.cli.Execute()
