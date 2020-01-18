#!/bin/sh
cd /etc/enigma2

if ! grep -q greekstreamtv.tv bouquets.tv
then
    sed -i '2i #SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.greekstreamtv.tv" ORDER BY bouquet' bouquets.tv
    echo "bouquet created successfully"
fi
echo
