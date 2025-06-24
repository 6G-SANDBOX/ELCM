from Scheduler.facility import bp
from Facility import Facility
from Interfaces import Management
from flask import jsonify, request
from typing import Dict, List
import os
import yaml

@bp.route('/resource_status')
def resourceStatus():
    busy = Facility.BusyResources()
    idle = Facility.IdleResources()
    busyIds = [res.Id for res in busy]
    idleIds = [res.Id for res in idle]

    return jsonify({'Busy': busyIds, 'Idle': idleIds})


@bp.route('/ues')
def facilityUes():
    user_id = request.args.get('user_id')
    if user_id and user_id.isdigit():
        folder = Facility.ue_folder(user_id)
        names: List[str] = []
        for fn in os.listdir(folder):
            if not fn.lower().endswith('.yml'):
                continue
            path = os.path.join(folder, fn)
            try:
                data = yaml.safe_load(open(path, encoding='utf-8'))
            except Exception:
                continue

            if isinstance(data, dict):
                if 'Name' in data:
                    name = data['Name']
                elif len(data) == 1:
                    name = next(iter(data.keys()))
                else:
                    continue
            else:
                continue

            if name in Facility.ues:
                names.append(name)

        ues = sorted(names)
    else:
        ues = sorted(list(Facility.ues.keys()))

    return jsonify({'UEs': ues})


@bp.route('/testcases')
def facilityTestCases():
    user_id = request.args.get('user_id')
    if user_id and user_id.isdigit():
        folder = Facility.testcase_folder(user_id)
        items: List[(str, Dict[str, object])] = []
        for fn in os.listdir(folder):
            if not fn.lower().endswith('.yml'):
                continue
            path = os.path.join(folder, fn)
            try:
                data = yaml.safe_load(open(path, encoding='utf-8'))
            except Exception:
                continue

            if isinstance(data, dict):
                if 'Name' in data:
                    name = data['Name']
                elif len(data) == 1:
                    name = next(iter(data.keys()))
                else:
                    continue
            else:
                continue

            if name != 'MONROE_Base' and name in Facility.testCases:
                items.append((name, Facility.GetTestCaseExtra(name).copy()))
    else:
        items = [
            (tc, Facility.GetTestCaseExtra(tc).copy())
            for tc in Facility.testCases
            if tc != 'MONROE_Base'
        ]

    res = []
    for name, extra in sorted(items, key=lambda x: x[0]):
        parametersDict: Dict[str, Dict[str, str]] = extra.pop('Parameters', {})
        parameters = []
        extra['Name'] = name
        for key in sorted(parametersDict.keys()):
            info = parametersDict[key]
            info['Name'] = key
            parameters.append(info)
        extra['Parameters'] = parameters
        res.append(extra)

    return jsonify({'TestCases': res})


@bp.route('/baseSliceDescriptors')
def baseSliceDescriptors():
    sliceManager = Management.SliceManager()
    return jsonify({"SliceDescriptors": sliceManager.GetBaseSliceDescriptors()})


@bp.route('/scenarios')
def scenarios():
    user_id = request.args.get('user_id')
    if user_id and user_id.isdigit():
        folder = Facility.scenario_folder(user_id)
        names: List[str] = []
        for fn in os.listdir(folder):
            if not fn.lower().endswith('.yml'):
                continue
            path = os.path.join(folder, fn)
            try:
                data = yaml.safe_load(open(path, encoding='utf-8'))
            except Exception:
                continue

            if isinstance(data, dict):
                if 'Name' in data:
                    name = data['Name']
                elif len(data) == 1:
                    name = next(iter(data.keys()))
                else:
                    continue
            else:
                continue

            if name in Facility.scenarios:
                names.append(name)

        scenarios = sorted(names)
    else:
        scenarios = sorted(list(Facility.scenarios.keys()))

    return jsonify({'Scenarios': scenarios})


@bp.route('/testcases/delete', methods=['POST'])
def deleteTestCase():
    data = request.json
    test_case_name = data.get('test_case_name')
    file_type = data.get('file_type', 'testcase')
    user_id = data.get('user_id')

    if not test_case_name:
        return jsonify({"success": False, "message": "No test case name provided"}), 400
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required"}), 400

    if file_type == 'testcase':
        try:
            folder, files_dict = (
                Facility.testcase_folder(user_id), Facility.testCases
            )
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400
    elif file_type == 'ues':
        try:
            folder, files_dict = (
                Facility.ue_folder(user_id), Facility.ues
            )
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400
    elif file_type == 'scenarios':
        try:
            folder, files_dict = (
                Facility.scenario_folder(user_id), Facility.scenarios
            )
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400
    else:
        return jsonify({"success": False, "message": f"Invalid file type: {file_type}"}), 400

    if test_case_name not in files_dict:
        return jsonify({"success": False, "message": f"{file_type} {test_case_name} not found"}), 404

    try:
        deleted_files = []

        for filename in os.listdir(folder):
            if not filename.lower().endswith('.yml'):
                continue
            file_path = os.path.join(folder, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
            except yaml.YAMLError:
                continue

            if isinstance(data, dict) and (
                data.get("Name") == test_case_name
                or test_case_name in data
            ):
                os.remove(file_path)
                deleted_files.append(filename)

        if not deleted_files:
            return jsonify({"success": False, "message": f"{file_type} {test_case_name} file was not found"}), 404

        del files_dict[test_case_name]
        Facility.Reload()

        return jsonify({
            "success": True,
            "message": f"{file_type} {test_case_name} deleted and {len(deleted_files)} file(s) removed"
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting {file_type}: {str(e)}"}), 500


@bp.route('/upload_test_case', methods=['POST'])
def upload_test_case():
    uploaded = request.files.get('test_case')
    file_type = request.form.get('file_type', 'testcase')
    user_id = request.form.get('user_id')

    # 1) Basic validations
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required"}), 400
    if not uploaded:
        return jsonify({"success": False, "message": "No file received"}), 400
    if not uploaded.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "Only .yml files are allowed"}), 400

    # 2) Determine destination folder
    if file_type == 'ues':
        try:
            folder = Facility.ue_folder(user_id)
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400
    elif file_type == 'scenarios':
        try:
            folder = Facility.scenario_folder(user_id)
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400
    else:
        try:
            folder = Facility.testcase_folder(user_id)
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400

    # 3) Read and parse YAML
    try:
        content = uploaded.read()
        data = yaml.safe_load(content)
    except Exception as e:
        return jsonify({"success": False, "message": f"Invalid YAML: {e}"}), 400

    # 3.1) Enforce: if 'Name' exists, 'Version' must be 2 (and vice versa)
    if isinstance(data, dict):
        version = data.get("Version")
        has_name = "Name" in data
        if (has_name and version != 2) or (version == 2 and not has_name):
            return jsonify({
                "success": False,
                "message": "Invalid format: when using the 'Name' field, 'Version: 2' is required and vice versa."
            }), 400

    # 4) Reset stream position for saving the file later
    uploaded.stream.seek(0)

    # 5) Determine internal name
    if isinstance(data, dict) and "Name" in data:
        internal_name = data["Name"]
    elif isinstance(data, dict):
        internal_name = next(iter(data.keys()))
    else:
        return jsonify({
            "success": False,
            "message": "YAML must be a mapping with a 'Name' field or a root key"
        }), 400

    # 6) Delete existing files with the same internal_name
    for filename in os.listdir(folder):
        if not filename.lower().endswith('.yml'):
            continue
        path = os.path.join(folder, filename)
        try:
            with open(path, encoding='utf-8') as f:
                existing = yaml.safe_load(f)
        except Exception:
            continue

        if isinstance(existing, dict) and (
            existing.get("Name") == internal_name or internal_name in existing
        ):
            os.remove(path)

    # 7) Save the new file using its original filename
    save_path = os.path.join(folder, uploaded.filename)
    try:
        uploaded.save(save_path)
        Facility.Reload()
        return jsonify({
            "success": True,
            "message": f"{'UEs' if file_type == 'ues' else ('Scenarios' if file_type == 'scenarios' else 'Test case')} '{internal_name}' uploaded successfully"
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving file: {e}"}), 500


def convert_to_dict(obj):
    """Recursively convert an object to a serializable dictionary."""
    if isinstance(obj, list):
        return [convert_to_dict(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return {key: convert_to_dict(value) for key, value in vars(obj).items()}
    else:
        return obj


def load_raw(folder: str, index: Dict[str, object], names: set) -> Dict[str, List[str]]:
    out = {}
    for name in names:
        if name not in index:
            continue
        raw_versions = []
        for fn in os.listdir(folder):
            if not fn.lower().endswith(".yml"):
                continue
            path = os.path.join(folder, fn)
            try:
                data = yaml.safe_load(open(path, encoding="utf-8"))
            except Exception:
                continue

            if isinstance(data, dict) and (data.get("Name") == name or name in data):
                try:
                    raw_versions.append(open(path, encoding="utf-8").read())
                except Exception:
                    continue
        if raw_versions:
            out[name] = raw_versions
    return out

@bp.route('/testcases/info', methods=['POST'])
def facilityTestCasesInfo():
    data = request.get_json()
    requested_testcases = set(data.get("TestCases", []))
    requested_ues = set(data.get("UEs", []))
    requested_scenarios = set(data.get("Scenarios", []))
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required"}), 400
    try:
        tc_folder = Facility.testcase_folder(user_id)
        ue_folder = Facility.ue_folder(user_id)
        sc_folder = Facility.scenario_folder(user_id)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    testcases_raw = load_raw(tc_folder, Facility.testCases, requested_testcases)
    ues_raw       = load_raw(ue_folder,    Facility.ues,       requested_ues)
    scenarios_raw = load_raw(sc_folder,    Facility.scenarios, requested_scenarios)

    return jsonify({
        "TestCases": testcases_raw,
        "UEs":       ues_raw,
        "Scenarios": scenarios_raw
    })


@bp.route('/edit_test_case', methods=['POST'])
def edit_test_case():
    uploaded = request.files.get('test_case')
    file_type = request.form.get('file_type', 'testcase')
    user_id = request.form.get('user_id')

    # 1) Basic validation
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required"}), 400
    
    if not uploaded or not uploaded.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "No file received or invalid extension"}), 400

    orig_name = uploaded.filename.rsplit('.', 1)[0]

    # 2) Read & parse YAML
    raw = uploaded.read()
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return jsonify({"success": False, "message": f"Invalid YAML: {e}"}), 400

    # Rewind for saving later
    uploaded.stream.seek(0)

    # 3) Enforce: if 'Name' exists, 'Version' must be 2 (and vice versa)
    if isinstance(doc, dict):
        version = doc.get("Version")
        has_name = "Name" in doc
        if (has_name and version != 2) or (version == 2 and not has_name):
            return jsonify({
                "success": False,
                "message": "Invalid format: when using the 'Name' field, 'Version: 2' is required and vice versa."
            }), 400

    # 4) Determine internal_name
    if isinstance(doc, dict) and "Name" in doc:
        internal_name = doc["Name"]
    elif isinstance(doc, dict):
        internal_name = next(iter(doc.keys()))
    else:
        return jsonify({
            "success": False,
            "message": "YAML must be a mapping with a 'Name' field or a root key"
        }), 400

    # 5) Determine folder
    try:
        if file_type == 'ues':
            folder = Facility.ue_folder(user_id)
        elif file_type == 'scenarios':
            folder = Facility.scenario_folder(user_id)
        else:
            folder = Facility.testcase_folder(user_id)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    # 6) Delete files
    if orig_name != internal_name:
        old_path = os.path.join(folder, f"{orig_name}.yml")
        try:
            os.remove(old_path)
        except OSError:
            pass

    for fn in os.listdir(folder):
        if not fn.lower().endswith('.yml'):
            continue
        path = os.path.join(folder, fn)
        try:
            with open(path, encoding='utf-8') as f:
                existing = yaml.safe_load(f)
        except Exception:
            continue

        if isinstance(existing, dict) and (
            existing.get("Name") == internal_name or internal_name in existing
        ):
            try:
                os.remove(path)
            except OSError:
                pass

    # 7) Save new YAML
    save_path = os.path.join(folder, f"{internal_name}.yml")
    try:
        uploaded.save(save_path)
        Facility.Reload()
        return jsonify({
            "success": True,
            "message": f"{file_type.capitalize()} '{internal_name}' updated successfully"
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving file: {e}"}), 500
    
@bp.route('/execution/info', methods=['POST'])
def get_execution_info():
    data = request.get_json()
    execution_id = data.get("ExecutionId")

    if not execution_id:
        return jsonify({"success": False, "message": "ExecutionId is required"}), 400

    folder = os.path.abspath("Persistence/Executions_yml")
    if not os.path.exists(folder):
        return jsonify({"success": False, "message": "Execution folder not found"}), 404

    testcases = {}
    ues = {}
    scenarios = {}

    for filename in os.listdir(folder):
        if not filename.endswith(".yml"):
            continue

        if filename.startswith(f"{execution_id}_testcase_"):
            name = filename.replace(f"{execution_id}_testcase_", "").replace(".yml", "")
            path = os.path.join(folder, filename)
            try:
                with open(path, encoding='utf-8') as f:
                    testcases[name] = [f.read()]
            except Exception:
                continue

        elif filename.startswith(f"{execution_id}_ue_"):
            name = filename.replace(f"{execution_id}_ue_", "").replace(".yml", "")
            path = os.path.join(folder, filename)
            try:
                with open(path, encoding='utf-8') as f:
                    ues[name] = [f.read()]
            except Exception:
                continue

        elif filename.startswith(f"{execution_id}_scenario_"):
            name = filename.replace(f"{execution_id}_scenario_", "").replace(".yml", "")
            path = os.path.join(folder, filename)
            try:
                with open(path, encoding='utf-8') as f:
                    scenarios[name] = [f.read()]
            except Exception:
                continue

    if not testcases and not ues and not scenarios:
        return jsonify({
            "success": False,
            "message": f"No testcases, UEs or Scenarios found for execution ID '{execution_id}'"
        }), 404

    return jsonify({
        "ExecutionId": execution_id,
        "TestCases": testcases,
        "UEs": ues,
        "Scenarios": scenarios
    }), 200
