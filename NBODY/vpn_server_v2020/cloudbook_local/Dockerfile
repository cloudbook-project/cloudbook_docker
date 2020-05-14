FROM centos:centos7
LABEL manteiner="EXPERIS IT. Maintainer Francisco Abril"

RUN yum update -y 

ENV TZ=Europe/Madrid

#SET LOCALE ENG UTF8
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG=en_US.UTF-8

ADD entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

#VPN CONFIGURATION
RUN yum install -y epel-release
RUN yum install -y openvpn easy-rsa
#INSTALL FIREWALL
RUN yum install -y iptables

#CLOUDBOOK CREATE CERTS
ADD vpn/server/server.conf /etc/openvpn/server/server.conf
ADD create-certs.sh /etc/openvpn/create-certs.sh
ADD create-certs-client.sh /etc/openvpn/create-certs-client.sh
WORKDIR "/etc/openvpn/"
RUN sh create-certs.sh
RUN cp /etc/openvpn/server/ca.crt /etc/openvpn/client/ca.crt
RUN sh create-certs-client.sh
RUN openssl genpkey -genparam -algorithm DH -out /etc/openvpn/server/dh.pem 

#NFS SERVER
RUN yum install nfs-utils -y

#CLOUBOOK AGENT 0
RUN yum update -y && \
yum -y install \
python3.7 \
python3-pip \
git

#CLOUDBOOK DEPENDENCIES
RUN yum -y install python3-tkinter
RUN pip3 install --trusted-host pypi.org --trusted-host files.pythonhosted.org ply flask pynat radon astunparse requests
WORKDIR "/root"

WORKDIR "/etc/cloudbook"
RUN git clone https://github.com/cloudbook-project/cloudbook_deployer.git
RUN git clone https://github.com/cloudbook-project/cloudbook_maker2.git
RUN git clone https://github.com/cloudbook-project/cloudbook_agent.git


#CLOUDBOOK FIX
ADD cloudbook_agent_fix/agent.py /etc/cloudbook/cloudbook_agent/agent.py
#ADD cloudbook_maker2_fix/cloudbook_maker.py /etc/cloudbook/cloudbook_maker2/cloudbook_maker.py

WORKDIR "/etc/cloudbook/cloudbook_deployer"

#RUN ln -s /root/cloudbook/base_project/distributed /share


#FOR DEBUG PURPOSE
RUN yum -y install nano net-tools

#VAMOS A EVITAR PROBLEMAS DE DOS2UNIX
RUN yum install dos2unix -y
RUN dos2unix /entrypoint.sh

#ATAJOS
RUN echo "alias ll='ls -l'" >> /root/.bashrc

CMD ["/entrypoint.sh"]
