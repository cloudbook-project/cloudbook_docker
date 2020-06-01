================
  REQUIREMENTS
================

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

----------------------------------------------------------------------------------------------------

=====================
  CREATE CONTAINERS
=====================

INSTRUCTIONS ONLY FOR AGENT 0 USER
----------------------------------
0) Enter in subfolder vpn_server_v2020
1) RUN: docker-compose up -d --build
2) Identify DOCKER_NAME. In order to find DOCKER_NAME execute "docker ps", output example:
CONTAINER ID        IMAGE                          COMMAND             CREATED             STATUS              PORTS                     NAMES (This is the DOCKER_NAME)
1f2fae46cc70        vpn_server_v2020_vpn_cloudbook   "/entrypoint.sh"    25 minutes ago      Up 25 minutes       0.0.0.0:11194->1194/tcp   vpn_server_v2020_vpn_cloudbook_1

3) Extract client certs:
   A) docker cp vpn_server_v2020_vpn_cloudbook_1:/etc/openvpn/client/ca.crt export_client/
   B) docker cp vpn_server_v2020_vpn_cloudbook_1:/etc/openvpn/client/client01.crt export_client/
   C) docker cp vpn_server_v2020_vpn_cloudbook_1:/etc/openvpn/client/client01.key export_client/

5) By default the port in host will be 11194 it must be open in our router. Use the same port in NAT to avoid misconfigurations.

6) Modify file client01.ovpn for the rest of agents. 
   For example, instead of:
     remote vpn_server_v2020_vpn_cloudbook_1 1194
   replace by:
     remote 212.132.34.114 11194
     
7) Send the 4 files to the rest of cloudbook agents (ca.crt, client01.crt, client01.key, client01.ovpn)


INSTRUCTIONS FOR THE REST OF AGENTS
-----------------------------------
1) You can skip this step if you have received the client01.ovpn file

   Inside vpn_client_v2020/cloudbook_local/vpn/client/ open the file client01.ovpn and change the next line:
	remote vpnserverv2020_vpn_cloudbook_1 1194
   Change vpn_server_v2020_vpn_cloudbook_1  by the AGENT_0 IP (Server) and the port of the server, if it is not changed use 11194 by default.
   For example, instead of:
     remote vpn_server_v2020_vpn_cloudbook_1 1194
   replace by:
     remote 212.132.34.114 11194
   
2) Copy the files sent from agent_0 user (client01.ovpn, ca.crt, client01.crt and client01.key) in vpn_client_v2020/cloudbook_local/vpn/client/

3) RUN: docker-compose up -d --build
    If an error raises up, follow the instructions printed on screen such as:
      execute:
        docker network create cloudbook
    else
      be patient, the cointainer is being created and takes some time. 
      during creation, it may ask you permission for accessing your file system
     
4) Identify DOCKER_NAME. In order to find DOCKER_NAME execute "docker ps", output example:
CONTAINER ID        IMAGE                          COMMAND             CREATED             STATUS              PORTS                     NAMES (This is the DOCKER_NAME)
6f2f2346cc11        vpn_client_v2020_vpn_cloudbook   "/entrypoint.sh"    25 minutes ago      Up 25 minutes       0.0.0.0:11194->1194/tcp   vpn_client_v2020_vpn_cloudbook_1

Therefore <DOCKER_NAME> is the value of the last column. In this example is: vpn_client_v2020_vpn_cloudbook_1

5) In order to check that everything is correct:
   A) Check Logs: docker logs vpn_client_v2020_vpn_cloudbook -f
   B) Check test file shared: docker exec -it vpn_client_v2020_vpn_cloudbook bash (Enter in bash of container)
      RUN: ll /share (we will see a test file)

----------------------------------------------------------------------------------------------------

=======================
  CLOUDBOOK EXECUTION
=======================

INSTRUCTIONS FOR SERVER (agent 0 only)
--------------------------------------
1) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_maker2/cloudbook_maker.py -project_folder <PROJECT_NAME>
2) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_0 -grant MEDIUM -project_folder <PROJECT_NAME>
3) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_agent/agent.py launch -agent_id agent_0 -project_folder <PROJECT_NAME> -verbose &

INSTRUCTIONS FOR CLIENTS  (rest of agents)
------------------------------------------
4) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_agent/agent.py create -project_folder <PROJECT_NAME> -grant <HIGH | MEDIUM |LOW>  
   For example:
     docker exec -it vpn_client_v2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py create -project_folder base_project -grant MEDIUM
   After this command, a cloudbook agent is created. Take note of agent_ID

5) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_agent/agent.py launch -agent_id <AGENT_ID_GENERATED> -project_folder <PROJECT_NAME> [-verbose]
  For example:
    docker exec -it vpn_client_v2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py launch -agent_id agent_NP1XWSTVFQ9UDMO96XCO -project_folder base_project -verbose

INSTRUCTIONS FOR SERVER
-----------------------
6) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_deployer/cloudbook_deployer.py -project_folder <PROJECT_NAME>
   The list of DUs and which agents will load each of them will be displayed on screen. This process may take some time.

7) docker exec -it <DOCKER_NAME> python3 /etc/cloudbook/cloudbook_deployer/cloudbook_run.py -project_folder <PROJECT_NAME>
   This command finally launches the program with cloudbook

----------------------------------------------------------------------------------------------------

===================================
  EXAMPLE OF EXECUTION BY EXPERIS
===================================
SERVER
1) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_maker2/cloudbook_maker.py -project_folder base_project
2) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py create -agent_0 -project_folder base_project -grant MEDIUM
3) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py launch -agent_id agent_0 -project_folder base_project -verbose &

CLIENT
4) docker exec -it vpnclientv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py create -project_folder base_project -grant MEDIUM
5) docker exec -it vpnclientv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_agent/agent.py launch -agent_id <AGENT_ID_GENERATED> -project_folder base_project -verbose

SERVER
6) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_deployer/cloudbook_deployer.py -project_folder base_project
7) docker exec -it vpnserverv2020_vpn_cloudbook_1 python3 /etc/cloudbook/cloudbook_deployer/cloudbook_run.py -project_folder base_project
