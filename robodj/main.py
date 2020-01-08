#!/usr/bin/python3

import flask

from . import client

bp = flask.Blueprint("main", __name__)

@bp.route("/")
def index():
  return flask.render_template("index.html")

@bp.route("/status")
def status():
  with client.Client() as flask.g.client:
    context = {
      "current_track": flask.g.client.get_current_track(),
      "queue_length": flask.g.client.get_queue_length()
    }
    return flask.render_template("status.html", **context)

@bp.route("/search")
def search():
  with client.Client() as flask.g.client:
    query = flask.request.args.get("query", "")
    page = int(flask.request.args.get("page", ""))
    context = {
      "query": query,
      "page": page,
      "results": flask.g.client.search(query, page)
    }
    return flask.render_template("search.html", **context)

@bp.route("/request")
def request():
  with client.Client() as flask.g.client:
    track_id = flask.request.args.get("track_id", "")
    if flask.g.client.request_track(track_id):
      return "Písnička bude zahrána"
    else:
      return "Písnička je již ve frontě"
