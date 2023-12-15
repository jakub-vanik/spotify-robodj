#!/usr/bin/python3

import flask
import flask_babel
import werkzeug.middleware.proxy_fix

from . import main
from . import setup

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)
flask_babel.Babel(app, locale_selector=lambda: flask.request.accept_languages.best_match(["en", "cs"]))
app.register_blueprint(main.bp)
app.register_blueprint(setup.bp)
