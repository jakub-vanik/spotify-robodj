#!/usr/bin/python3

import flask
import flask_babel

babel = flask_babel.Babel()

@babel.localeselector
def get_locale():
  return flask.request.accept_languages.best_match(["en", "cs"])

@babel.timezoneselector
def get_timezone():
  return None
