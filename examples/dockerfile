FROM fedora
MAINTAINER langdon <langdon@fedoraproject.org>
RUN yum clean all && yum -y update
RUN yum -y install python python-pip make gcc krb5-devel python-devel python-setuptools python-gssapi python-nitrate python-dateutil python-urllib-gssapi
RUN yum clean all

COPY . /opt/did
WORKDIR /opt/did
RUN python setup.py install
#RUN ln -s /user-home/.did /root/.did
RUN ln -s /did.conf /root/.did

VOLUME /did.conf

LABEL RUN docker run --privileged --rm -it -v $(HOME)/.did:/did.conf $(USERNAME)/did

ENTRYPOINT ["/usr/bin/did"]
