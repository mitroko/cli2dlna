#!/usr/bin/env python
#
#    Description : Command line tool to play media on remote renderers.
#    Author      : Dmitriy Stremkovskiy <mitroko@gmail.com>.
#    Copyright   : 2016, Dmitriy Stremkovskiy.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import array                             # used during ip calculations
import fcntl                             # used during ip calculations
import httplib                           # used to get location from fake socket
import os                                # used to get os environment
import re                                # used to filterout upnp address from ssdp responce
import socket                            # used to implement socket funcions
import struct                            # used during ip calculations
import sys                               # used to get argv
import subprocess                        # used to call youtube-dl
import urllib2                           # used to send xml packets
import urlparse                          # used to split/parse ssdp responce into
from StringIO import StringIO as fake_io # used for fake socket

class SsdpFakeSocket(fake_io):
  def makefile(self, *args, **kw): return self

def print_finish(happy):
  print
  if happy:
    print ' [:)] Finished.'
    print
    sys.exit(0)
  else:
    print ' [:(] Finished.'
    print
    sys.exit(1)

# https://gist.github.com/pklaus/289646 code
def format_ip(addr):
  return str(ord(addr[0])) + '.' + \
    str(ord(addr[1])) + '.' + \
    str(ord(addr[2])) + '.' + \
    str(ord(addr[3]))

# https://gist.github.com/pklaus/289646 improved code
def all_interfaces(max_possible):
   bytes = max_possible * 32
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   names = array.array('B', '\0' * bytes)
   outbytes = struct.unpack('iL', fcntl.ioctl(
     s.fileno(),
     0x8912,  # SIOCGIFCONF
     struct.pack('iL', bytes, names.buffer_info()[0])
   ))[0]
   namestr = names.tostring()
   ips = []
   ifaces = []
   for i in range(0, outbytes, 40):
     ips.append(format_ip(namestr[i+20:i+24]))
     ifaces.append(namestr[i:i+16].split('\0', 1)[0])
   return ifaces, ips

def get_router(ip, port):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.connect((ip, port))
  router = s.getsockname()[0]
  s.close()
  return router

# array members deduplication
def uniq_array(seq):
  seen = set()
  seen_add = seen.add
  return [x for x in seq if not (x in seen or seen_add(x))]

def get_headers(action, clength):
  return {
    'Accept': '*/*',
    'Content-Type': 'text/xml;charset=utf-8',
    'Content-Length': clength,
    'Connection': 'Keep-Alive',
    'Soapaction': sth + ':1#' + action + '"'
  }

# SSDP discovery improved code
def ssdp_discover(service, bind_ip, res):
  group = ('239.255.255.250', 1900)
  message = "\r\n".join(['M-SEARCH * HTTP/1.1', 'HOST: {0}:{1}', 'MAN: "ssdp:discover"', 'ST: {st}','MX: 3','',''])
  socket.setdefaulttimeout(1)
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
  sock.bind((bind_ip, 1900))
  sock.sendto(message.format(*group, st=service), group)
  while True:
    try:
      r = httplib.HTTPResponse(SsdpFakeSocket(sock.recv(1024)))
      r.begin()
      res.append(r.getheader('location'))
    except socket.timeout:
      break

def ssdp_lookup_main(results):
  print ' [**] Dropping into SSDP discovery. Please wait'
  ifaces, ips = all_interfaces(16)
  for ip in ips:
    ssdp_discover('urn:schemas-upnp-org:service:AVTransport:1', ip, results)
  results = uniq_array(results)
  
  if len(results) < 1:
    print ' [:(] No UPnP answered. Try again in one minute.'
    print_finish(False)
  
  print ' [:)] Got non empty reply'
  print ' ----------------------------------------------'
  print

def get_header():
  print
  print ' ---[=                         :: cli2dlna.py ::                         =]--- '
  print ''
  print ' [!] This is a PoC code. It does not support multiple UPnP renderers :('
  print

def get_renderer_from_config(rfile):
  try:
    r = open(rfile, 'r')
    renderer = r.read()
    r.close()
  except:
    renderer = ''
  if not renderer == '':
    print ' [:)] Using cached renderer: %s' % renderer
  return renderer

def cache_renderer(rfile, result):
  try:
    r = open(rfile, 'w')
    r.write(result)
    r.close()
  except:
    pass

def get_renderer_control(result):
  try:
    data = urllib2.urlopen(result).read()
    expr = re.compile(r'urn:upnp-org:serviceId:AVTransport.*<controlURL>(.*)</controlURL>', re.DOTALL)
    regexresult = expr.findall(data)
    o = urlparse.urlparse(result)
  except:
    print ' [:(] Unable to get/parse renderer control. Unsupported device.'
    print_finish(False)
  return str(o.hostname), o.port, str(regexresult[0])

def renderer_cmd_multi(addr, action, message, is_critical):
  try:
    print ' [**] Sending ' + str(action) + ' message'
    req = urllib2.Request(addr, data=message, headers=get_headers(action, len(message)))
    urllib2.urlopen(req)
  except urllib2.HTTPError, e:
    if is_critical:
      pre = ' [:(] '
    else:
      pre = ' [:|] '
    print pre + 'Got code: %s' % str(e.code)
    print pre + 'Got reason: %s' % str(e.reason)
    print pre + 'Failed to send ' + str(action) + ' message'
    if is_critical:
      print_finish(False)

def return_help():
  me = sys.argv[0]
  print ' [?] Examples, how to run:'
  print ' ]$ ' + me + ' -f /some/file'
  print '     Assuming you have running web server on 80 port that shares your files.'
  print '     Script will notify your UPnP renderer to get media from this server.'
  print
  print ' ]$ ' + me + ' -u http://...'
  print '     Script will notify your UPnP renderer to get media from this url.'
  print ' ]$ ' + me + ' -y ...'
  print '     Script will call youtube-dl to process your request.'
  print '     [!] - YOUTUBE_DL environment variable should be set'
  print '     [!]   or default of /usr/local/bin/youtube-dl will be used'
  print '     youtube-dl will be executed as subprocess with -g key to get http link.'
  print '     Afterthat, this link will be sent to your UPnP renderer.'
  print
  print ' ]$ ' + me + ' -c'
  print '     Perform simple SSDP lookup for remote renderers'
  print
  print ' ]$ ' + me + ' -C'
  print '     continue playing current media'
  print
  print ' ]$ ' + me + ' -P'
  print '     pause current media'
  print
  print ' ]$ ' + me + ' -S'
  print '     stop current media'
  print
  print ' ]$ ' + me + ' -h'
  print '     Print this message :)'
  print
  print ' [!] Script WILL try to save discovered UPnP renderer to renderer.cache to'
  print '     prevent future SSDP lookups. Remove config to manage another renderer.'
  print
  print ' ---[=                           Have fun ;)                             =]--- '
  print
  sys.exit(0)


#
# ---[= Main
#
# :: static
xml_head = '<?xml version="1.0" encoding="utf-8" standalone="yes"?><s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
it = 'xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"><InstanceID>0</InstanceID>'
stop_message = xml_head + '<u:Stop ' + it + '</u:Stop></s:Body></s:Envelope>'
play_message = xml_head + '<u:Play ' + it + '<Speed>1</Speed></u:Play></s:Body></s:Envelope>'
pause_message = xml_head + '<u:Pause ' + it + '<Speed>1</Speed></u:Pause></s:Body></s:Envelope>'
msg_tail = '</CurrentURI><CurrentURIMetaData>21BDbFXIWvF2.128.mp3</CurrentURIMetaData></u:SetAVTransportURI></s:Body></s:Envelope>'
sth = '"urn:schemas-upnp-org:service:AVTransport'
ytd = os.getenv('YOUTUBE_DL', '/usr/local/bin/youtube-dl')
rconf = os.path.dirname(sys.argv[0]) + '/renderer.cache'

# :: greetings
get_header()
if len(sys.argv) < 2:
  return_help()

a1 = sys.argv[1]
if (a1 == '-h') or (a1 == '--help'):
  return_help()

if a1 == '-c':
  results = []
  ssdp_lookup_main(results)
  print ' ' + str(results)
  print_finish(True)

renderer = get_renderer_from_config(rconf)
if renderer == '':
  results = []
  ssdp_lookup_main(results)
  result = results[0]
  cache_renderer(rconf, result)
else:
  result = renderer

rhost, rport, rurl = get_renderer_control(result)
addr = 'http://' + rhost + ':' + str(rport) + rurl

if a1 == '-C':
  renderer_cmd_multi(addr, 'Play', play_message, True)
  print_finish(True)
if a1 == '-P':
  renderer_cmd_multi(addr, 'Pause', pause_message, True)
  print_finish(True)
if a1 == '-S':
  renderer_cmd_multi(addr, 'Stop', stop_message, True)
  print_finish(True)

my_http_addr = get_router(rhost, rport)

payload = ''
if a1 == '-f':
  payload = 'http://' + my_http_addr + '/' + urllib2.quote(os.path.basename(sys.argv[2]))
if a1 == '-u':
  payload = sys.argv[2]
if a1 == '-y':
  command = [ytd, '-g', '--format', 'mp4', sys.argv[2]]
  process = subprocess.Popen(command, stdout=subprocess.PIPE)
  out, err = process.communicate()
  for url in out:
    payload = out.strip()
  if payload == '':
    print ' [:(] youtube-dl could not provide us with url'
    print_finish(False)
  print ' [:)] caught this url: %s' % payload

if payload == '':
  return_help()

message_template = xml_head + '<u:SetAVTransportURI ' + it + '<CurrentURI>' + payload + msg_tail

renderer_cmd_multi(addr, 'Stop', stop_message, False)
renderer_cmd_multi(addr, 'SetAVTransportURI', message_template, True)
renderer_cmd_multi(addr, 'Play', play_message, True)

print_finish(True)
