from flask import redirect, url_for, flash, render_template, jsonify, send_from_directory
from Status import Status, ExecutionQueue
from Experiment import ExperimentRun, Tombstone
from Scheduler.execution import bp
from typing import Union, Optional
from Settings import Config
from Data import ExperimentDescriptor
from Facility import Facility
from os.path import join, isfile, abspath


@bp.route('<int:executionId>/cancel')
def cancel(executionId: int):
    try:
        ExecutionQueue.Cancel(executionId)
        flash(f'Cancelled execution {executionId}', 'info')
    except Exception as e:
        flash(f'Error cancelling execution {executionId}: {str(e)}', 'danger')
    return redirect(url_for('index'))


@bp.route('<int:executionId>/cancel_execution_api')
def cancel_execution_api(executionId: int):
    try:
        ExecutionQueue.Cancel(executionId)
        return jsonify(success=True, message=f'Cancelled execution {executionId}'), 200
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@bp.route('<int:executionId>/delete')  # To be removed
def delete(executionId: int):
    ExecutionQueue.Delete(executionId)
    flash(f'Deleted execution {executionId}', 'info')
    return redirect(url_for('index'))


@bp.route('<int:executionId>')
def view(executionId: int):
    execution = ExecutionQueue.Find(executionId)
    if execution is None:
        try:
            execution = Tombstone(str(executionId))
        except:
            flash(f'Execution {executionId} does not exist or is not within Scheduler context', 'danger')

    if execution is None:
        return redirect(url_for('index'))
    else:
        return render_template('execution.html', execution=execution)


@bp.route('<int:executionId>/json')
@bp.route('<int:executionId>/status')
def json(executionId: int):
    execution = executionOrTombstone(executionId)
    coarse = status = 'ERR'
    verdict = 'NotSet'
    percent = 0
    messages = []
    if execution is not None:
        coarse = execution.CoarseStatus.name
        verdict = execution.Verdict.name
        if isinstance(execution, Tombstone):
            status = "Not Running"
        else:
            status = execution.Status
            percent = execution.PerCent
            messages = execution.Messages
    return jsonify({
        'Coarse': coarse, 'Status': status,
        'PerCent': percent, 'Messages': messages,
        'Verdict': verdict
    })


def executionOrTombstone(executionId: int) -> Optional[Union[ExperimentRun, Tombstone]]:
    execution = ExecutionQueue.Find(executionId)
    if execution is None:
        try:
            execution = Tombstone(str(executionId))
        except:
            execution = None
    return execution


@bp.route('<int:executionId>/logs')
def logs(executionId: int):
    execution = executionOrTombstone(executionId)

    if execution is not None:
        status = "Success"
        preRun = execution.PreRunner.RetrieveLogInfo().Serialize()
        executor = execution.Executor.RetrieveLogInfo().Serialize()
        postRun = execution.PostRunner.RetrieveLogInfo().Serialize()
    else:
        status = "Not Found"
        preRun = executor = postRun = None
    return jsonify({
        "Status": status, "PreRun": preRun, "Executor": executor, "PostRun": postRun
    })


@bp.route('<int:executionId>/peerId')
def peerId(executionId: int):
    execution = executionOrTombstone(executionId)

    return jsonify({
        'RemoteId': execution.RemoteId if execution is not None else None
    })


# Shared implementation with east_west.files
@bp.route('<int:executionId>/results')
def results(executionId: int):
    return handleExecutionResults(executionId)


def handleExecutionResults(executionId: int):
    execution = executionOrTombstone(executionId)
    if execution is not None:
        folder = abspath(Config().ResultsFolder)
        filename = f"{executionId}.zip"
        if isfile(join(folder, filename)):
            return send_from_directory(folder, filename, as_attachment=True)
        else:
            return f"No results for execution {executionId}", 404
    else:
        return f"Execution {executionId} not found", 404


@bp.route('<int:executionId>/descriptor')
def descriptor(executionId: int):
    execution = executionOrTombstone(executionId)

    if execution is not None:
        return jsonify(execution.JsonDescriptor)
    else:
        return f"Execution {executionId} not found", 404


@bp.route('<int:executionId>/kpis')
def kpis(executionId: int):
    execution = executionOrTombstone(executionId)

    if execution is not None:
        kpis = set()
        descriptor = ExperimentDescriptor(execution.JsonDescriptor)
        for testcase in descriptor.TestCases:
            kpis.update(Facility.GetTestCaseKPIs(testcase))

        res = []
        for kpi in sorted(kpis):
            measurement, name, kind, description = kpi
            res.append({
                'Measurement': measurement, 'KPI': name, 'Type': kind, 'Description': description
            })

        return jsonify({"KPIs": res})
    else:
        return f"Execution {executionId} not found", 404


@bp.route('nextExecutionId')
def nextExecutionId():
    return jsonify({'NextId': Status.PeekNextId()})
