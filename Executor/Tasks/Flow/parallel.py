from Task import Task
from Helper import Level
from threading import Thread
from Composer import TaskDefinition
from Experiment import Expander
from Executor import Verdict


class ChildInfo:
    def __init__(self, definition: TaskDefinition):
        self.Thread = None
        self.TaskDefinition = definition
        self.TaskInstance = None


class Parallel(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Parallel", parent, params, logMethod, None)

    def Run(self):
        if len(self.Children) == 0:
            self.Log(Level.WARNING, f"Skipping parallel execution: no children defined.")
            return

        self.Log(Level.INFO, f"Starting parallel execution ({len(self.Children)} children)")

        children: [ChildInfo] = []

        for index, child in enumerate(self.Children, start=1):
            if child.Label is None:
                child.Label = f"Br{index}"

            flowState = {'Branch': index}
            info = ChildInfo(child)
            info.TaskInstance = child.GetTaskInstance(
                self.Log, self.parent, Expander.ExpandDict(child.Params, self.parent, flowState))
            info.Thread = Thread(target=self.runChild, args=(info.TaskInstance,))
            children.append(info)

            if not self.parent.stopRequested:
                info.Thread.start()
                self.Log(Level.DEBUG, f"Started branch {index}: {child.Label}")

        for index, info in enumerate(children, start=1):
            if info.Thread.is_alive():
                info.Thread.join()
                self.parent.params.update(info.TaskInstance.Vault)  # Propagate any published values
                self.Log(Level.DEBUG, f"Branch {index} ({info.TaskDefinition.Label}) joined")
                self.Verdict = Verdict.Max(self.Verdict, info.TaskInstance.Verdict)

        self.Log(Level.INFO, f"Finished execution of all child tasks")

    def runChild(self, taskInstance: Task):
        try:
            taskInstance.Start()
        except Exception as e:
            taskInstance.Verdict = Verdict.Error
            self.Log(Level.ERROR, str(e))
