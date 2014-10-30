# Ejabberd 14.07

FROM ubuntu:14.04

MAINTAINER Rafael Römhild <rafael@roemhild.de>

# System update
RUN rm /etc/apt/sources.list.d/proposed.list
RUN apt-get -qq update
# ejabberd related stuff
RUN DEBIAN_FRONTEND=noninteractive apt-get -qqy install wget libyaml-0-2 \
    libexpat1 erlang-nox python-jinja2
# Park related stuff
RUN DEBIAN_FRONTEND=noninteractive apt-get -qqy install python-virtualenv git-core \
    python-dev libxslt1-dev zlib1g-dev

# Add ejabberd user and group
RUN groupadd -r ejabberd \
    && useradd -r -g ejabberd -d /opt/ejabberd -s /usr/sbin/nologin ejabberd
RUN mkdir -p /opt/ejabberd/ /opt/park/
RUN chown -R ejabberd:ejabberd /opt/ejabberd /opt/park

# ejabberd
USER ejabberd
RUN wget -q -O /tmp/ejabberd-installer.run "http://www.process-one.net/downloads/downloads-action.php?file=/ejabberd/14.07/ejabberd-14.07-linux-x86_64-installer.run"
RUN chmod +x /tmp/ejabberd-installer.run
RUN /tmp/ejabberd-installer.run --mode unattended --prefix /opt/ejabberd --adminpw ejabberd

# config
ADD ./ejabberd.yml.tpl /opt/ejabberd/conf/ejabberd.yml.tpl
ADD ./ejabberdctl.cfg /opt/ejabberd/conf/ejabberdctl.cfg
RUN sed -i "s/ejabberd.cfg/ejabberd.yml/" /opt/ejabberd/bin/ejabberdctl

# wrapper for setting config on disk from environment
# allows setting things like XMPP domain at runtime
ADD ./run /opt/ejabberd/bin/run
ADD ./park-setup /opt/ejabberd/bin/park-setup

# Clean up when done.
USER root
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
USER ejabberd

# set home dir
ENV HOME /opt/ejabberd

EXPOSE 5222 5269 5280
VOLUME ["/opt/ejabberd/database", "/opt/ejabberd/ssl", "/opt/park"]

CMD /opt/ejabberd/bin/run start && /opt/ejabberd/bin/park-setup
