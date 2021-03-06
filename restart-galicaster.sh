#!/bin/bash

# kill galicaster
echo "" >> /tmp/restart-galicaster.log
echo "----Running restart script----> `date`"  >> /tmp/restart-galicaster.log
date
echo "Killing Galicaster"
pkill -u $USER python

echo "Waiting 20 sec for network to be established"
sleep 20

# start galicaster again
echo "Restarting Galicaster"
/opt/galicaster/run_galicaster.py >> /tmp/restart-galicaster.log &
