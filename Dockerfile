FROM registry.fedoraproject.org/fedora

# For root user
RUN set -x && \
  mkdir -p /tmt/

COPY plans/main.fmf /tmt/plans/
COPY .fmf/ /tmt/.fmf

# In case someone needs regular user
ENV HOME_DIR /home/test

RUN set -x && \
  mkdir -p $HOME_DIR/tmt/

COPY plans/main.fmf $HOME_DIR/tmt/plans/
COPY .fmf/ $HOME_DIR/tmt/.fmf

RUN set -x && \
  echo "Set disable_coredump false" >> /etc/sudo.conf && \
  sed -i '/tsflags=nodocs/d' /etc/dnf/dnf.conf && \
  \
  dnf install -y tmt-all beakerlib && \
  \
  dnf autoremove -y && \
  dnf clean all --enablerepo='*' && \
  useradd -u 1001 test && \
  chown -R test:test $HOME_DIR && \
  echo 'test ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# USER 1001
# Run as root by default
# WORKDIR $HOME_DIR/tmt

WORKDIR /tmt

CMD tmt run -av provision -h local
