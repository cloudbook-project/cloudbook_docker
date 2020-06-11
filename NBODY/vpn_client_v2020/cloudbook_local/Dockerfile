FROM centos:7.7.1908
LABEL manteiner="EXPERIS IT. Maintainer Francisco Abril"

ENV TZ=Europe/Madrid
ARG DEBIAN_FRONTEND=noninteractive

ADD refresh.sh /root/refresh.sh
ADD entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

#VPN CONFIGURATION
RUN yum install -y epel-release
RUN yum install -y openvpn easy-rsa
#INSTALL FIREWALL
RUN yum install -y iptables

#NFS CLIENT
RUN yum install nfs-utils -y
RUN mkdir -p /share


#CLOUBOOK AGENT N
RUN yum -y install \
python3.7 \
python3-pip \
python3-devel \
gcc \
git

#CLOUDBOOK DEPENDENCIES
RUN yum -y install python3-tkinter
RUN pip3 install --trusted-host pypi.org --trusted-host files.pythonhosted.org ply flask pynat radon astunparse requests psutil ifaddr
WORKDIR "/root"

WORKDIR "/etc/cloudbook"
RUN git clone https://github.com/cloudbook-project/cloudbook_agent.git

WORKDIR "/etc/cloudbook/cloudbook_agent"

#RUN ln -s /root/cloudbook/base_project/distributed /share

#FOR DEBUG PURPOSE
RUN yum -y install nano net-tools

#VAMOS A EVITAR PROBLEMAS DE DOS2UNIX
RUN yum install dos2unix -y
RUN dos2unix /entrypoint.sh
RUN dos2unix /root/refresh.sh

#ATAJOS
RUN echo "alias ll='ls -l'" >> /root/.bashrc

CMD ["/entrypoint.sh"]
