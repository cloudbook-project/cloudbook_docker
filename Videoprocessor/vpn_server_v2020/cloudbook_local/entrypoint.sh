#!/bin/bash

#ENABLE PORT FORWARD
echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
sysctl -p

#OPEN VPN
iptables -t nat -A POSTROUTING -s 10.10.0.0/24 -o eth0 -j MASQUERADE
openvpn --config /etc/openvpn/server/server.conf &

#CLOUDBOOK
#python3 /etc/cloudbook/cloudbook_maker2/cloudbook_maker.py -project_folder base_project
#python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_id 0 -project_folder base_project

#NFS SERVER CONFIG
#ESTAS CARPETAS DEBEN ESTAR MAPEADAS EN EL HOST
mnt=/share
chmod 777 $mnt
echo "$mnt *(rw,fsid=2,sync,no_subtree_check)" >> /etc/exports

mnt_cloud=/root/cloudbook/base_project/distributed
chmod 777 $mnt_cloud
echo "$mnt_cloud *(rw,fsid=1,sync,no_subtree_check)" >> /etc/exports

exportfs -ar
rpcbind
rpc.statd
rpc.nfsd

exec rpc.mountd --foreground


