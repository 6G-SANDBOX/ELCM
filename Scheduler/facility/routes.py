from Scheduler.facility import bp
from Facility import Facility
from Interfaces import Management
from flask import jsonify
from typing import Dict
import os
from flask import request
import yaml
from typing import Dict, List

@bp.route('/resource_status')
def resourceStatus():
    busy = Facility.BusyResources()
    idle = Facility.IdleResources()
    busyIds = [res.Id for res in busy]
    idleIds = [res.Id for res in idle]

    return jsonify({'Busy': busyIds, 'Idle': idleIds})


@bp.route('/ues')
def facilityUes():
    return jsonify({
        'UEs': sorted(list(Facility.ues.keys()))
    })


@bp.route('/testcases')
def facilityTestCases():
    res = []
    testcases = sorted(list(Facility.testCases.keys()))
    for testcase in testcases:
        if testcase == 'MONROE_Base': continue

        # Work over a copy, otherwise we end up overwriting the Facility data
        extra = Facility.GetTestCaseExtra(testcase).copy()
        parametersDict: Dict[str, Dict[str, str]] = extra.pop('Parameters', {})
        parameters = []
        extra['Name'] = testcase
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
    return jsonify({"Scenarios": list(Facility.scenarios.keys())})

@bp.route('/testcases/delete', methods=['POST'])
def deleteTestCase():
    test_case_name = request.json.get('test_case_name')
    file_type = request.json.get('file_type', 'testcase')

    if not test_case_name:
        return jsonify({"success": False, "message": "No test case name provided"}), 400

    if file_type == 'testcase':
        folder = Facility.TESTCASE_FOLDER
        files_dict = Facility.testCases
    elif file_type == 'ues':
        folder = Facility.UE_FOLDER
        files_dict = Facility.ues
    else:
        return jsonify({"success": False, "message": f"Invalid file type: {file_type}"}), 400

    if test_case_name not in files_dict:
        return jsonify({"success": False, "message": f"{file_type} {test_case_name} not found"}), 404

    try:
        deleted_files = []

        for filename in os.listdir(folder):
            if filename.endswith('.yml'):
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

    # 1) Basic validations
    if not uploaded:
        return jsonify({"success": False, "message": "No file received"}), 400
    if not uploaded.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "Only .yml files are allowed"}), 400

    # 2) Determine destination folder
    folder = Facility.UE_FOLDER if file_type == 'ues' else Facility.TESTCASE_FOLDER

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

    uploaded_version = data.get("Version") if isinstance(data, dict) else None

    # 6) Check for duplicates and block V1 → V2 upgrades
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
            existing_version = existing.get("Version")
            if (existing_version is None or existing_version == 1) and uploaded_version == 2:
                return jsonify({
                    "success": False,
                    "message": f"Upload blocked: '{internal_name}' is already defined as a V1 TestCase and cannot be replaced by a V2 version."
                }), 400

            return jsonify({
                "success": False,
                "message": f"An entry named '{internal_name}' already exists (file: {filename})"
            }), 409

    # 7) Save the new file using its original filename
    save_path = os.path.join(folder, uploaded.filename)
    if os.path.exists(save_path):
        return jsonify({"success": False, "message": f"File {uploaded.filename} already exists"}), 409

    try:
        uploaded.save(save_path)
        Facility.Reload()
        return jsonify({
            "success": True,
            "message": f"{'UEs' if file_type == 'ues' else 'Test case'} "
                       f"'{internal_name}' uploaded successfully"
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

    testcases_raw = load_raw(Facility.TESTCASE_FOLDER, Facility.testCases, requested_testcases)
    ues_raw       = load_raw(Facility.UE_FOLDER,      Facility.ues,      requested_ues)

    return jsonify({
        "TestCases": testcases_raw,
        "UEs":       ues_raw
    })

@bp.route('/edit_test_case', methods=['POST'])
def edit_test_case():
    uploaded = request.files.get('test_case')
    file_type = request.form.get('file_type', 'testcase')

    # 1) Basic validation
    if not uploaded or not uploaded.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "No file received or invalid extension"}), 400

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

    # 5) Prevent renaming
    orig_base = uploaded.filename.rsplit('.', 1)[0]
    if internal_name != orig_base:
        return jsonify({
            "success": False,
            "message": "Changing the internal 'Name' is not allowed"
        }), 400

    # 6) Ensure the resource exists
    index = Facility.ues if file_type == 'ues' else Facility.testCases
    if internal_name not in index:
        return jsonify({
            "success": False,
            "message": f"{file_type.capitalize()} '{internal_name}' does not exist"
        }), 404

    # 7) Prevent version changes (V1 ↔ V2)
    folder = Facility.UE_FOLDER if file_type == 'ues' else Facility.TESTCASE_FOLDER
    existing_doc = None
    for fn in os.listdir(folder):
        if not fn.lower().endswith('.yml'):
            continue
        path = os.path.join(folder, fn)
        try:
            with open(path, encoding='utf-8') as f:
                candidate = yaml.safe_load(f)
        except Exception:
            continue
        if isinstance(candidate, dict) and (
            candidate.get("Name") == internal_name or internal_name in candidate
        ):
            existing_doc = candidate
            break

    existing_version = existing_doc.get("Version") if isinstance(existing_doc, dict) else None
    uploaded_version = doc.get("Version") if isinstance(doc, dict) else None

    if existing_version == 2 and uploaded_version != 2:
        return jsonify({
            "success": False,
            "message": f"Editing not allowed: '{internal_name}' is a V2 TestCase and must remain Version: 2."
        }), 400

    if (existing_version is None or existing_version == 1) and uploaded_version == 2:
        return jsonify({
            "success": False,
            "message": f"Editing not allowed: '{internal_name}' is a V1 TestCase and cannot be upgraded to V2."
        }), 400

    # 8) Delete existing file(s)
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
            os.remove(path)

    # 9) Save new YAML
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

    if not testcases and not ues:
        return jsonify({
            "success": False,
            "message": f"No testcases or UEs found for execution ID '{execution_id}'"
        }), 404

    return jsonify({
        "ExecutionId": execution_id,
        "TestCases": testcases,
        "UEs": ues
    }), 200
