FROM fedora
MAINTAINER langdon <langdon@fedoraproject.org>
RUN yum clean all && yum -y update
RUN yum -y install python python-pip make gcc krb5-devel python-devel python-setuptools python-kerberos python-nitrate python-dateutil python-urllib2_kerberos
RUN yum clean all

COPY . /opt/status-report
WORKDIR /opt/status-report
RUN source/setup.py install
#RUN ln -s /user-home/.status-report /root/.status-report
RUN ln -s /status-report.conf /root/.status-report

VOLUME /status-report.conf

LABEL RUN docker run --privileged --rm -it -v $(HOME)/.status-report:/status-report.conf $(USERNAME)/status-report

ENTRYPOINT ["/usr/bin/status-report"]
