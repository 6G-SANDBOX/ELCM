from Task import Task
from Helper import Cli
from Helper import Level
from enum import Enum


class HelmAction(Enum):
    DEPLOY = "deploy"
    DELETE = "delete"
    ROLLBACK = "rollback"


class HelmDeploy(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Helm Deploy", parent, params, logMethod)

        self.paramRules = {
            'HelmChartPath': (None, False),
            'ReleaseName': (None, True),
            'Action': (None, True),
            'Namespace': ('Default', False)
        }

    def inDepthSanitizeParams(self):

        if self.params['Action'].lower() == HelmAction.DEPLOY.value and self.params['HelmChartPath'] == \
                self.paramRules['HelmChartPath'][0]:
            self.Log(Level.ERROR, f"Parameter HelmChartPath is mandatory if the Action parameter is Deploy "
                                  f"but was not configured for the task.")
            self.SetVerdictOnError()
            return False
        else:
            return True

    def Run(self):
        helm_chat_path = self.params['HelmChartPath']
        release_name = self.params['ReleaseName']
        namespace = self.params['Namespace']
        command = ""
        action = None

        # Check for valid action
        try:
            action = HelmAction(self.params['Action'].lower())
        except ValueError:
            self.Log(Level.ERROR, f"Invalid Helm Action {action}")
            self.SetVerdictOnError()

        if action == HelmAction.DEPLOY:
            command = f'helm upgrade --install {release_name} {helm_chat_path} --namespace {namespace} --wait --timeout 3m'
        elif action == HelmAction.DELETE:
            command = f'helm uninstall {release_name} --namespace {namespace}'
        elif action == HelmAction.ROLLBACK:
            command = f'helm rollback {release_name} --namespace {namespace} --wait --timeout 3m'

        cli = Cli(command, self.params['CWD'], self.Log)
        cli.Execute()
