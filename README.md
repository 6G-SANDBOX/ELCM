# ELCM (Experiment Life-Cycle Manager)

## Requirements

 - [Python 3.12.x](https://www.python.org) (see requirements.txt for a detailed view of required packages)

### Optional integrations:

 - [Portal](https://gitlab.com/morse-uma/elcm-portal) Version 3.2.2 or later
 - [Katana Slice Manager](https://github.com/5genesis/katana-slice_manager) Version 2.2.6 (14/07/2020) or later

#### Third party components

 - [Grafana](https://grafana.com/) (tested with versions 5.4 and 11.3.0)
 - [InfluxDB](https://www.influxdata.com/products/influxdb/) (tested with versions 1.7.6 and 2.7.10)
 - [OpenTAP](https://www.opentap.io/) (tested with version 9.9 (Windows))
 - [Grafana reporter](https://github.com/IzakMarais/reporter) (tested with version 2.1.0, commit 41b38a0)

## Deployment

### Installation procedure

> Additional dependencies may be needed depending on your environment. For example, older Windows versions may require
certain Visual C++ redistributables to be installed, and the following packages are known to be required on many Ubuntu
distributions: `gcc python3.12 python3.12-venv python3.12-dev`.

This repository includes two sets of scripts for use on Linux (`.sh`) and Windows (`.ps1`) machines. In general,
these scripts should be able to perform most of the actions required for instantiating the ELCM, however, depending
on the deployment environment some actions may fail or require additional tweaking. The contents of the scripts can
be used as a guide for manual installation, and a description of the actions performed by the scripts is included below
for use as reference.

1. Ensure that Python 3.12.x is installed. For environments with multiple Python versions note the correct alias.
   > For example, older Ubuntu distributions refer to Python 2.x by default when invoking `python`, and reference 
   > Python 3.12 as `python3` or `python3.12`. Use the `--version` parameter to check the version number.
2. Clone the repository to a known folder
3. Run `install.sh <python_alias>` or `install.ps1 <python_alias>` (depending on your OS). The script will:
   - Display the Python version in use (ensure that this is 3.12.x)
   - Create a [Python virtual environment](https://virtualenv.pypa.io/en/stable/) for exclusive use of the ELCM.
   - Install the required Python packages (using [pip](https://pypi.org/project/pip/))
   > Most issues occur during this step, since it is highly dependent on the environment. In case of error, note the 
   > name of the package that could not be installed, the error message and your OS distribution. Performing an Internet 
   > search with this information usually yields a solution. Once solved you may re-run the script (delete the `venv` 
   > folder that was created by the script if necessary) until all packages are correctly installed.
4. Run `start.sh` or `start.ps1` (depending on your OS). This will create an empty configuration file (`config.yml`).
   If necessary, press ctrl+c (or your OS equivalent) in order to close the server.
5. Ensure that the `config.yml` is available in the ELCM folder and customize its contents. Information about all the 
   possible configuration values can be found below.

### Starting the ELCM

> Before using the scripts for starting a production ELCM instance consider changing the `<YOUR SECRET KEY HERE>`  
> value to a random string (for more info see [this answer](https://stackoverflow.com/a/22463969).). This is  
> particularly important if the ELCM port is exposed to the Internet (in this case also consider using `waitress`,  
> as can be seen in the Portal scripts).  
>   
> Please note that **it is not recommended exposing the ELCM to the open Internet**, regardless of these tips.

Once configured, the ELCM can be started by running `start.sh <port_number>` or `start.ps1 <port_number>`. If not
specified, the server will listen on port 5001. In order to stop the server, press ctrl+c (or your OS equivalent) in
the terminal where the server is running.

## Documentation

Detailed usage documentation can be found in the `docs` folder of this repository. 

1. [ELCM Configuration](/docs/1_CONFIGURATION.md)
2. Platform Registry:
   1. [Facility Configuration](/docs/2-1_FACILITY_CONFIGURATION.md)
   2. [TestCase Parameters](/docs/2-2_TESTCASE_PARAMETERS.md)
   3. [TestCase Dashboard, PDF Creation](/docs/2-3_DASHBOARD_PDF.md)
   4. [Resources, Scenarios and Network Slices ](/docs/2-4_RESOURCE_SCENARIO_NS.md)
3. TestCase Definition:
   1. Task Order and Execution Flow:
      1. [Experiment Composition, Top-Level Tasks and Children](/docs/3-1a-COMPOSITION.md)
      2. [Flow Control Tasks](/docs/3-1b_FLOW_TASKS.md)
   2. Available Tasks:
      1. [General Tasks](/docs/3-2a_GENERAL_TASKS.md)
      2. [EVOLVED-5G Tasks](/docs/3-2b_EVOLVED-5G_TASKS.md)
   3. [Variable Expansion and Execution Verdict](/docs/3-3_VARIABLE_EXPANSION_VERDICT.md)
   4. [MONROE Experiments](/docs/3-4_MONROE.md)
   5. [Implementing Additional Tasks](/docs/3-5_TASK_IMPLEMENTATION.md)
4. [Distributed Experiments](/docs/4_DISTRIBUTED.md)

#### Appendix
1. [REST Endpoints](/docs/A1_ENDPOINTS.md)
2. [Experiment Descriptor](/docs/A2_EXPERIMENT_DESCRIPTOR.md)
3. [Misc configurations](/docs/A3_MISC_CONFIGURATIONS.md)

## Authors

* **[Bruno Garcia Garcia](https://github.com/NaniteBased)**

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
