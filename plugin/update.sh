#!/bin/sh
URL="http://sgcpm.com/livestream/stream.xml"

if wget -q -O /tmp/stream.xml $URL
then
    mv /tmp/stream.xml $1
    echo "stations updated successfully"
else
    echo "error downloading stations"
fi
echo
