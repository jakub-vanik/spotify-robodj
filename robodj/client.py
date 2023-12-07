#!/usr/bin/python3

import os
import rpyc
import time

class Client:

  def __init__(self):
    self.connection = self.connect()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.connection.close()
    self.connection = None

  def connect(self):
    for i in range(0, 5):
      try:
        return rpyc.connect("localhost", 18861)
      except ConnectionRefusedError:
        if i == 0:
          connection = rpyc.classic.connect("localhost")
          connection.modules.os.chdir(os.environ["FLASK_APP"])
          connection.modules.os.system("./service.py &")
        time.sleep(2)
    raise Exception("Unable to connect to the service")

  def oauth2_url(self, redirect_uri):
    return self.connection.root.oauth2_url(redirect_uri)

  def login(self, code, redirect_uri):
    return self.connection.root.login(code, redirect_uri)

  def get_devices(self):
    return self.connection.root.get_devices()

  def select_device(self, device_id):
    return self.connection.root.select_device(device_id)

  def get_playlists(self):
    return self.connection.root.get_playlists()

  def load_playlist(self, palylist_id, skip_tracks):
    return self.connection.root.load_playlist(palylist_id, skip_tracks)

  def get_current_track(self):
    return self.connection.root.get_current_track()

  def get_queue_length(self):
    return self.connection.root.get_queue_length()

  def search(self, query, page):
    return self.connection.root.search(query, page)

  def request_track(self, track_id):
    return self.connection.root.request_track(track_id)

  def kill_track(self):
    return self.connection.root.kill_track()

  def exit(self):
    return self.connection.root.exit()
