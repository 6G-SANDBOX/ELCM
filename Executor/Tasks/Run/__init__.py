from .dummy import Dummy
from .message import Message
from .tap_execute import TapExecute
from .cli_execute import CliExecute
from .slice_creation_time import SliceCreationTime
from .single_slice_creation_time import SingleSliceCreationTime
from .publish import Publish
from .compress_files import CompressFiles
from .delay import Delay
from .csvToInflux import CsvToInflux
from .add_milestone import AddMilestone
from .publish_from_source import PublishFromPreviousTaskLog, PublishFromFile
from .rest_api import RestApi
from .upgrade_verdict import UpgradeVerdict
from .evaluate import Evaluate
from .robot_framework import RobotFramework
from .helm_deploy import HelmDeploy
