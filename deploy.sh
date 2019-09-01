#!/bin/sh
sudo mkdir wphotos
sudo mount.cifs //192.168.0.244/wphotos wphotos/ -o user=wphotos password=$wphotos_password
sudo docker-compose up -d --build
