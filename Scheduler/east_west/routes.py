from Scheduler.east_west import bp
from Scheduler.execution import handleExecutionResults, executionOrTombstone
from flask import jsonify, request, json, redirect, url_for
from Status import ExecutionQueue
from Helper import InfluxDb
from Settings import Config


notFound = {'success': False, 'message': 'Execution ID not found'}
hiddenVariables = ['Configuration', 'Descriptor']

@bp.route('/run', methods=['POST'])
def start():
    return redirect(url_for('dispatcherApi.start'))

@bp.route('/<int:executionId>/peerDetails', methods=['POST'])
def peer(executionId: int):
    execution = executionOrTombstone(executionId)
    if execution is not None:
        data = request.json
        try:
            remoteId = data['execution_id']
        except KeyError as e:
            return jsonify({'success': False, 'message': f'Invalid payload, missing {e}'})

        if execution.RemoteId is None:
            execution.RemoteId = remoteId
            return jsonify({'success': True, 'message': f'Remote Id for experiment {executionId} set to {remoteId}'})
        else:
            return jsonify({'success': False, 'message': f'Remote Id for experiment {executionId} was already set'})
    else:
        return jsonify(notFound)

# Note: Routes below can operate with finished exeperiments

@bp.route('/<int:executionId>/status')
def status(executionId: int):
    execution = executionOrTombstone(executionId)
    if execution is not None:
        payload = {'success': True, 'status': execution.CoarseStatus.name, 'milestones': execution.Milestones,
                   'message': f'Status of execution {executionId} retrieved successfully'}
        return jsonify(payload)
    else:
        return jsonify(notFound)


@bp.route('/<int:executionId>/values')
@bp.route('/<int:executionId>/values/<name>')
def values(executionId: int, name: str = None):
    execution = ExecutionQueue.Find(executionId)
    if execution is not None:
        variables = {}
        for key, value in execution.Params.items():
            if key not in hiddenVariables:
                variables[str(key)] = str(value)
        if name is None:
            return jsonify({'success': True, 'values': variables,
                            'message': f'Variables of execution {executionId} retrieved successfully'})
        else:
            if name in variables.keys():
                return jsonify({'success': True, 'value': variables[name],
                                'message': f"Value of '{name}' for execution {executionId} retrieved successfully"})
            else:
                return jsonify({'success': False,
                                'message': f"Value of '{name}' is not available for execution {executionId}"})
    else:
        return jsonify(notFound)


@bp.route('/<int:executionId>/results')
def results(executionId: int):
    execution = executionOrTombstone(executionId)
    if execution is not None:
        if Config().InfluxDb.Enabled:
            influx = InfluxDb()
            measurements = influx.GetExecutionMeasurements(executionId)
            data = {}

            for measurement in measurements:
                payloads = influx.GetMeasurement(executionId, measurement)
                data[measurement] = []

                for payload in payloads:
                    if len(payload.Points) != 0:
                        header = list(payload.Points[0].Fields.keys())
                        points = []
                        for point in payload.Points:
                            fields = point.Fields
                            values = [fields[value] for value in header]

                            points.append([point.Time.timestamp(), values])
                        data[measurement].append({
                            'tags': payload.Tags,
                            'header': header,
                            'points': points
                        })

            return jsonify({'success': True, 'measurements': measurements, 'data': data,
                            'message': f"Results for execution {executionId} retrieved successfully"})
        else:
            return {'success': False, 'message': 'Database not available'}
    else:
        return jsonify(notFound)


# Shared implementation with execution.results
@bp.route('<int:executionId>/files')
def files(executionId: int):
    return handleExecutionResults(executionId)
