from collections import deque
from Experiment import ExperimentRun, ExperimentStatus
from typing import Deque, Optional, List, Dict
from Helper import Log
from .status import Status
from Scheduler.facility.routes import load_raw
from Facility import Facility
import os

class ExecutionQueue:
    queue: Deque[ExperimentRun] = deque()

    @classmethod
    def Find(cls, executionId) -> Optional[ExperimentRun]:
        needles = [e for e in cls.queue if e.Id == executionId]
        return needles[0] if needles else None

    @classmethod
    def Create(cls, params: Dict) -> ExperimentRun:
        executionId = Status.NextId()

        descriptor = params.get("Descriptor")
        testcase_names = []
        ue_names = []

        if descriptor and hasattr(descriptor, "_data"):
            testcase_names = descriptor._data.get("TestCases", [])
            ue_names = descriptor._data.get("UEs", [])

        folder = os.path.abspath("Persistence/Executions_yml")
        os.makedirs(folder, exist_ok=True)

        for name in testcase_names:
            raw = load_raw(Facility.TESTCASE_FOLDER, Facility.testCases, {name})
            if name in raw:
                raw_content = raw[name][0]
                dest_path = os.path.join(folder, f"{executionId}_testcase_{name}.yml")
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(raw_content)
                Log.I(f"Copied TestCase '{name}' YAML to {dest_path}")

        for name in ue_names:
            raw = load_raw(Facility.UE_FOLDER, Facility.ues, {name})
            if name in raw:
                raw_content = raw[name][0]
                dest_path = os.path.join(folder, f"{executionId}_ue_{name}.yml")
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(raw_content)
                Log.I(f"Copied UE '{name}' YAML to {dest_path}")

        execution = ExperimentRun(executionId, params)
        cls.queue.appendleft(execution)
        Log.I(f'Created Execution {execution.Id}')
        return execution

    @classmethod
    def Delete(cls, executionId):
        execution = cls.Find(executionId)
        if execution is not None:
            execution.Save()
            cls.queue.remove(execution)

    @classmethod
    def Cancel(cls, executionId: int):
        execution = cls.Find(executionId)
        if execution is not None:
            Log.I(f'Cancelling execution {execution.Id}')
            execution.Cancel()
        else:
            Log.W(f'Cannot cancel execution {executionId}: Not found')

    @classmethod
    def Retrieve(cls, status: Optional[ExperimentStatus] = None) -> List[ExperimentRun]:
        if status is None:
            return list(cls.queue)
        else:
            return [e for e in cls.queue if e.CoarseStatus == status]

    @classmethod
    def UpdateAll(cls):
        executions = cls.Retrieve()
        if len(executions) != 0:
            Log.D(f"UpdateAll: {(', '.join(str(e) for e in executions))}")
        for execution in reversed(executions):  # Reversed to give priority to older executions (for resources)
            Log.D(f"Update Execution: {execution.Id}")
            try:
                if execution.Active:
                    pre = execution.CoarseStatus
                    Log.I(f'Advancing Execution {execution.Id}')
                    execution.Advance()
                    Log.D(f'{execution.Id}: {pre.name} -> {execution.CoarseStatus.name}')
                else:
                    Log.I(f'Removing Execution {execution.Id} from queue (status: {execution.CoarseStatus.name})')
                    cls.Delete(execution.Id)
            except Exception as e:
                Log.C(f"Exception while updating execution {execution.Id}: {e}")
