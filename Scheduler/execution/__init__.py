from flask import Blueprint

bp = Blueprint('execution', __name__)

from Scheduler.execution import routes