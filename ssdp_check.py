#!/usr/bin/env python
#
#    Description : Command line tool to check DLNA renderers.
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
import socket                            # used to implement socket funcions
import struct                            # used during ip calculations
from StringIO import StringIO as fake_io # used for fake socket

class SsdpFakeSocket(fake_io):
  def makefile(self, *args, **kw): return self

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

# array members deduplication
def uniq_array(seq):
  seen = set()
  seen_add = seen.add
  return [x for x in seq if not (x in seen or seen_add(x))]

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


ifaces, ips = all_interfaces(16)

results = []
print
print ' [**] Dropping into SSDP discovery. Please wait'
for ip in ips:
  ssdp_discover('urn:schemas-upnp-org:service:AVTransport:1', ip, results)
results = uniq_array(results)

print
if len(results) < 1:
  print ' [:(] No UPnP renders answered. Try again'
else:
  print results

print
