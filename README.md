# ELCM (Experiment Life-Cycle Manager)

## Requirements

 - [Python 3.7.x](https://www.python.org)
 - [Optional] [Grafana](https://grafana.com/) (tested on version 5.4)
 - [Optional] [Grafana reporter](https://github.com/IzakMarais/reporter) (tested on version 2.1.0, commit 41b38a0cfe91ac3fd21c5d759bd41d3e76bdc3d0)

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
* FLASK_RUN_PORT: Port where the portal will listen (5001 by default)

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
* Flask:
    * SECRET_KEY: A random string.
> Since the ELCM should not be exposed to the Internet it is not so important to set a random SECRET_KEY. However, the 
value is still needed and it's recommended to follow the same approach as in the 5Genesis Portal.
* Tap: 
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
    * ReportGenerator: URL where the `Grafana reporter` instance can be reached
> These values will be used when generating a dashboard for the results generated by an experiment execution.

## facility.yml

The `facility.yml` describes the behavior of the 5Genesis Platform when an Experiment execution request is received.
An example file will be generated automatically if it does not exist when the first request is received. The file is
composed by 3 sections:

* UEs: The `UEs` section describes the actions to perform when a certain UE is included in the `Experiment descriptor` received
as part of the request (for example, initializing or configuring the UE). The `Composer` will add the actions defined for 
every UE to the Tasks list.

* TestCases: Similarly to the `UEs` section, this section defines the actions required to execute a certain TestCase included in the
`Experiment descriptor`.

* Dashboards: This section specifies what are the panels to create in the Grafana dashboard that can be generated after an experiment
execution has finished.

More information about the possible values to use in this file and the behavior of the composer when generating the list
of tasks to execute can be seen on the example file (also at `./Facility/default_facility`). 

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

TBD