#!/bin/sh
./destroy.sh
sudo cp -TRv firefox_cache_bck firefox_cache
./deploy.sh