#!/usr/bin/python3

import flask
import os

from . import babel
from . import main
from . import setup

class ReverseProxied:

  def __init__(self, app, script_name):
    self.app = app
    self.script_name = script_name

  def __call__(self, environ, start_response):
    environ["SCRIPT_NAME"] = self.script_name
    environ["wsgi.url_scheme"] = environ.get("HTTP_X_FORWARDED_PROTO")
    return self.app(environ, start_response)

def create_app():
  app = flask.Flask(__name__)
  babel.babel.init_app(app)
  app.register_blueprint(main.bp)
  app.register_blueprint(setup.bp)
  app.wsgi_app = ReverseProxied(app.wsgi_app, os.environ["SCRIPT_NAME"])
  return app
