REQUIREMENTS

1) Install Docker CE
WINDOWS
https://docs.docker.com/docker-for-windows/install/
LINUX - CENTOS7
https://docs.docker.com/engine/install/centos/

2) Install docker-compose
WINDOWS 
Included in previous installation.
LINUX-CENTOS
https://docs.docker.com/compose/install/

CREATE CONTAINERS

ONLY FOR AGENT 0 USER:
//////////////////////////////////
0) enter in subfolder vpn_server_v2020
1) RUN: docker-compose up -d --build
2) Identify DOCKER_NAME. In order to find DOCKER_NAME execute "docker ps", output example:
CONTAINER ID        IMAGE                          COMMAND             CREATED             STATUS              PORTS                     NAMES (This is the DOCKER_NAME)
1f2fae46cc70        vpnserverv2020_vpn_cloudbook   "/entrypoint.sh"    25 minutes ago      Up 25 minutes       0.0.0.0:11194->1194/tcp   vpnserverv2020_vpn_cloudbook_1

3) Extract client certs:
   A) docker cp vpnserverv2020_vpn_cloudbook_1:/etc/openvpn/client/ca.crt export_client/
   B) docker cp vpnserverv2020_vpn_cloudbook_1:/etc/openvpn/client/client01.crt export_client/
   C) docker cp vpnserverv2020_vpn_cloudbook_1:/etc/openvpn/client/client01.key export_client/

5) By default the port in host will be 11194 it must be open in our router. Use the same port in NAT for avoid misconfigurations.


FOR THE REST OF AGENTS:
//////////////////////////////////
vpn_client_v2020
1) Inside vpn_client_v2020/cloudbook_local/vpn/client/ open the file client01.ovpn and change the next line:
	remote vpnserverv2020_vpn_cloudbook_1 1194
   Change vpnserverv2020_vpn_cloudbook_1  by the AGENT_0 IP (Server) and the port of the server, if it is not changed use 11194 by default.
2) Copy the extract files in server ca.crt, client01.crt y client01.key in vpn_client_v2020/cloudbook_local/vpn/client/

3) RUN: docker-compose up -d --build

4) Identify DOCKER_NAME. In order to find DOCKER_NAME execute "docker ps", output example:
CONTAINER ID        IMAGE                          COMMAND             CREATED             STATUS              PORTS                     NAMES (This is the DOCKER_NAME)
6f2f2346cc11        vpnclientv2020_vpn_cloudbook   "/entrypoint.sh"    25 minutes ago      Up 25 minutes       0.0.0.0:11194->1194/tcp   vpnclientv2020_vpn_cloudbook_1

5) In order to check if all is correct:
   A) Check Logs: docker logs vpnclientv2020_vpn_cloudbook -f
   B) Check test file shared: docker exec -it vpnclientv2020_vpn_cloudbook bash (Enter in bash of container)
      RUN: ll /share (we will see a test file)
	

#CLOUDBOOK EXECUTION

SERVER
1) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_maker2/cloudbook_maker.py -project_folder NOMBRE_PROYECTO
2) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_id 0 -project_folder NOMBRE_PROYECTO
3) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_agent/agent.py -agent_id agent_0 -project_folder NOMBRE_PROYECTO -verbose &

CLIENT
4) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_id "" -project_folder NOMBRE_PROYECTO
5) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_agent/agent.py -agent_id "AGENT_ID_GENERATED" -project_folder NOMBRE_PROYECTO

SERVER
7) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_deployer/cloudbook_deployer.py -project_folder NOMBRE_PROYECTO
8) docker exec -it DOCKER_NAME python3 /etc/cloudbook/cloudbook_deployer/cloudbook_run.py -project_folder NOMBRE_PROYECTO


#EXPERIS EXECUTION
SERVER
1) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_maker2/cloudbook_maker.py -project_folder base_project
2) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_id 0 -project_folder base_project
3) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py -agent_id agent_0 -project_folder base_project -verbose &

CLIENT
4) docker exec -it vpnclientv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_id "" -project_folder base_project
5) docker exec -it vpnclientv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py -agent_id "AGENT_ID_GENERATED" -project_folder base_project -verbose

SERVER
7) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_deployer/cloudbook_deployer.py -project_folder base_project
8) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_deployer/cloudbook_run.py -project_folder base_project
