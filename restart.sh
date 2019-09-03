#!/bin/sh
echo "----------------Started Restart--------------------"
./destroy.sh
sudo cp -TRv firefox_cache_bck firefox_cache
./deploy.sh
echo "----------------Ended restart-----------------------"