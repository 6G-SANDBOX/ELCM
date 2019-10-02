from flask import Flask
from Helper import Log
from Status import Status
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from Helper import Config
from Facility import Facility
from .heartbeat import HeartBeat
import os

config = Config()
print("Config validation:")
for level, message in config.Validation:
    print(f"  {level.name:8}: {message}")

Facility.Reload()
print("Facility validation:")
for level, message in Facility.Validation:
    print(f"  {level.name:8}: {message}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

bootstrap = Bootstrap(app)
moment = Moment(app)
Log.Initialize(app)
Status.Initialize()
HeartBeat.Initialize()

from Scheduler.execution import bp as ExecutionBp
app.register_blueprint(ExecutionBp, url_prefix='/execution')

from Scheduler.dispatcher import bp as DispatcherBp
app.register_blueprint(DispatcherBp, url_prefix='/api/v0')

from Scheduler import routes
