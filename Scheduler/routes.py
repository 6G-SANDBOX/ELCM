from Scheduler import app
from Status import Status, ExecutionQueue
from Experiment import Tombstone
from flask import render_template, make_response, request, flash, redirect, url_for
from functools import wraps, update_wrapper
from datetime import datetime
from Helper import Log, Serialize, LogInfo
from Settings import Config, EvolvedConfig
from Facility import Facility
from typing import List, Dict
from flask_paginate import Pagination, get_page_parameter


# https://arusahni.net/blog/2014/03/flask-nocache.html
def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return update_wrapper(no_cache, view)


@app.route("/")
@nocache
def index():
    config = Config()
    evolved = EvolvedConfig()
    configLog = LogInfo.FromTuple(config.Validation)
    evolvedLog = LogInfo.FromTuple(evolved.Validation)
    facilityLog = LogInfo.FromTuple(Facility.Validation)
    resources = Facility.Resources()
    return render_template('index.html', executionId=Status.PeekNextId(),
                           executions=ExecutionQueue.Retrieve(), resources=resources,
                           configLog=configLog, evolvedLog=evolvedLog, facilityLog=facilityLog)


@app.route("/log")
def log():
    return render_template('mainLog.html', logInfo=Log.RetrieveLogInfo(tail=100))


@app.route("/history")
def history():
    ids = Serialize.List(False, False, 'Execution')
    ids.sort(key=int, reverse=True)
    page = request.args.get(get_page_parameter(), type=int, default=1)
    pagination = Pagination(page=page, total=len(ids), search=False,
                            record_name='executions', per_page=10, bs_version=4,
                            display_msg='Displaying <b>{start} - {end}</b> {record_name} (out of <b>{total}</b>)')
    start = pagination.skip
    end = start + pagination.per_page
    ids = ids[start:end]
    executions: List[Tombstone] = []
    for id in ids:
        digest = Tombstone(id)
        executions.append(digest)

    return render_template('history.html', executions=executions, pagination=pagination)


@app.route("/reload_config")
def reloadConfig():
    try:
        configurations = [('Configuration', Config(forceReload=True)),
                          ('Evolved5g Configuration', EvolvedConfig(forceReload=True))]

        for name, config in configurations:
            Log.I(f"{name} reloaded:")
            for level, message in config.Validation:
                Log.Log(level, message)

        flash("Reloaded all configurations", "info")
    except Exception as e:
        flash(f"Exception while reloading configurations: {e}", "error")
    finally:
        return redirect(url_for('index'))


@app.route("/reload_facility")
def reloadFacility():
    try:
        Facility.Reload()
        Log.I("Facility reloaded:")
        for level, message in Facility.Validation:
            Log.Log(level, message)
        flash("Reloaded Facility", "info")
    except Exception as e:
        flash(f"Exception while reloading facility: {e}", "error")
    finally:
        return redirect(url_for('index'))
