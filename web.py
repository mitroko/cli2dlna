#!/usr/bin/env python2
from time import asctime
import BaseHTTPServer
from urllib import unquote
from subprocess import call
from re import match

HOST_NAME = '0.0.0.0'
PORT_NUMBER = 5600
ytl_re = 'http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?[\w\?=]*)?'

class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        s.wfile.write("<html><head><title>Simple nc cli2dlna UI</title></head>")
        s.wfile.write("<body><form action=/play method=GET><input type=text id=ytu name=ytu><input type=submit value=Play></form>")
        s.wfile.write("Enter youtube URL to play")
        if len(s.path) > 10 and s.path[0:10] == '/play?ytu=':
            url = unquote(s.path[10:])
            if match(ytl_re, url):
                s.wfile.write("<br>Accepted URL: %s" % url)
                call([
                         "/storage/.kodi/addons/service.system.docker/bin/docker",
                         "run",
                         "--rm",
                         "--name",
                         "cli2dlna",
                         "-v",
                         "/storage/.cache/cli2dlna/renderer.cache:/renderer.cache",
                         "mitroko/cli2dlna",
                         "-yv",
                         url
                     ])
        s.wfile.write("</body></html>")

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), HTTPHandler)
    print asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER)
