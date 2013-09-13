#!/bin/sh
cd /tmp
echo -------------------------------------------------------------------------
echo $1
echo -------------------------------------------------------------------------
case $1 in
############# update #############
"update")
    URL="http://sgcpm.com/livestream/stream.xml"
    echo -n "Downloading new stream.xml file..."
    if wget -q -O /tmp/stream.xml $URL; then
        chmod 644 /tmp/stream.xml
        mv /tmp/stream.xml /usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV
        echo -n "... stream.xml updated."
    else
        echo "error!"
    fi
    ;;
*)
    echo "error"
    ;;
esac
exit 0
