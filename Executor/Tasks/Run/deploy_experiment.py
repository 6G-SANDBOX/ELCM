import re
from Task import Task
from Helper import Cli
from Settings import Config
from os import environ


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
        self.action = self.params['Action']
        self.namespace = self.params['Namespace']

        if self.action == "Deploy":
            command = f'helm upgrade --install {self.release_name} {self.helm_chat_path} --namespace {self.namespace} --wait --timeout 3m'
        elif self.action == "Delete":
            command = f'helm uninstall {self.release_name} --namespace {self.namespace}'
        elif self.action == "Rollback":
            command = f'helm rollback {self.release_name} --namespace {self.namespace} --wait --timeout 3m'
        else:
            raise Exception("Invalid action")

        self.cli = Cli(command, self.params['CWD'], self.Log)

    def Run(self):
        self.cli.Execute()
