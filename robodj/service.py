#!/usr/bin/python3

import aiohttp
import asyncio
import base64
import copy
import json
import os
import queue
import rpyc
import shelve
import threading
import time
import traceback
import urllib.parse

class PriorityEntry:

  def __init__(self, priority, data):
    self.priority = priority
    self.data = data

  def __lt__(self, other):
    return self.priority < other.priority

class Spotify:

  def __init__(self, client_id, client_secret, storage_path):
    self.client_id = client_id
    self.client_secret = client_secret
    self.storage_path = storage_path
    self.access_token = None
    self.refresh_token = None
    self.device_id = ""
    self.playlist = set()
    self.current_track = None
    self.queued_tracks = set()
    self.refresh_task = None
    self.play_next_task = None
    self.loop = asyncio.new_event_loop()
    self.queue = asyncio.PriorityQueue(loop = self.loop)
    self.thread = threading.Thread(target = self.entry_point)
    self.thread.start()
    asyncio.run_coroutine_threadsafe(self.start_async(), self.loop).result()

  def oauth2_url(self, redirect_uri):
    params = {
      "response_type": "code",
      "client_id": self.client_id,
      "scope": "user-read-playback-state user-read-currently-playing user-modify-playback-state playlist-read-private playlist-read-collaborative",
      "redirect_uri": redirect_uri
    }
    return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

  def login(self, code, redirect_uri):
    return asyncio.run_coroutine_threadsafe(self.login_async(code, redirect_uri), self.loop).result(10)

  def get_devices(self):
    return asyncio.run_coroutine_threadsafe(self.get_devices_async(), self.loop).result(10)

  def select_device(self, device_id):
    return asyncio.run_coroutine_threadsafe(self.select_device_async(device_id), self.loop).result(10)

  def get_playlists(self):
    return asyncio.run_coroutine_threadsafe(self.get_playlists_async(), self.loop).result(10)

  def load_playlist(self, palylist_id, skip_tracks):
    return asyncio.run_coroutine_threadsafe(self.load_playlist_async(palylist_id, skip_tracks), self.loop).result(10)

  def get_current_track(self):
    return asyncio.run_coroutine_threadsafe(self.get_current_track_async(), self.loop).result(10)

  def get_queue_length(self):
    return asyncio.run_coroutine_threadsafe(self.get_queue_length_async(), self.loop).result(10)

  def search(self, query, page):
    return asyncio.run_coroutine_threadsafe(self.search_async(query, page), self.loop).result(10)

  def request_track(self, track_id):
    return asyncio.run_coroutine_threadsafe(self.request_track_async(track_id), self.loop).result(10)

  def kill_track(self):
    return asyncio.run_coroutine_threadsafe(self.kill_track_async(), self.loop).result(10)

  def close(self):
    return asyncio.run_coroutine_threadsafe(self.close_async(), self.loop).result(10)

  def entry_point(self):
    asyncio.set_event_loop(self.loop)
    try:
      self.loop.run_forever()
    finally:
      self.loop.close()

  async def start_async(self):
    with shelve.open(self.storage_path) as storage:
      if "device_id" in storage:
        self.device_id = storage["device_id"]
      if "refresh_token" in storage:
        self.refresh_token = storage["refresh_token"]
      if "playlist" in storage:
        self.playlist = set(storage["playlist"])
        for entry in self.playlist:
          if entry.priority[0] == 0:
            self.queued_tracks.add(entry.data["id"])
          await self.queue.put(entry)
      if await self.refresh_async(0):
        await self.play_first_async()

  async def login_async(self, code, redirect_uri):
    params = {
      "grant_type": "authorization_code",
      "code": code,
      "redirect_uri": redirect_uri
    }
    response = await self.oauth2_async(params)
    if "access_token" in response and "refresh_token" in response and "expires_in" in response:
      self.access_token = response["access_token"]
      self.refresh_token = response["refresh_token"]
      if self.refresh_task:
        self.refresh_task.cancel()
      self.refresh_task = self.loop.create_task(self.refresh_async(response["expires_in"] - 5))
      self.refresh_task.add_done_callback(Spotify.done_callback)
      await self.play_first_async()
      await self.save_async()
      return True
    return False

  async def get_devices_async(self):
    response = await self.api_get_async("https://api.spotify.com/v1/me/player/devices")
    if response:
      return response["devices"]
    return []

  async def select_device_async(self, device_id):
    self.device_id = device_id
    query_params = {}
    body_params = {
      "device_ids": [self.device_id]
    }
    await self.api_put_async("https://api.spotify.com/v1/me/player", query_params, body_params)
    await self.save_async()

  async def get_playlists_async(self):
    result = []
    offset = 0
    repeat = True
    while repeat:
      params = {
        "offset": offset
      }
      response = await self.api_get_async("https://api.spotify.com/v1/me/playlists", params)
      if response:
        result.extend(response["items"])
        offset += response["limit"]
        if not response["next"]:
          repeat = False
      else:
        repeat = False
    return result

  async def load_playlist_async(self, playlist_id, skip_tracks):
    while not self.queue.empty():
      entry = await self.queue.get()
      self.playlist.remove(entry)
      track = entry.data
      self.queued_tracks.discard(track["id"])
    timestamp = int(time.time())
    serial = 0
    offset = skip_tracks
    repeat = True
    while repeat:
      params = {
        "offset": offset
      }
      response = await self.api_get_async("https://api.spotify.com/v1/playlists/%s/tracks" % (playlist_id, ), params)
      if response:
        for item in response["items"]:
          entry = PriorityEntry((1, timestamp, serial), item["track"])
          self.playlist.add(entry)
          await self.queue.put(entry)
          serial += 1
        offset += response["limit"]
        if not response["next"]:
          repeat = False
      else:
        repeat = False
    await self.save_async()

  async def get_current_track_async(self):
    return self.current_track

  async def get_queue_length_async(self):
    return len(self.queued_tracks)

  async def search_async(self, query, page):
    params = {
      "q": query,
      "type": "track",
      "available_markets": "CZ",
      "limit": 10,
      "offset": page * 10
    }
    for _ in range(2):
      response = await self.api_get_async("https://api.spotify.com/v1/search", params)
      if response and "tracks" in response:
        return response["tracks"]["items"]
      await asyncio.sleep(1)
    return []

  async def request_track_async(self, track_id):
    if not track_id in self.queued_tracks:
      self.queued_tracks.add(track_id)
      response = await self.api_get_async("https://api.spotify.com/v1/tracks/%s" % (track_id, ))
      if response:
        timestamp = int(time.time())
        entry = PriorityEntry((0, timestamp, 0), response)
        self.playlist.add(entry)
        await self.queue.put(entry)
      else:
        self.queued_tracks.discard(track_id)
      return True
    else:
      return False

  async def kill_track_async(self):
    if self.play_next_task:
      self.play_next_task.cancel()
    query_params = {
      "device_id": self.device_id
    }
    body_params = {
      "uris": ["spotify:track:6pwt5G9ZKwM6I0GKVfIBb4"],
      "position_ms": 40700
    }
    await self.api_put_async("https://api.spotify.com/v1/me/player/play", query_params, body_params)
    self.play_next_task = self.loop.create_task(self.play_next_async(9))
    self.play_next_task.add_done_callback(Spotify.done_callback)

  async def close_async(self):
    if self.refresh_task:
      self.refresh_task.cancel()
    if self.play_next_task:
      self.play_next_task.cancel()
    await self.save_async()
    self.loop.call_soon_threadsafe(self.loop.stop)

  async def refresh_async(self, wait):
    await asyncio.sleep(wait)
    if self.refresh_token:
      params = {
        "grant_type": "refresh_token",
        "refresh_token": self.refresh_token
      }
      response = await self.oauth2_async(params)
      if response:
        if "access_token" in response and "expires_in" in response:
          self.access_token = response["access_token"]
          self.refresh_task = self.loop.create_task(self.refresh_async(response["expires_in"] - 5))
          self.refresh_task.add_done_callback(Spotify.done_callback)
          return True
        else:
          self.access_token = None
          self.refresh_token = None
          self.refresh_task = None
          await self.save_async()
      else:
        self.refresh_task = self.loop.create_task(self.refresh_async(1))
        self.refresh_task.add_done_callback(Spotify.done_callback)
    return False

  async def play_first_async(self):
    wait_time = 0
    response = await self.api_get_async("https://api.spotify.com/v1/me/player")
    if response and response["is_playing"]:
      self.current_track = response["item"]
      wait_time = (response["item"]["duration_ms"] - response["progress_ms"]) / 1000
    if self.play_next_task:
      self.play_next_task.cancel()
    self.play_next_task = self.loop.create_task(self.play_next_async(wait_time))
    self.play_next_task.add_done_callback(Spotify.done_callback)

  async def play_next_async(self, wait):
    await asyncio.sleep(wait)
    entry = await self.queue.get()
    self.playlist.remove(entry)
    track = entry.data
    self.queued_tracks.discard(track["id"])
    query_params = {
      "device_id": self.device_id
    }
    body_params = {
      "uris": [track["uri"]]
    }
    await self.api_put_async("https://api.spotify.com/v1/me/player/play", query_params, body_params)
    self.current_track = track
    wait_time = track["duration_ms"] / 1000
    self.play_next_task = self.loop.create_task(self.play_next_async(wait_time))
    self.play_next_task.add_done_callback(Spotify.done_callback)
    await self.save_async()

  async def oauth2_async(self, params):
    data = urllib.parse.urlencode(params).encode()
    headers = {
      "Content-Type": "application/x-www-form-urlencoded",
      "Authorization": "Basic " + Spotify.base64_encode(self.client_id + ":" + self.client_secret)
    }
    try:
      async with aiohttp.ClientSession() as session:
        async with session.post("https://accounts.spotify.com/api/token", data = data, headers = headers) as response:
          return await response.json()
    except:
      traceback.print_exc()
    return None

  async def api_get_async(self, url, params = {}):
    if self.access_token:
      data = urllib.parse.urlencode(params)
      print("GET " + url + "?" + data)
      headers = {
        "Authorization": "Bearer " + self.access_token
      }
      try:
        async with aiohttp.ClientSession() as session:
          async with session.get(url + "?" + data, headers = headers) as response:
            return await response.json()
      except:
        traceback.print_exc()
    return None

  async def api_post_async(self, url, params = {}):
    if self.access_token:
      data = json.dumps(params)
      print("POST " + url + " " + data)
      headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + self.access_token
      }
      try:
        async with aiohttp.ClientSession() as session:
          async with session.post(url, data = data, headers = headers) as response:
            return await response.json()
      except:
        traceback.print_exc()
    return None

  async def api_put_async(self, url, query_params = {}, body_params = {}):
    if self.access_token:
      query_data = urllib.parse.urlencode(query_params)
      body_data = json.dumps(body_params)
      print("PUT " + url + "?" + query_data + " " + body_data)
      headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + self.access_token
      }
      try:
        async with aiohttp.ClientSession() as session:
          async with session.put(url + "?" + query_data, data = body_data, headers = headers) as response:
            if response.status == 204:
              return True
      except:
        traceback.print_exc()
    return False

  async def save_async(self):
    with shelve.open(self.storage_path) as storage:
      storage["device_id"] = self.device_id
      storage["refresh_token"] = self.refresh_token
      storage["playlist"] = list(self.playlist)

  @staticmethod
  def done_callback(future):
    try:
      future.result()
    except asyncio.CancelledError:
      pass
    except:
      traceback.print_exc()

  @staticmethod
  def base64_encode(text):
    return base64.b64encode(text.encode()).decode()

class SpotifyService(rpyc.Service):

  def __init__(self, server):
    self.server = server
    self.exiting = False

  def on_connect(self, conn):
    pass

  def on_disconnect(self, conn):
    if self.exiting:
      self.server.exit()

  def exposed_oauth2_url(self, redirect_uri):
    return self.server.spotify.oauth2_url(copy.copy(redirect_uri))

  def exposed_login(self, code, redirect_uri):
    return self.server.spotify.login(copy.copy(code), copy.copy(redirect_uri))

  def exposed_get_devices(self):
    return self.server.spotify.get_devices()

  def exposed_select_device(self, device_id):
    return self.server.spotify.select_device(copy.copy(device_id))

  def exposed_get_playlists(self):
    return self.server.spotify.get_playlists()

  def exposed_load_playlist(self, palylist_id, skip_tracks):
    return self.server.spotify.load_playlist(copy.copy(palylist_id), copy.copy(skip_tracks))

  def exposed_get_current_track(self):
    return self.server.spotify.get_current_track()

  def exposed_get_queue_length(self):
    return self.server.spotify.get_queue_length()

  def exposed_search(self, query, page):
    return self.server.spotify.search(copy.copy(query), copy.copy(page))

  def exposed_request_track(self, track_id):
    return self.server.spotify.request_track(copy.copy(track_id))

  def exposed_kill_track(self):
    return self.server.spotify.kill_track()

  def exposed_exit(self):
    self.exiting = True

class Server:

  def __init__(self):
    self.spotify = Spotify(os.environ["CLIENT_ID"], os.environ["CLIENT_SECRET"], os.environ["STORAGE_PATH"])
    self.service = rpyc.utils.helpers.classpartial(SpotifyService, self)

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self.spotify.close()

  def start(self):
    self.server = rpyc.utils.server.ThreadedServer(self.service, port = 18861)
    self.server.start()

  def exit(self):
    self.server.close()

def main():
  with Server() as server:
    server.start()

if __name__ == "__main__":
  main()
