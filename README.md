# spotify-robodj
RoboDJ is a web based application which uses Spotify to act like a jukebox at a party. It plays predefined playlist while anybody can search any song at Spotify and add it to request queue. Songs in the queue are played as soon as previous song is finished. When the queue is empty other songs from the playlist are played. User interface is simplistic. It only shows current song, length of request queue, search input and search results with a button for adding found song to the queue.

## Disclaimer
RoboDJ requires Spotify Premium to work. RoboDJ should be used only on private parties. Always use RoboDJ in such way which do not violate [Spotify Terms and Conditions of Use](https://www.spotify.com/us/legal/end-user-agreement/).

## Application design
The application consists of two components. The first one is a web application based on [Flask](https://www.palletsprojects.com/p/flask/) which handles user requests and HTML rendering. This component proxies all requests through [RPyC](https://rpyc.readthedocs.io/en/latest/) to underlying service. The second component is a service which accepts user requests through [RPyC](https://rpyc.readthedocs.io/en/latest/) and communicates with [Spotify Web API](https://developer.spotify.com/documentation/web-api/). This component manages the playlist and the queue and choose what to play each time Spotify finishes current song. This service also handles authentication against Spotify OAuth and searching through Spotify database. The application itself is not capable of playin sound. It requires standalone player which is controlled through [Spotify Web API](https://developer.spotify.com/documentation/web-api/). This can be [Spotify Web Player](https://open.spotify.com/), [Spotify Desktop Player](https://www.spotify.com/us/download/other/) or [librespot](https://github.com/librespot-org/librespot) if a headless software is required.

## Registering application
Application must be registered in order to use [Spotify Web API](https://developer.spotify.com/documentation/web-api/). Visit https://developer.spotify.com/dashboard/applications, login using your Spotify account and click **CREATE A CLIENT ID** button. Choose some name and description. As a redirect URI fill your intended RoboDJ base URL extended by **/setup/auth**. For example if your RoboDJ instance run at https://mydomain.org/robodj/ use https://mydomain.org/robodj/setup/auth as redirect URI.

## Deplyment
RoboDJ is designed to be run as a microservice inside a Docker container behind [NGINX](https://www.nginx.com/) reverse proxy.
- Build image using provided Dockerfile.

```
docker build -t robodj .
```

- Create container and start it in background.

   **SCRIPT_NAME** is base path excluding domain used by flask for link generation. **CLIENT_ID** and **CLIENT_SECRET** are values obtained from application registration.

```
docker run -d -e 'SCRIPT_NAME=/robodj/' -e 'CLIENT_ID=xxx' -e 'CLIENT_SECRET=xxx' --restart always --name robodj robodj
```

- Setup [NGINX](https://www.nginx.com/) to proxy requests to RoboDJ.

   **Host** header must be forwarded. **X-Forwarded-Proto** header must be set if HTTPS scheme is used. The simplest possible configuration snippet is:

```
location /robodj/ {
    proxy_pass http://172.17.0.2:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Initial setup
All setup is done at single page at address **/setup** relative to the application root. Although the application is registered it is not automatically associated with Spotify user account. It is necessary to login the application to your account using OAuth using button at this page. The player to be used has to be selected. Player has to be running and connected to same user account in order to show up in the list. When playlist is selected application will wait to current song to finish and start playing it.

## Additional features
If you do not like song currently playing you can kill it by button at setup page. When the button is pressed 9 seconds long refrain of [Kill the DJ](https://open.spotify.com/track/6pwt5G9ZKwM6I0GKVfIBb4) is played followed by next song from the queue or playlist. This action can be also triggered by any application or device by sending HTTTP POST request to URL **/setup/kill** relative to RoboDJ base URL.

## Further reading
- https://developer.spotify.com/documentation/general/guides/app-settings/
- https://developer.spotify.com/documentation/web-api/reference/
