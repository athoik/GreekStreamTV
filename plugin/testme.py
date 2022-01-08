"""
Test Livestreamer Script for enigma2

Test commands:
cd /usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV
python testme.py

"""

import sys
sys.path.append("/usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV")

import os
import requests
from livestreamer import Livestreamer

url = "http://www.dailymotion.com/video/xqjey2"
#url = "hds://http://btslive-lh.akamaihd.net/z/live_1@87036/manifest.f4m"
#url = "http://www.youtube.com/watch?v=ZTf2EzTd1TE"

livestreamer = Livestreamer()
livestreamer.set_loglevel("debug")
channel = livestreamer.resolve_url(url)
streams = channel.get_streams()

print('Streams: %s' % list(streams.keys()))

stream = streams["best"]
print(stream)

fd = stream.open()

while True:
    data = fd.read(1024)
    if len(data) == 0:
        break
    else:
        print("Got Data! Livestreamer Works!")
        break

# All streams are not guaranteed to support .close()
if hasattr(fd, "close"):
    fd.close()
fd = None

