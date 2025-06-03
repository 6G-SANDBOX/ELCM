from flask import jsonify, request
from Status import ExecutionQueue
from Data import ExperimentDescriptor
from Scheduler.dispatcher import bp
from Helper import Log

@bp.route('/run', methods=['POST'])
def start():
    try:
        data = request.json
        Log.I("Received execution request")
        Log.D(f"Payload: {data}")

        if data is None:
            raise RuntimeError("Received empty payload")

        descriptor = ExperimentDescriptor(data)
        valid, reasons = descriptor.ValidityCheck

        if not valid:
            raise RuntimeError(f'Invalid experiment description: {"; ".join(reasons)}')

        params = {'Descriptor': descriptor}
        executionId = ExecutionQueue.Create(params).Id
        return jsonify({'ExecutionId': executionId})

    except Exception as e:
        message = f"Exception while processing execution request: {e}"
        Log.W(message)
        return jsonify({"success": False, "message": message}), 400
