# General Tasks:

The following is a list of the tasks that can be defined as part of a TestCase or UE list of actions, as well as
their configuration values.

### Common values:
All tasks recognize the following configuration value:
- `VerdictOnError`: Name of the verdict to reach when the task encounters an error during execution (what is considered
an error varies from task to task). By default, the value in `config.yml` is used. See 'Task and execution verdicts'
([Variable Expansion and Execution Verdict](/docs/3-3_VARIABLE_EXPANSION_VERDICT.md)).

## Run.CliExecute
Executes a script or command through the command line. Configuration values:
- `Parameters`: Parameters to pass to the command line (i.e. the line to write on the CLI)
- `CWD`: Working directory where the command will run

## Run.CompressFiles
Generates a Zip file that contains all the specified files. Configuration values:
- `Files`: List of (single) files to add to the Zip file
- `Folders`: List of folders to search files from. All the files contained within
these folders and their sub-folders will be added to the Zip file
- `Output`: Name of the Zip file to generate.

## Run.CsvToInflux
Uploads the contents of a CSV file to InfluxDb. The file must contain a header row that specifies the names of each
column, and must contain a column that specifies the timestamp value of the row as a POSIX timestamp (seconds from the
epoch as float, and UTC timezone). Configuration values:
- `ExecutionId`: Id of the execution (can be dinamically expanded from `@{ExecutionId}`)
- `CSV`: Path of the CSV file to upload
- `Measurement`: Measurement (table) where the results will be saved
- `Delimiter`: CSV separator, defaults to `','`.
- `Timestamp`: Name of the column that contains the row timestamp, defaults to `"Timestamp"`.
- `Convert`: If True, try to convert the values to a suitable format (int, float, bool, str). Only 'True' and 'False'
with any capitalization are converted to bool. If False, send all values as string. Defaults to True.

## Run.Delay
Adds a configurable time wait to an experiment execution. Has a single configuration value:
- `Time`: Time to wait in seconds.

## Run.Dummy
Dummy action, will only display the values on the `Config` dictionary on the log

## Run.Evaluate

Evaluates `Expression`, and publishes the generated result as the `Key` variable. Configuration values:
- `Key`: Name of the key used to save the generated value (as string).
- `Expression`: Python expression that will be evaluated (as string). Variable expansion can be used for specifying
runtime values.

> ⚠ This task makes use of the [eval](https://docs.python.org/3/library/functions.html#eval) built-in function:
> - The `Expression` can execute arbitrary code.
> - Since the test cases are defined by the platform operators it is expected that no dangerous code will be executed,
> however, **exercise extreme caution, specially if variable expansion is used** as part of the expression.

The following is an example of the use of this task:

```yaml
   - Order: 1
     Task: Run.Publish
     Config: { VAR: 4 }
   - Order: 2
     Task: Run.Evaluate
     Config:
       Key: VAR
       Expression: <See below>
```

After the execution of both tasks, the value of `VAR` will be, depending on the expression:
- For `1+@[VAR]`: "5"
- For `1+@[VAR].0`: "5.0"
- For `1+@[VAR].0>3`: "True"
- For `self`: "<Executor.Tasks.Run.evaluate.Evaluate object at 0x...>"

## Run.Message
Displays a message on the log, with the configured severity. Configuration values:
- `Severity`: Severity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `Message`: Text of the message

## Run.Publish
Saves a value (identified with a name) for use in another task that runs later. The value can be retrieved using
the `@[key]` or `@[Publish.key]` variable expansion. If the key is not defined at the time of expansion it will
be replaced by the string `<<UNDEFINED>>` unless another default is defined using `@[key:default]`.
In the case of this Task the `Config` dictionary contains the keys and values that will be published. For example,
the following tasks:
```yaml
- Order: 5
  Task: Run.Publish
  Config: { Publish1: "Text", Publish2: 1 }
- Order: 10
  Task: Run.Message
  Config: { Severity: INFO, Message: "1: @[Publish1]; 2: @[Publish.Publish2]; 3: @[Publish3]; 4: @[Publish.Publish4:NoProblem]" }
```
Will produce this message in the log:

`- INFO - 1: Text; 2: 1; 3: <<UNDEFINED>>; 4: NoProblem`

> Note that keys that are common to all tasks (for example, `VerdictOnError`) will be ignored.

## Run.PublishFromFile / Run.PublishFromPreviousTaskLog
Reads the contents of a file / the log of the previous task and looks for lines that match the specified regular
expression pattern, publishing the groups found. If multiple matches are found only the last one is saved.
Configuration values:
- `Pattern`: Regular expression to try to match, following
[Python's syntax](https://docs.python.org/3/library/re.html#regular-expression-syntax).
> Extra escaping may be needed inside the regular expression, for example `\d` needs to be written as `\\d`, otherwise
> an exception will occur when parsing the YAML file ("unknown escape character 'd'").
- `Keys`: List of (index, key) pairs, where index refers to the regex group, and key is the identifier to use
when publishing. If not included, nothing will be published (an empty list will be used). This can be useful
if only setting a Verdict is needed.
> - Groups are defined within regular expressions using '(' ... ')'.
> - Group 0 always refers to the complete matched line, manually specified groups start at index 1.
> - While writing the `Keys` in the task configuration note that YAML does not have a syntax for tuples, use lists of two elements instead.
- `VerdictOnMatch`: Verdict to set if a line matches the regular expression. Defaults to `NotSet`.
- `VerdictOnNoMatch`: Verdict to set if no line matches the regular expression. Defaults to `NotSet`.
- `Path` (only for Run.PublishFromFile): Path of the file to read

## Run.RestApi

Provides direct access to the internal RestClient functionality, avoiding the need of using external utilities such as
`curl` for simple requests. Configuration values:
- `Host`: Location where the REST API is listening
- `Port`: Port where the REST API is listening
- `Endpoint`: Specific API endpoint where the request will be sent
- `Https`: Whether to use HTTPS or not, defaults to False
- `Insecure`: Whether to ignore certificate errors when using HTTPS, defaults to False
- `Method`: REST method to use, currently suported methods are `GET`, `POST`, `PATCH`, `DELETE`
- `Payload`: Data to send in JSON format (as a single string), defaults to `'{}'`
- `PayloadMode`: Field where the payload will be sent, possible values are:
  - `Data`: The payload is saved in the `Body` field of the request. Also adds the `Content-Type=application/json` header
  - `Form`: The payload is saved on the `Form` field of the request
- `Responses`: Set of expected responses as a single value or a list. The special value `Success` indicates any possible
success response (2xx). Set to `None` to disable the check.
- `Timeout`: Maximum time in seconds to wait for a response
- `Headers`: Additional headers to add to the request

## Run.RobotFramework
Execute one or more test suites using an external Robot Framework instance. It is recommended to store and configure
Robot Framework in a dedicated virtualenv, where all the required dependencies (for example `robotframework-requests`)
are also installed. Configuration values:
- `Executable`: Absolute path to the Robot Framework executable. On a pre-configured virtualenv this file is usually
`<venv>/bin/robot` or `<venv>/Scripts/robot.exe`
- `Paths`: Either a single path (string) or a list of paths, each with the location of one of the test suites to run.
- `CWD`: Working directory, usually the root folder where the test suites are stored. If `GatherResults` is set to
`False` the generated report files will be left in this folder.
- `Variables`: Dictionary that contains the variables to be passed to Robot Framework. If present, the contents will be
used for generating a YAML file that is passed through the `--variablefile (-V)` parameter.
> The `PyYAML` module must be installed in the Robot Framework virtualenv in order to make use of this option, otherwise
> a runtime error will be reported and the file will not be read.
- `GatherResults`: Whether to store the generated files along with other files created by the experiment or not.
These reports will be compressed in a single zip file identified by the `Identifier` parameter. `True` by default.
- `Identifier`: Name used to identify a particular Robot Framework execution, in order to avoid overwriting results
for TestCases that include multiple invocations. If not set, it will be automatically generated from the time as
`RobotFwHHMMSS`, where HHMMSS corresponds to the hour, minutes and seconds in UTC.
- `VerdictOnPass`: Verdict to set if all tests are completed successfully. Defaults to `Pass`.
- `VerdictOnFail`: Verdict to set if any test in the suite fails. Defaults to `Fail`.

## Run.SingleSliceCreationTime
Sends the Slice Creation Time reported by the Slice Manager to InfluxDb. This task will not perform any deployment
 by itself, and will only read the values for a slice deployed during the experiment pre-run stage.
Configuration values:
- `ExecutionId`: Id of the execution (can be dinamically expanded from `@{ExecutionId}`)
- `WaitForRunning`: Boolean, wait until the Slice Manager reports that the slice is running, or retrieve results immediately
- `Timeout`: 'WaitForRunning' timeout in (aprox) seconds
- `SliceId`: Slice ID to check (can be dinamically expanded from `@{SliceId}`)

## Run.SliceCreationTime
Repeats a cycle of slice creation and deletion for a configured number of times, obtaining the Slice Creation Time on
each iteration and sending the values to the configured InfluxDb database. This task does not take into account the
slices deployed during the experiment's pre-run stage (if any). This task uses a local NEST file to describe the
slice to be deployed. Configuration values:
- `ExecutionId`: Id of the execution (can be dynamically expanded from `@{ExecutionId}`)
- `NEST`: Absolute path of the NEST file to use
- `Iterations`: Number of iterations. Defaults to 25
- `Timeout`: Timeout in (aprox) seconds to wait until the slice is running or deleted before skipping the iteration.
If not specified or set to None the task will continue indefinitely.
- `CSV`: If set, save the generated results to a CSV file in the specified path. In case of error while sending the
results to InfluxDb a CSV file will be forcibly created on `"@{TempFolder}/SliceCreationTime.csv"` (only if not set,
otherwise the file will be created as configured).

## Run.TapExecute
Executes a TAP TestPlan, with the possibility of configuring external parameters. Configuration values:
- `TestPlan`: Path (absolute) of the testplan file.
- `GatherResults`: Indicates whether to compress the generated CSV files to a Zip file (see below)
- `Externals`: Dictionary of external parameters

###### Gathering generated results
If selected, the task will attempt to retrieve all the results generated by the testplan, saving them to a Zip file
that will be included along with the logs once the execution finishes. The task will look for the files in the TAP
Results folder, inside a sub-folder that corresponds with the experiment's execution ID, for this reason, it is
necessary to add a MultiCSV result listener to TAP that has the following (recommended) `File Path` configuration:
```
Results\{Identifier}\{Date}-{ResultType}-{Identifier}.csv
```

## Run.UpgradeVerdict
Sets a particular verdict for this task, which in turn upgrades the verdict of the experiment execution, based
on the value of a published variable. Configuration values:
- `Key`: Name of the key to compare
- `Pattern`: Regular expression to try to match against the value of `Key`, following
[Python's syntax](https://docs.python.org/3/library/re.html#regular-expression-syntax)
- `VerdictOnMissing`: Verdict to set if `Key` is not found. Defaults to `NotSet`.
- `VerdictOnMatch`: Verdict to set if the value matches the regular expression. Defaults to `NotSet`.
- `VerdictOnNoMatch`: Verdict to set if the value does not match the regular expression. Defaults to `NotSet`.
