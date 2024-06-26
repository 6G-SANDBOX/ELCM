from typing import Dict, Union
from .experiment_run import ExperimentRun
from Executor import ExecutorBase
from re import finditer
from Settings import Config
from json import dumps


class Expander:
    @classmethod
    def ExpandDict(cls, dict: Dict, context: Union[ExecutorBase, ExperimentRun], flowState: Dict = None):
        config = Config()
        if flowState is None:
            flowState = {}
        return cls.expandParams(dict, context, config, flowState)

    @classmethod
    def expandParams(cls, item: object, context: Union[ExecutorBase, ExperimentRun],
                     config: Config, flowState: Dict) -> object:
        if isinstance(item, dict):
            res = {}
            for key, value in item.items():
                res[key] = cls.expandParams(value, context, config, flowState)
        elif isinstance(item, list) or isinstance(item, tuple):
            res = []
            for value in item:
                res.append(cls.expandParams(value, context, config, flowState))
        elif isinstance(item, str):
            res = cls.expand(item, context, config, flowState)
        else:
            res = item
        return res

    @classmethod
    def expand(cls, item: str, context: Union[ExecutorBase, ExperimentRun], config: Config, flowState: Dict) -> str:
        duration = context.Descriptor.Duration or 0
        replacements = {
            # Dynamic values
            "@{TempFolder}": context.TempFolder,
            "@{ExecutionId}": context.ExecutionId,
            "@{SliceId}": context.Params.get("DeployedSliceId", "None"),
            "@{DeployedSliceId}": context.Params.get("DeployedSliceId", "None"),
            "@{Application}": context.Descriptor.Application,
            "@{JSONParameters}": dumps(context.Descriptor.Parameters, indent=None),
            "@{ReservationTime}": duration,
            "@{ReservationTimeSeconds}": duration * 60,
            # Configuration values
            "@{TapFolder}": config.Tap.Folder,
            "@{TapResults}": config.Tap.Results,
        }

        for key, value in flowState.items():  # [Iter0|Iter1|Branch] on the current level, if applies
            replacements[f'@{{{key}}}'] = value

        expanded = item
        for key, value in replacements.items():
            expanded = expanded.replace(key, str(value))

        # Expand custom values published by Run.Publish and parameters
        for match in [m for m in finditer(r'@\[(.*?)]', item)]:
            all = match.group()
            capture = match.groups()[0]
            if ':' in capture:
                key, default = capture.split(':')
            else:
                key = capture
                default = '<<UNDEFINED>>'

            collection = None
            group = None
            if '.' in key:
                group, key = key.split('.')
                if group == "Params":
                    collection = context.Descriptor.Parameters
                elif group == "Publish":
                    collection = context.params
            else:
                collection = context.params

            value = collection.get(key, default) if collection is not None else f'<<UNKNOWN GROUP {group}>>'
            expanded = expanded.replace(all, str(value))

        return expanded
