from Scheduler.facility import bp
from Facility import Facility
from Interfaces import Management
from flask import jsonify
from typing import Dict
import os
from flask import request
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
    file = request.files.get('test_case')
    file_type = request.form.get('file_type', 'testcase')

    if not file:
        return jsonify({"success": False, "message": "No file received"}), 400
    
    if not file.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "Invalid file extension. Only .yml allowed."}), 400
    
    if file_type == 'ues':
        save_folder = Facility.UE_FOLDER
    else:
        save_folder = Facility.TESTCASE_FOLDER

    save_path = os.path.join(save_folder, file.filename)

    if os.path.exists(save_path):
        return jsonify({"success": False, "message": f"File {file.filename} already exists."}), 400

    try:
        file.save(save_path)
        Facility.Reload()
        return jsonify({
            "success": True,
            "message": f"{'UEs' if file_type == 'ues' else 'Test case'} {file.filename} uploaded successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving file: {str(e)}"}), 500

@bp.route('/testcases/info')
def facilityTestCasesInfo():
    result = {
        name: [str(entry) for entry in entries]
        for name, entries in Facility.testCases.items()
    }
    return jsonify({"TestCases": result})