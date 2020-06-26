# ELCM (Experiment Life-Cycle Manager)

## Requirements

 - [Python 3.7.x](https://www.python.org)
 - [Optional] [Grafana](https://grafana.com/) (tested on version 5.4)
 - [Optional] [Grafana reporter](https://github.com/IzakMarais/reporter) 
 (tested on version 2.1.0, commit 41b38a0)

## Interoperability with other components

The following information specifies the version that most closely match the expected behavior when this package interacts
with others developed internally in 5 Genesis (i.e. the version that was available during the development and that was 
used while testing this component). It's possible that most (or all) features work with some previous versions, and most
probably there will be no issues when using more recent versions.

 - [Portal](https://gitlab.fokus.fraunhofer.de/5genesis/portal) Version 1.0.8 (29/05/2019)

## Installing (development)
> A video detailing the deployment procedure of the ELCM (and Portal) can be seen [in BSCW](https://bscw.fokus.fraunhofer.de/bscw/bscw.cgi/d3208170/Coordinationlayer_call20190422.mp4)

> It is recommended, but not required, to run the Portal in a [Python virtual environment](https://virtualenv.pypa.io/en/stable/).
> If you are not using virtual environments, skip steps 3 and 4.

1. Clone the repository to a known folder, e.g. in `c:\ELCM` 
2. Enter the folder
```bash
cd c:/ELCM
```
3. Create a new Python virtualenv:
```bash
pip install virtualenv
virtualenv venv
```
4. Activate the virtual environment:
- For Windows:
```powershell
venv\Scripts\Activate.bat
```
- For Linux:
```bash
source venv/bin/activate
```
5. Install Python dependencies:
```bash
pip install -r requirements.txt
```

6. Start the development server:
```bash
flask run
```
The app will generate a default configuration file (`config.yml`) and start listening for requests on port 5001.
Refer to the Configuration section for information about customizing the default values.
Press `Control+C` to stop the development server.

## Deployment (production)

Since the ELCM should not be exposed to the Internet (the administration interface should only be accessed on the host 
machine or from inside a trusted network), and it will not receive a large number of concurrent requests it is possible 
to run the ELCM using the included development server. 

It is, however, also possible to run the ELCM using a production WSGI server such as [Waitress](https://github.com/Pylons/waitress) 
following these instructions:

1. Install Waitress on the ELCM Python environment:
```bash
pip install waitress
```
2. Start the server:
```bash
waitress-serve --listen=*:5001 app:app
```

## Configuration

The ELCM instance can be configured by setting environment variables and by editing the `config.yml` file. The ELCM uses
`python-dotenv`, so it's possible to save the environment variables in the `.flaskenv` file.

The environment variables that can be set are:
* FLASK_RUN_PORT: Port where the ELCM will listen (5000 by default)
* SECRET_KEY: A random string.
> Since the ELCM should not be exposed to the Internet it is not so important to set a random SECRET_KEY. However, the 
value is still **needed** and it's recommended to follow the same approach as with the 5Genesis Portal.

The values that can be configured on `config.yml` are:
* TempFolder: Root folder where the temporal files for the Executors can be created.
* Logging:
    * Folder: Root folder where the different log files will be saved.
    * AppLevel: Minimum log level that will be displayed in the console.
    * LogLevel: Minimum log level that will be recorded in the log files.
* Dispatcher:
    * Host: Location of the machine where the Dispatcher is running (localhost by default).
    * Port: Port where the Dispatcher is listening for connections (5000 by default).
> The Dispatcher does not currently exist as a separate entity, so this information refers to the Portal during Release A.
* Tap: 
    * Enabled: Whether or not to use TAP, if set to False the settings below will be ignored
    * OpenTap: True if using OpenTap (TAP 9), False if using TAP 8
    * Exe: TAP CLI executable
    * Folder: TAP installation folder
    * Results: TAP results folder
    * EnsureClosed: Performs an additional check on test plan completion, to ensure that all child processes are 
    correctly closed. Recommended to set to True, but increases execution time by roughtly 15 seconds.
> These values will be used by the `Run.TapExecute` task.
* Grafana:
    * Enabled
    * Host
    * Port
    * Bearer: Grafana API key without the 'Bearer ' prefix
    * ReportGenerator: URL where the `Grafana reporter` instance can be reached, if any
> These values will be used when generating a dashboard for the results generated by an experiment execution.
* SliceManager:
    * Host
    * Port
> These values will be used to communicate with the Katana Slice Manager when deploying/decommisioning slices and when 
> using the `Run.SingleSliceCreationTime` and `Run.SliceCreationTime` tasks. 
* InfluxDb:
    * Enabled: If set to False the settings below will be ignored
    * Host
    * Port
    * User: InfluxDb instance user
    * Password: InfluxDb user password
    * Database: InfluxDb instance database
> These values will be used for sending results to an InfluxDb instance. In particular, they will be used by the
> `Run.SingleSliceCreationTime` and `Run.SliceCreationTime` task. Additional tags will be generated by using the values
> in the `Metadata` section
* Metadata:
    * HostIp: IP address of the machine where the ELCM is running
    * Facility: Facility name (or platform)
> Additional ELCM instance metadata, currently used for values sent to InfluxDb

## Facility Configuration

> Starting with version 1.1, the facility is no longer configured by a single `facility.yml` file. UEs must now
> be defined using separate files in the `UEs` sub-folder, while TestCases (and their dashboards) are defined in
> the `TestCases` sub-folder. 
> 
> The available values for each element have not changed, so it's possible to move each key on the `facility.yml` file
> to their respective folders and have the same configuration as before the update.

The contents of the `UEs` and `TestCases` sub-folder describe the behavior of the 5Genesis Platform when an Experiment 
execution request is received. These folders will be automatically generated if they do not exist. The ELCM will load
the contents of every `yml` file contained in these folders on startup and whenever the `Reload facility` button on
the web dashboard is pressed. The dashboard will also display a validation log (`Facility log`) which can be used
in order to detect errors on a TestCase or UE configuration.

* UEs: The files on the `UEs` folder describe the actions to perform when a certain UE is included in the `Experiment descriptor` received
as part of the request (for example, initializing or configuring the UE). The `Composer` will add the actions defined for 
every UE to the Tasks list. The following is an example of a yaml file that configures an UE:

````yaml
TestUE:
    - Order: 1
      Task: Run.Dummy
      Requirements: [UE1]
      Config:
        Message: This is a dummy entity initialization
    - Order: 10
      Task: Run.Dummy
      Config:
        Message: This is a dummy entity closure
```` 

The name of the UE will be extracted from the initial key on the dictionary (not the name of the file). This key contains
a list of every action to perform, described by the relative `Order` in which to run, the `Task` to perform (which
correspond to the different Tasks defined in the `Executor.Tasks` package) and `Config` dictionary, which is different
for every task and optionally a list of `Requirements`. These requirements corresponds to the resources defined for the
facility. (See "Facility resources" below).

> More information about the composition process can be found in section 3.2 of Deliverable D3.15, please note that
> this example uses the old `facility.yml` file, but the behavior is the same.

* TestCases and Dashboards: Similarly to the UEs, the files in the ´TestCases´ folder define the actions required in 
order to execute a certain TestCase included in the `Experiment descriptor`. The following is an example TestCase file:

````yaml
Slice Creation:
    - Order: 5
      Task: Run.SingleSliceCreationTime
      Config:
        ExperimentId: "@{ExperimentId}"
        WaitForRunning: True
        Timeout: 60
        SliceId: "@{SliceId}"
Dashboard:
    - Name: "Slice Deployment Time"
      Measurement: Slice_Creation_Time
      Field: Slice_Deployment_Time
      Unit: "s"
      Type: Singlestat
      Percentage: False
      Size: [8, 8]
      Position: [0, 0]
      Gauge: True
      Color: ["#299c46", "rgba(237, 129, 40, 0.89)", "#d44a3a"]
      Thresholds: [0, 15, 25, 30]
```` 

The first key ('Slice Creation') follows the same format as un the UEs section, however, these files can contain an 
additional `Dashboard` key that define the list of panels that will be generated as part of the Grafana dashboard
that corresponds to the TestCase. The following values can be set for each panel:

- [Mandatory] `Type`: 'singlestat' (gauges or single value) or 'graph' (time series)
- [Optional]  `Name`: Panel name, '{Measurement}: {Field}' if not set
- [Mandatory] `Measurement`: Measurement (table) name
- [Mandatory] `Field`: Field (column) name
- [Optional]  `Unit`: Field unit
- [Mandatory] `Size`: (As list) [<height>, <width>]
- [Mandatory] `Position`: (As list) [<x>, <y>]
- [Optional]  `Color`: Graph or text color(s). For Gauges this is a list of 3 colors, otherwise a single value. Each color can be defined using these formats: "#rrggbb" or "rgba(rrr, ggg, bbb, a.aa)"

#### For graph:
- [Mandatory] `Lines`: True to display as lines, False to display as bars
- [Mandatory] `Percentage`: Whether the field is a percentage or not
- [Optional]  `Interval`: Time interval of the graph, default $__interval if not set
- [Optional]  `Dots`: Display dots along with the graph or bar

#### For singlestat:
- [Mandatory] `Gauge`: True to display as a gauge, false to display as numeric value
- [Optional]  `MaxValue`: Max expected value of the gauge, 100 if not set
- [Optional]  `MinValue`: Min expected value of the gauge, 0 if not set

### Facility resources

It is possible to define a set of available local resources. These resources can be specified as requirements for the
execution of each kind of task inside a test case.

Resources are defined by including a YAML file in the `Resources`. The contents of these files are as follows:
- `Id`: Resource ID. This Id must be unique to the facility and will be used to identify the resource on the test cases.
- `Name`: Name of the resource (visible on the ELCM dashboard).
- `Icon`: Resource icon (visible on the ELCM dashboard). Uses Font Awesome (only free icons)
[(Available icons)](https://fontawesome.com/icons?d=gallery&m=free), defaults to `fa-cash-register`.

Required resources are configured per task. When an experiment execution is received, the ELCM will generate a list of
all the required resources. When an experiment starts, all these resources will be *locked* and the execution of other
experiments with common requirements will be blocked until the running experiment finishes and their resources are
released.

### Dashboard auto-generation (Autograph)

The ELCM is able to generate additional panels if certain values appear on the names of the generated TAP results. For
this feature to work an additional result listener (AutoGraph) must be enabled in TAP. This result listener does not
require any configuration and, once enabled, the auto-generation of panels will work for any subsequently executed
experiment.

This feature works as follows:
 - During the experiment execution within TAP, the AutoGraph result listener inspects the generated results for names
   that include information about panel generation.
 - At testplan end, the result listener generates a message describing the panel to generate.
 - If the test case includes a dashboard definition the ELCM will generate the panels described in it first.
 - The logs generated during the experiment execution will be parsed, looking for messages generated by the AutoGraph
   result listener.
 - For each message detected, a new panel will be generated after the ones described in the test case.
 
The expected formats on a result name are "`<Result name> [[<Panel type>]]`" and
"`<Result name> [[<Panel type>:<Unit>]]`", where:
 - `<Result name>` is the name of the panel.
 - `<Panel type>` is one of [`Si`, `Ga`, `Li`, `Ba`], where:
    - `Si` stands for 'Single': The panel contains a single numeric value.
    - `Ga` stands for 'Gauge': The panel is a Gauge (min 0, max 100, green until 25, red after 75).
    - `Li` stands for 'Lines': The panel is a line graph.
    - `Ba` stands for 'Bars': The panel is a bars graph.
 - `<Unit>` if present, is the unit of the results. Must be recognized by Grafana, otherwise an error will be displayed
   in the panel.

> All graphs are generated with an interval of 1 sec

> Other result listeners will save the results including the panel information in the result name.

### TestCase parameters. Standard and Custom experiment:

In order to control how each TestCase is handled by the 5GENESIS Portal, several keys can be added to the yml description.
These keys are:
 - `Standard`: Boolean. Indicates wether or not the TestCase must be selectable from the list of Standard test cases.
 If not specified, this value defaults to 'False' if the `Custom` key is defined, 'True' otherwise.
 - `Custom`: List of strings. Indicates that the TestCase is a Custom test case and may accept parameters. If this value
 is set to an empty list ('[]') the test case is considered public and will appear on the list of Custom experiments for
 all users of the Portal. If the list contains one or more email addresses, the test case will be visible only to the users
 with matching emails.
 - `Parameters`: Dictionary of dictionaries, where each entry is defined as follows:
 ```yaml
"<Parameter Name>":
    Type: "String, used to guide the user as to what is the expected format"
    Description: "String, textual description of the parameter"
 ```

Parameters can be used to customize the execution of test cases. For example, a Test Case may be implemented using a TAP test plan,
that accepts an external parameter called 'Interval'. Using variable expansion the value of this external parameter can be linked
with the value of an 'Interval' (or a different name) parameter contained in the experiment descriptor. 

It is also possible to define default values during variable expansion, which means that a Test Case can be defined as 'Standard', 
where it will use the default values for all parameters, and 'Custom', where some of the values can be replaced by the experimenter.

For more information see the 'Variable expansion' section below.

> Parameters with the equal names from different test cases are considered to be **the same**: They will appear only once in the
Portal when the user selects multiple test cases and will have the same value at run time. For example, if two different test cases
define an 'Interval' parameter and are both included in the same experiment they will share the same value.
> - If it's necessary to configure these values separately please use different names.
> - If a parameter is defined in multiple test cases with different Type or Description a warning will be displayed on the ELCM interface. The information displayed on the Portal will correspond to one (any one) of the definitions.

### Available Tasks:

The following is a list of the tasks that can be defined as part of a TestCase or UE list of actions, as well as their
configuration values:

#### Run.CliExecute
Executes a script or command through the command line. Configuration values:
- `Parameters`: Parameters to pass to the command line (i.e. the line to write on the CLI)
- `CWD`: Working directory where the command will run

#### Run.CompressFiles
Generates a Zip file that contains all the specified files. Configuration values:
- `Files`: List of (single) files to add to the Zip file
- `Folders`: List of folders to search files from. All the files contained within
these folders and their sub-folders will be added to the Zip file
- `Output`: Name of the Zip file to generate. 

#### Run.CsvToInflux
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

#### Run.Delay
Adds a configurable time wait to an experiment execution. Has a single configuration value:
- `Time`: Time to wait in seconds.

#### Run.Dummy
Dummy action, will only display the values on the `Config` dictionary on the log

#### Run.Message
Displays a message on the log, with the configured severity. Configuration values:
- `Severity`: Severity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `Message`: Text of the message

#### Run.Publish
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

#### Run.SingleSliceCreationTime
Sends the Slice Creation Time reported by the Slice Manager to InfluxDb. This task will not perform any deployment
 by itself, and will only read the values for an slice deployed during the experiment pre-run stage.
Configuration values:
- `ExecutionId`: Id of the execution (can be dinamically expanded from `@{ExecutionId}`)
- `WaitForRunning`: Boolean, wait until the Slice Manager reports that the slice is running, or retrieve results immediately
- `Timeout`: 'WaitForRunning' timeout in (aprox) seconds
- `SliceId`: Slice ID to check (can be dinamically expanded from `@{SliceId}`)

#### Run.SliceCreationTime
Repeats a cycle of slice creation and deletion for a configured number of times, obtaining the Slice Creation Time on
each iteration and sending the values to the configured InfluxDb database. This task does not take into account the
slices deployed during the experiment's pre-run stage (if any). This task uses a local NEST file to describe the
slice to be deployed. Configuration values:
- `ExecutionId`: Id of the execution (can be dinamically expanded from `@{ExecutionId}`)
- `NEST`: Absolute path of the NEST file to use
- `Iterations`: Number of iterations. Defaults to 25
- `Timeout`: Timeout in (aprox) seconds to wait until the slice is running or deleted before skipping the iteration.
If not specified or set to None the task will continue indefinitelly.
- `CSV`: If set, save the generated results to a CSV file in the specified path. In case of error while sending the
results to InfluxDb a CSV file will be forcibly created on `"@{TempFolder}/SliceCreationTime.csv"` (only if not set,
otherwise the file will be created as configured).

#### Run.TapExecute
Executes a TAP TestPlan, with the possibility of configuring external parameters. Configuration values:
- `TestPlan`: Path (absolute) of the testplan file.
- `GatherResults`: Indicates whether or not to compress the generated CSV files to a Zip file (see below)
- `External`: Dictionary of external parameters 

###### Gathering generated results
If selected, the task will attempt to retrieve all the results generated by the testplan, saving them to a Zip file
that will be included along with the logs once the execution finishes. The task will look for the files in the TAP
Results folder, inside a sub-folder that corresponds with the experiment's execution ID, for this reason, it is 
necessary to add a MultiCSV result listener to TAP that has the following (recommended) `File Path` configuration:
```
Results\{Identifier}\{Date}-{ResultType}-{Identifier}.csv
```

##### Variable expansion

It's possible to expand the value of some variables enclosed by @{ }. (Use quotes where required in order to generate 
valid YAML format). Available values are:
- `@{ExecutionId}:` Experiment execution ID (unique identifier)
- `@{SliceId}`: ID of the slice deployed by the Slice Manager during the PreRun stage
- `@{TempFolder}`: Temporal folder exclusive to the current executor, it's deleted when the experiment finishes.
- `@{Application}`: The `Application` field from the Experiment Descriptor
- `@{JSONParameters}`: The `Parameters` dictionary from the Experiment Descriptor, in JSON format (a single line string)
- `@{ReservationTime}`: The `ReservationTime` field of the Experiment Descriptor (minutes), or 0 if not defined
- `@{ReservationTimeSeconds}`: Same as above, but converted to seconds.
- `@{TapFolder}`: Folder where the (Open)TAP executable is located (as configured in `config.yml`)
- `@{TapResults}`: Folder where the (Open)TAP results are saved (as configured in `config.yml`)

Separate values from the `Parameters` dictionary can also be expanded using the following expressions:
- `@[Params.key]`: The value of `key` in the dictionary, or `<<UNDEFINED>>` if not found
- `@[Params.key:default]`: The value of `key` in the dictionary, or `default` if not found

> A keen reader may notice that this expressions are very similar to the ones defined for `Run.Publish`: They are 
> implemented together, but use different dictionaries when looking for values. When a expression does not include 
> a '.' the ELCM will falls back to looking at the Publish values (the default for Release A). If the collection 
> is not 'Publish' or 'Params', the expression will be replaced by `<<UNKNOWN GROUP {collection}>>`

## PDF Report generation

It's possible to integrate an instance of [Grafana reporter](https://github.com/IzakMarais/reporter) in order to 
generate PDF reports from the Grafana dashboards of the experiments. This feature will appear as a button on the 
top-right of the dashboard.

For using this feature in the ELCM you only need to specify the URL where `Grafana reporter` is reachable. Please refer 
to the reporter documentation for the configuration of the reporter itself. 

The following is an example of a custom template that includes the 5 Genesis branding:

```tex
%use square brackets as golang text templating delimiters
\documentclass{article}
\usepackage{graphicx}
\usepackage[margin=1in]{geometry}
\graphicspath{ {images/} }

\begin{document}
\title{
\includegraphics[scale=1.0]{<<PATH TO 5GENESIS LOGO>>}~\\
5 Genesis [[.Title]] [[if .VariableValues]] \\ \large [[.VariableValues]] [[end]] [[if .Description]] 
%\small [[.Description]] [[end]]}
\date{[[.FromFormatted]] to [[.ToFormatted]]}
\maketitle
\begin{center}
[[range .Panels]][[if .IsSingleStat]]\begin{minipage}{0.3\textwidth}
\includegraphics[width=\textwidth]{image[[.Id]]}
\end{minipage}
[[else]]\par
\vspace{0.5cm}
\includegraphics[width=\textwidth]{image[[.Id]]}
\par
\vspace{0.5cm}
[[end]][[end]]
\end{center}
\end{document}
```
> Remember to specify the correct path to the 5Genesis logo

## REST API

Information about the current REST API of the ELCM (and Portal) can be seen [in BSCW](https://bscw.fokus.fraunhofer.de/bscw/bscw.cgi/d3228781/OpenAPIv1.docx).

## Authors

* **Bruno Garcia Garcia**

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   > <http://www.apache.org/licenses/LICENSE-2.0>

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.