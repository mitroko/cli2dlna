#!/usr/bin/env python
import os, socket, sys, urllib2

# Default timeout 3H
socket.setdefaulttimeout(10800)

try:
  location = sys.stdin.readline().split(' ')
  url = str(location[1])
  sys.stdout.write("HTTP/1.1 200\r\n")
  sys.stdout.write("Transfer-Encoding: chunked\r\n")
  u = urllib2.urlopen('http://try.lc' + url, timeout = 3)
  meta = u.info()
  file_size = int(meta.getheaders("Content-Length")[0])
  sys.stdout.write('Content-Type: ' + meta.getheaders("Content-Type")[0] + '\r\n')
  sys.stdout.write('\r\n')
  blk_size = 8192
  transfered = 0
  while True:
    buffer = u.read(blk_size)
    transfered += blk_size
    if not buffer:
      break
    tosend = '%X\r\n%s\r\n'%(len(buffer),buffer)
    sys.stdout.write(tosend)
  sys.stdout.write('0\r\n\r\n')
except:
  pass
