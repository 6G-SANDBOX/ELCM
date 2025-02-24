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


## Run.KafkaConsumerToInflux

**Description**:

This task consumes messages from a Kafka topic and sends them to InfluxDB.

**How It Works**:
1. **Initialization**: Configures Kafka consumer settings based on the provided parameters and sets up the connection to InfluxDB.
2. **Message Handling**: Continuously listens to messages from a Kafka topic, processes them, and sends the data to InfluxDB.
3. **Stopping Condition**: The task stops consuming messages when a specific stop signal is detected.

**Configuration Parameters**:
- `ExecutionId` (required): Unique identifier for the execution.
- `Ip` (required): IP address of the Kafka broker.
- `Port` (required): Port number for Kafka broker connection.
- `Topic` (required): Kafka topic to consume messages from.
- `Measurement` (required): InfluxDB measurement name where data will be sent.
- `Stop` (required): Signal to stop message consumption.
- `Account` (required): Flag indicating when user and password is used (`True` or `False`).
- `GroupId` (optional): Kafka consumer group ID, used to manage offsets and group consumption.
- `Certificates` (optional): Path to SSL/TLS certificate files, needed if encryption is used.
- `Encryption` (required): Flag indicating whether SSL/TLS encryption is used (`True` or `False`).
- `Timestamp` (optional): The name of the timestamp field for the metrics.
- `CSV` (optional): Flag indicating whether CSV output is enabled (`True` or `False`).

**Encryption**:

This task supports encryption to secure the connection:

- **TLS/SSL**: If enabled, the connection to Kafka is secured using TLS/SSL. The configuration includes:
  - **Certificate File** (`client-cert-signed.pem`): Authenticates the client to the Kafka broker.
  - **Private Key File** (`client-key.pem`): Establishes the client’s identity.
  - **CA File** (`ca-cert.pem`): Verifies the Kafka broker’s certificate.

**YAML Configuration Example**:

```yaml
Version: 2
Name: KAFKA
Sequence:
  - Order: 1
    Task: Run.KafkaConsumerToInflux
    Config:
      ExecutionId: "@{ExecutionId}"
      Ip: "X.X.X.X"
      Port: "XXXX"
      Topic: "my_topic"
      Measurement: "my_measurement"
      Stop: "stop_flag"
      Account: True       
      GroupId: "my_group"     # Optional
      Certificates: "/path/to/certificates/"  # Optional, if encryption is used
      Encryption: True        # Set to True if TLS/SSL is used, False otherwise
      CSV: False              # Optional, default is False
```

**Important Note**: 
A stop task (e.g., `AddMilestone`) must be used to ensure the `Run.KafkaConsumerToInflux` task terminates properly and stops retrieving data from Kafka.

For server configuration details, refer to: [Misc configurations](/docs/A3_MISC_CONFIGURATIONS.md).
## Run.MqttToInflux

**Description**:

This task subscribes to an MQTT topic, processes received messages, and sends them to InfluxDB.

**How It Works**:
1. **Initialization**: Configures the MQTT client settings based on the provided parameters and sets up the connection to InfluxDB.
2. **Message Handling**: Subscribes to the MQTT topic, processes incoming messages, and sends the data to InfluxDB.
3. **Stopping Condition**: The task stops processing messages when a specific stop signal is detected.

**Configuration Parameters**:
- `ExecutionId` (required): Unique identifier for the execution.
- `Broker` (required): Address of the MQTT broker.
- `Port` (required): Port number for MQTT broker connection.
- `Account` (required): Flag indicating when user and password is used (`True` or `False`).
- `Topic` (required): MQTT topic to subscribe to.
- `Stop` (required): Signal to stop message processing.
- `Measurement` (required): InfluxDB measurement name where data will be sent.
- `Certificates` (optional): Path to SSL/TLS certificate files, needed if encryption is used.
- `Encryption` (required): Flag indicating whether SSL/TLS encryption is used (`True` or `False`).

**Encryption**:

This task uses encryption to secure the MQTT connection:

- **TLS/SSL**: If enabled, the connection to the MQTT broker is secured using TLS/SSL. The configuration includes:
  - **Certificate File** (`client-cert.pem`): Authenticates the client to the MQTT broker.
  - **Private Key File** (`client-key.pem`): Establishes the client’s identity.
  - **CA File** (`ca.pem`): Verifies the MQTT broker’s certificate.

**YAML Configuration Example**:

```yaml
Version: 2
Name: MQTT
Sequence:
  - Order: 1
    Task: Run.MqttToInflux
    Config:
      ExecutionId: "@{ExecutionId}"
      Broker: "mqtt_broker_address"
      Port: "8885"
      Account: True
      Topic: "my_topic"
      Stop: "stop_flag"
      Measurement: "my_measurement"
      Certificates: "/path/to/certificates/"  # Optional, if encryption is used
      Encryption: True        # Set to True if TLS/SSL is used, False otherwise
```
Note: It is necessary to use a stop task (AddMilestone) to halt the execution of the Run.MqttToInflux task. This ensures that the task terminates properly and stops retrieving data from MQTT.

For server configuration, consult: [Misc configurations](/docs/A3_MISC_CONFIGURATIONS.md)

## Run.PrometheusToInflux

**Description**:

This task retrieves data from Prometheus using specified queries and sends the processed data to InfluxDB.

**How It Works**:
1. **Initialization**: Configures the Prometheus session based on the provided parameters and sets up the connection to InfluxDB.
2. **Data Retrieval**: Executes range and custom queries to retrieve data from Prometheus.
3. **Data Processing**: Processes and stores the retrieved data.
4. **Data Transfer**: Sends the processed data to InfluxDB.
5. **Stopping Condition**: The task stops processing when a specific stop signal is detected.

**Configuration Parameters**:
- `ExecutionId` (required): Unique identifier for the execution.
- `Url` (required): URL of the Prometheus server.
- `Port` (required): Port number for Prometheus server connection.
- `QueriesRange` (optional): List of range queries to execute.
- `QueriesCustom` (optional): List of custom (instant) queries to execute.
- `Measurement` (required): InfluxDB measurement name where data will be sent.
- `Stop` (required): Signal to stop data retrieval.
- `Step` (required): Step interval for range queries.
- `Account` (required): Flag indicating when user and password is used (`True` or `False`).
- `Certificates` (optional): Path to SSL/TLS certificate files, needed if encryption is used.
- `Encryption` (required): Flag indicating whether SSL/TLS encryption is used (`True` or `False`).

**Encryption**:

This task uses encryption to secure the connection:

- **TLS/SSL**: If enabled, the connection to Prometheus is secured using TLS/SSL. The configuration includes:
  - **Certificate File** (`client-cert.pem`): Authenticates the client to Prometheus.
  - **Private Key File** (`client-key.pem`): Establishes the client’s identity.
  - **CA File** (`ca.pem`): Verifies the Prometheus server’s certificate.

**YAML Configuration Example**:

```yaml
Version: 2
Name: PROMETHEUS
Sequence:
  - Order: 1
    Task: Run.PrometheusToInflux
    Config:
      ExecutionId: "@{ExecutionId}"
      Url: "prometheus.example.com"
      Port: "9090"
      QueriesRange:
        - "query_range_1"
        - "query_range_2"
      QuieriesCustom:
        - "custom_query_1"
        - "custom_query_2"
      Measurement: "my_measurement"
      Stop: "stop_flag"
      Step: "1s"
      Account: True
      Certificates: "/path/to/certificates/"  # Optional, if encryption is used
      Encryption: True        # Set to True if TLS/SSL is used, False otherwise
```
Note: It is necessary to use a stop task (AddMilestone) to halt the execution of the Run.PrometheusToInflux task. This ensures that the task terminates properly and stops retrieving data from Prometheus.

For server configuration, consult: [Misc configurations](/docs/A3_MISC_CONFIGURATIONS.md)

## Run.TelegrafToInflux

**Description**:

This task listens for incoming TCP connections from Telegraf, processes the received data, and sends it to InfluxDB.

**How It Works**:
1. **Initialization**: Configures the TCP server and sets up SSL/TLS if required.
2. **Data Handling**: Receives and decodes data from Telegraf, processes it, and sends it to InfluxDB.
3. **Stopping Condition**: The task stops based on a specified stop signal.

**Configuration Parameters**:
- `Measurement` (required): The name of the InfluxDB measurement where the data will be stored.
- `Stop` (required): Signal to stop the task.
- `Encryption` (required): Flag indicating whether SSL/TLS encryption is used (`True` or `False`).
- `Certificates` (optional): Path to SSL certificate files, needed if encryption is enabled.

**Encryption**:

If SSL/TLS encryption is enabled:
- **TLS/SSL**: The connection uses SSL/TLS. The SSL/TLS configuration includes:
  - **Certificate File** (`server-cert.pem`): Authenticates the server to clients.
  - **Private Key File** (`server-key.pem`): Establishes the server’s identity.
  - **CA File** (`ca.pem`): Verifies the client’s certificate.

**YAML Configuration Example**:

```yaml
Version: 2
Name: TELEGRAF
Sequence:
  - Order: 1
    Task: Run.TelegrafToInflux
    Config:
      Measurement: "my_measurement"
      Stop: "stop_flag"
      Encryption: True       # Set to True if TLS/SSL is used, False otherwise
      Certificates: "/path/to/certificates/"  # Optional, if encryption is used
      Port: "8094"           # Optional
```
Note: It is necessary to use a stop task (AddMilestone) to halt the execution of the Run.TelegrafToInflux task. This ensures that the task terminates properly and stops retrieving data from Telegraf.
For server configuration, consult: [Misc configurations](/docs/A3_MISC_CONFIGURATIONS.md)

## Run.EmailNotification

**Description**:

This task sends an email notification about the completion of an experiment or task.

**How It Works**:
1. **Initialization**: Configures the email settings based on the provided parameters.
2. **Email Composition**: Creates an email message with a subject and body indicating the completion of the task.
3. **Email Sending**: Connects to the SMTP server and sends the email.

**Configuration Parameters**:
- `ExecutionId` (required): Unique identifier for the execution.
- `Email` (required): Recipient email address.

**SMTP Configuration**:

The task uses SMTP for sending the email:

- **Server Address**: The address of the SMTP server to connect to.
- **Port**: The port number for the SMTP server (usually 587 for TLS).
- **Authentication**: Uses username and password for SMTP authentication.

**YAML Configuration Example**:

```yaml
Version: 2
Name: EMAIL
Sequence:
  - Order: 1
    Task: Run.EmailNotification
    Config:
      ExecutionId: "@{ExecutionId}"
      Email: "recipient@example.com"
```

## Run.HelmDeploy
Deploy the Helm Chart indicated by parameters in the cluster selected by the kubeconfig file where the ELCM resides. Configuration values:
- `Action`: Action to be performed by the ELCM, one between "Deploy", "Delete" and "Rollback"
- `Namespace`: Name of the namespace where it will be deployed, if omitted, default is applied
- `ReleaseName`: Chart release name
- `HelmChartPath`: Path of the HelmChart to be deployed

## Run.CliSsh

**Description**:

The `CliSsh` task establishes an SSH connection to a remote server, executes a specified command, and logs the output or any errors encountered during execution. It supports multiple types of private key authentication, including RSA, ECDSA, and Ed25519.

**How It Works**:
1. **Initialization**: 
   - Defines a set of required and optional parameters needed to configure the SSH connection, such as hostname, port, username, private key path, and the command to execute.
   
2. **SSH Connection**: 
   - The client connects to the specified SSH server using the provided hostname and port, and it accepts various private key types (RSA, ECDSA, Ed25519) for authentication.
   
3. **Command Execution**:
   - Once connected, the provided command is executed on the remote server.
   - Captures the standard output and error output streams from the executed command.

**Configuration Parameters**:
- `Hostname` (required): The hostname or IP address of the SSH server.
- `Port` (optional): The SSH port (default is 22).
- `Username` (required): The username for the SSH connection.
- `Certificate` (required): Path to the private key file used for authentication (supports RSA, ECDSA, and Ed25519).
- `Command` (required): The command to execute on the remote server.

**YAML Configuration Example**
```yaml
Version: 2
Name: CLI_SSH
Sequence:
  - Order: 1
    Task: Run.CliSsh
    Config:
      Hostname: "192.168.1.100"               # IP address or hostname of the SSH server
      Port: 22                                # SSH port (default is 22)
      Username: "user"                        # Username for the SSH connection
      Certificate: "/path/to/private_key"     # Path to the private key for authentication
      Command: "ifconfig"                     # Command to execute on the remote server
```
## Run.AthonetToInflux

**Description**:

The `AthonetToInflux` task fetches monitoring data from an Athonet system using Prometheus queries and sends the processed data to an InfluxDB instance. It handles token-based authentication, range-based and custom Prometheus queries, and efficient data mapping for InfluxDB insertion.

**How It Works**:
1. **Initialization**:
   - The task is configured with required parameters for authentication, Prometheus query execution, and InfluxDB data insertion.
   - Parameters include Athonet URLs, authentication credentials, query details, and execution configurations.

2. **Authentication**:
   - Authenticates to the Athonet system using the provided username and password, retrieving an access token required for subsequent Prometheus queries.

3. **Prometheus Query Execution**:
   - Supports both range-based and custom Prometheus queries to fetch monitoring data.
   - Handles token expiration by automatically re-authenticating when necessary.

4. **Data Processing**:
   - Processes the retrieved Prometheus data, sanitizes metric names, and organizes the data into a dictionary for InfluxDB insertion.

5. **Data Insertion into InfluxDB**:
   - Sends the processed data to an InfluxDB instance with proper timestamp mapping, measurement configuration, and execution context.

**Configuration Parameters**:
- `ExecutionId` (required): Unique identifier for the execution instance.
- `QueriesRange` (optional): List of Prometheus range queries to execute.
- `QueriesCustom` (optional): List of custom Prometheus queries to execute.
- `Measurement` (required): The InfluxDB measurement name where data will be stored.
- `Stop` (required): A stop condition identifier, ensuring the task terminates upon specific criteria.
- `Step` (required): Time step for Prometheus range queries.
- `Username` (required): Athonet authentication username.
- `Password` (required): Athonet authentication password.
- `AthonetLoginUrl` (required): URL for Athonet authentication.
- `AthonetQueryUrl` (required): URL for Prometheus queries on the Athonet system.

**YAML Configuration Example**:
```yaml
Version: 2
Name: ATHONET_TO_INFLUX
Sequence:
  - Order: 1
    Task: Run.AthonetToInflux
    Config:
      ExecutionId: "@{ExecutionId}"                    # Unique execution identifier
      QueriesRange: 
        - "query1"           # Prometheus range query
        - "query2"           # Another Prometheus range query
      QueriesCustom:
        - "query3"           # Custom Prometheus query
      Measurement: "athonet_metrics"         # InfluxDB measurement name
      Stop: "stop_athonet"           # Stop condition identifier
      Step: "1s"                            # Time step for range queries
      Username: "admin"                      # Athonet username
      Password: "password"                   # Athonet password
      AthonetLoginUrl: "https://athonet.example.com/core/login" # Athonet login URL
      AthonetQueryUrl: "https://athonet.example.com/core/prometheus"   # Athonet Prometheus query URL
```
Note: It is necessary to use a stop task (AddMilestone) to halt the execution of the Run.AthonetToInflux. This ensures that the task terminates properly and stops retrieving data from Prometheus.