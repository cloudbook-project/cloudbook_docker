#!/bin/bash

openvpn --config /etc/openvpn/client/client01.ovpn &

sleep 10
echo "Start Mount DIRs"
mount -o nfsvers=3,nolock 10.10.0.1:/share /share -t nfs
mkdir -p /root/cloudbook/base_project/distributed
mount -v -t nfs -o nfsvers=3,nolock 10.10.0.1:/root/cloudbook/base_project/distributed /root/cloudbook/base_project/distributed
mkdir /root/cloudbook/base_project/agents
#python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_id "" -project_folder base_project
sh /root/refresh.sh &

while :
do
   echo "Running and OK"
   sleep 60
done
