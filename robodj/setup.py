#!/usr/bin/python3

import flask

from . import client

bp = flask.Blueprint("setup", __name__, url_prefix = "/setup")

@bp.route("/")
def index():
  with client.Client() as flask.g.client:
    context = {
      "devices": flask.g.client.get_devices(),
      "playlists": flask.g.client.get_playlists()
    }
    return flask.render_template("setup.html", **context)

@bp.route("/auth")
def auth():
  with client.Client() as flask.g.client:
    code = flask.request.args.get("code", "")
    error = flask.request.args.get("error", "")
    if code:
      flask.g.client.login(code, flask.url_for(".auth", _external = True))
      return flask.redirect(flask.url_for(".index"))
    if error:
      return flask.redirect(flask.url_for(".index", error = error))
    return flask.redirect(flask.g.client.oauth2_url(flask.url_for(".auth", _external = True)))

@bp.route("/set_device", methods=["POST"])
def set_device():
  with client.Client() as flask.g.client:
    device_id = flask.request.form["device_id"]
    flask.g.client.select_device(device_id)
    return flask.redirect(flask.url_for(".index"))

@bp.route("/set_playlist", methods=["POST"])
def set_playlist():
  with client.Client() as flask.g.client:
    playlist_id = flask.request.form["playlist_id"]
    skip_tracks = int(flask.request.form["skip_tracks"])
    flask.g.client.load_playlist(playlist_id, skip_tracks)
    return flask.redirect(flask.url_for(".index"))

@bp.route("/restart", methods=["POST"])
def restart():
  with client.Client() as flask.g.client:
    flask.g.client.exit()
    return flask.redirect(flask.url_for(".index"))

@bp.route("/kill", methods=["POST"])
def kill():
  with client.Client() as flask.g.client:
    flask.g.client.kill_track()
    return flask.redirect(flask.url_for(".index"))
