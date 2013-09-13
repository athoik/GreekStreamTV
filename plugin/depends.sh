#!/bin/sh

opkg update

opkg install python-compression
opkg install python-ctypes
opkg install python-zlib
opkg install python-subprocess
opkg install python-pkgutil
opkg install python-json
opkg install python-textutils
opkg install python-shell
opkg install python-io
opkg install python-misc

if [ -d "/usr/lib/python2.7" ]; then
 opkg install gst-plugins-good-flv
else
 opkg install gst-plugin-flv
fi

echo
echo -n "Depends Installation Completed. Please Restart STB"

exit 0

