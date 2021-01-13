#!/usr/bin/env python
# Plays MPV when instructed to by a chrome extension =]

import sys
from subprocess import Popen
from shutil import which

PORT = 7531
# Use --public if you want the server and extension on different computers
hostname = 'localhost'
if '--public' in sys.argv:
    hostname = '0.0.0.0'

if sys.version_info[0] < 3:  # python 2
    import BaseHTTPServer
    import urlparse

    class CompatibilityMixin:
        def send_body(self, msg):
            self.wfile.write(msg+'\n')
            self.wfile.close()

else:  # python 3
    import http.server as BaseHTTPServer
    import urllib.parse as urlparse

    class CompatibilityMixin:
        def send_body(self, msg):
            self.wfile.write(bytes(msg+'\n', 'utf-8'))


class Handler(BaseHTTPServer.BaseHTTPRequestHandler, CompatibilityMixin):
    def respond(self, code, body=None):
        self.send_response(code)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        if body:
            self.send_body(body)

    def play_with_mpv(self, query):
        if "list" in query:
            list_url = 'https://www.youtube.com/playlist?list={}'.format(
                query["list"][0])

            ytdl_format = ''
            if query["mpv_args"] is not None:
                ytdl_format = '--ytdl-format={}'.format(query["mpv_args"][0])

            return Popen([mpv_command, list_url, '--force-window'] +
                         query.get("mpv_args", []))
        else:
            mpv_options = ''
            return Popen([mpv_command, urls, '--force-window'] +
                         query.get("mpv_args", []))

    def play_with_celluloid(self, query):
        if which('celluloid') is not None:
            # Playlist support
            if "list" in query:
                urls += str("&list={}".format(query["list"][0]))
            mpv_command = 'celluloid'
            mpv_options = []

            # Translate mpv options to celluloid
            for mpv_arg in query["mpv_args"]:
                if '--ytdl-format' in mpv_arg:
                    mpv_options.append(mpv_arg.replace(
                        '--ytdl-format=', '--mpv-ytdl-format="') + '"')
                else:
                    mpv_options.append(mpv_arg)

            return Popen([mpv_command, urls] + mpv_options)

    def do_GET(self):
        try:
            url = urlparse.urlparse(self.path)
            query = urlparse.parse_qs(url.query)
        except:
            query = {}
        if query.get('mpv_args'):
            print("MPV ARGS:", query.get('mpv_args'))
            mpv_command = 'mpv'
            if('mpv_player' in query):
                mpv_command = query['mpv_player'][0]
        if "play_url" in query:
            urls = str(query["play_url"][0])
            if urls.startswith('magnet:') or urls.endswith('.torrent'):
                pipe = Popen(['peerflix', '-k',  urls, '--', '--force-window'] +
                             query.get("mpv_args", []))
            else:
                if mpv_command == 'mpv':
                    pipe = self.play_with_mpv(query)
                elif mpv_command == 'celluloid':
                    pipe = self.play_with_celluloid(query)                   
                    
            self.respond(200, "playing...")
        elif "cast_url" in query:
            urls = str(query["cast_url"][0])
            if urls.startswith('magnet:') or urls.endswith('.torrent'):
                print(" === WARNING: Casting torrents not yet fully supported!")
                with Popen(['mkchromecast', '--video',
                            '--source-url', 'http://localhost:8888']):
                    pass
                pipe.terminate()
            else:
                pipe = Popen(['mkchromecast', '--video', '-y', urls])
            self.respond(200, "casting...")

        elif "fairuse_url" in query:
            urls = str(query["fairuse_url"][0])
            location = query.get("location", ['~/Downloads/'])[0]
            if "%" not in location:
                location += "%(title)s.%(ext)s"
            print("downloading ", urls, "to", location)
            if urls.startswith('magnet:') or urls.endswith('.torrent'):
                msg = " === ERROR: Downloading torrents not yet supported!"
                print(msg)
                self.respond(400, msg)
            else:
                pipe = Popen(['youtube-dl', urls, '-o', location] +
                             query.get('ytdl_args', []))
                self.respond(200, "downloading...")
        else:
            self.respond(400)


def start():
    httpd = BaseHTTPServer.HTTPServer((hostname, PORT), Handler)
    print("serving on {}:{}".format(hostname, PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(" shutting down...")
        httpd.shutdown()


if __name__ == '__main__':
    start()
