#!/bin/sh
./destroy.sh
cp -TRv firefox_cache_bck firefox_cache
./deploy.sh