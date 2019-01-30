from flask import redirect, url_for, flash, render_template
from Status import Status, ExperimentQueue
from Executor import ExecutorStatus
from Scheduler.executor import bp


@bp.route('/start')
def start():
    executorId, executor = Status.CreateExecutor()
    executor.Start()
    flash(f'Created executor {executorId}', 'info')
    return redirect(url_for('index'))


@bp.route('<int:executorId>/cancel')
def cancel(executorId: int):
    Status.CancelExecutor(executorId)
    flash(f'Cancelled executor {executorId}', 'info')
    return redirect(url_for('index'))


@bp.route('<int:executorId>/delete')
def delete(executorId: int):
    try:
        executor = ExperimentQueue.Find(executorId)
        if executor.Status != ExecutorStatus.Running:
            Status.DeleteExecutor(executorId)
            flash(f'Deleted executor {executorId}', 'info')
        else:
            flash(f'Cannot remove {executorId}', 'danger')
    except Exception as e:
        flash(f'Exception while deleting executor {executorId}', 'danger')

    return redirect(url_for('index'))


@bp.route('<int:executorId>')
def view(executorId:int):
    executor = ExperimentQueue.Find(executorId)
    if executor is None:
        flash(f'Executor {executorId} does not exist or is not within Scheduler context', 'danger')
        return redirect(url_for('index'))
    return render_template('executor.html', executor=executor)
