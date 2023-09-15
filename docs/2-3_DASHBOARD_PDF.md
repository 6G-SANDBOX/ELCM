# Test case dashboard

If a Grafana instance is available and configured, the ELCM can automatically create a Dashboard for displaying
some of the most important raw results generated during an experiment execution. In order to use this functionality,
the test case definition must include a collection of Grafana panel definitions. For each experiment execution, the
panels defined by all the test cases selected will be aggregated in a single dashboard. An example of dashboard
definition with a single panel can be seen below.

````yaml
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

The following values can be set for each panel:

- [Mandatory] `Type`: 'singlestat' (gauges or single value) or 'graph' (time series)
- [Optional]  `Name`: Panel name, '{Measurement}: {Field}' if not set
- [Mandatory] `Measurement`: Measurement (table) name
- [Mandatory] `Field`: Field (column) name
- [Optional]  `Unit`: Field unit
- [Mandatory] `Size`: (As list) [<height>, <width>]
- [Mandatory] `Position`: (As list) [<x>, <y>]
- [Optional]  `Color`: Graph or text color(s). For Gauges this is a list of 3 colors, otherwise a single value. Each color can be defined using these formats: "#rrggbb" or "rgba(rrr, ggg, bbb, a.aa)"

###### For graph:
- [Mandatory] `Lines`: True to display as lines, False to display as bars
- [Mandatory] `Percentage`: Whether the field is a percentage or not
- [Optional]  `Interval`: Time interval of the graph, default $__interval if not set
- [Optional]  `Dots`: Display dots along with the graph or bar

###### For singlestat:
- [Mandatory] `Gauge`: True to display as a gauge, false to display as numeric value
- [Optional]  `MaxValue`: Max expected value of the gauge, 100 if not set
- [Optional]  `MinValue`: Min expected value of the gauge, 0 if not set

# Dashboard auto-generation (Autograph)

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

# PDF Report generation

It's possible to integrate an instance of [Grafana reporter](https://github.com/IzakMarais/reporter) in order to
generate PDF reports from the Grafana dashboards of the experiments. This feature will appear as a button on the
top-right of the dashboard.

For using this feature in the ELCM you only need to specify the URL where `Grafana reporter` is reachable. Please
refer to the reporter documentation for the configuration of the reporter itself.

The following is an example of a custom template that includes the 5Genesis branding:

```tex
%use square brackets as golang text templating delimiters
\documentclass{article}
\usepackage{graphicx}
\usepackage[margin=1in]{geometry}
\graphicspath{ {images/} }

\begin{document}
\title{
\includegraphics[scale=1.0]{<<PATH TO 5GENESIS LOGO>>}~\\
5Genesis [[.Title]] [[if .VariableValues]] \\ \large [[.VariableValues]] [[end]] [[if .Description]]
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