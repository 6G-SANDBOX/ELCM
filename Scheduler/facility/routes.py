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

                if isinstance(data, dict):
                    if data.get("Version") == 2 and data.get("Name") == test_case_name:
                        os.remove(file_path)
                        deleted_files.append(filename)
                    elif test_case_name in data:
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

    if not uploaded:
        return jsonify({"success": False, "message": "No file received"}), 400
    if not uploaded.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "Invalid file extension. Only .yml allowed."}), 400

    # Determine destination folder
    if file_type == 'ues':
        folder = Facility.UE_FOLDER
    else:
        folder = Facility.TESTCASE_FOLDER

    # 1) Read the YAML content to extract the internal Name field
    try:
        raw_bytes = uploaded.read()
        data = yaml.safe_load(raw_bytes)
    except Exception as e:
        return jsonify({"success": False, "message": f"Invalid YAML: {e}"}), 400

    # Reset the stream position so we can save the file later
    uploaded.stream.seek(0)

    # Extract the internal name
    if isinstance(data, dict) and data.get("Version") == 2 and "Name" in data:
        name = data["Name"]
    elif isinstance(data, dict):
        # Fallback to the first root key
        name = next(iter(data.keys()))
    else:
        return jsonify({"success": False, "message": "YAML does not contain a valid mapping"}), 400

    # 2) Remove any existing files with the same internal Name
    for fn in os.listdir(folder):
        if not fn.lower().endswith('.yml'):
            continue
        path = os.path.join(folder, fn)
        try:
            existing = yaml.safe_load(open(path, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(existing, dict) and (
            (existing.get("Version") == 2 and existing.get("Name") == name)
            or name in existing
        ):
            os.remove(path)

    # 3) Save the new file using the original filename
    save_path = os.path.join(folder, uploaded.filename)
    try:
        uploaded.save(save_path)
        Facility.Reload()
        return jsonify({
            "success": True,
            "message": f"{'UEs' if file_type == 'ues' else 'Test case'} '{uploaded.filename}' uploaded successfully"
        })
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

@bp.route('/testcases/info', methods=['POST'])
def facilityTestCasesInfo():
    data = request.get_json()
    requested_testcases = set(data.get("TestCases", []))
    requested_ues = set(data.get("UEs", []))

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
                if (isinstance(data, dict) and
                    ((data.get("Version") == 2 and data.get("Name") == name)
                     or name in data)):
                    try:
                        raw_versions.append(open(path, encoding="utf-8").read())
                    except Exception:
                        continue
            if raw_versions:
                out[name] = raw_versions
        return out

    testcases_raw = load_raw(Facility.TESTCASE_FOLDER, Facility.testCases, requested_testcases)
    ues_raw       = load_raw(Facility.UE_FOLDER,      Facility.ues,      requested_ues)

    return jsonify({
        "TestCases": testcases_raw,
        "UEs":       ues_raw
    })