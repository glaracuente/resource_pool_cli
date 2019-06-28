FROM alpine:3.7

ENV ANSIBLE_VERSION 2.8.0
ENV ANSIBLE_GATHERING smart
ENV ANSIBLE_HOST_KEY_CHECKING false
ENV ANSIBLE_RETRY_FILES_ENABLED false
ENV ANSIBLE_SSH_PIPELINING True
ENV PYTHONPATH /ansible/lib
ENV PATH /ansible/bin:$PATH

ENV BUILD_PACKAGES \
  bash \
  curl \
  wget \
  tar \
  openssh-client \
  sshpass \
  git \
  python \
  python3 \
  py-boto \
  py-dateutil \
  py-httplib2 \
  py-jinja2 \
  py-paramiko \
  py-pip \
  py-yaml \
  ca-certificates

RUN set -x && \
    \
    echo "==> Adding build-dependencies..."  && \
    apk --update add --virtual build-dependencies \
      gcc \
      musl-dev \
      libffi-dev \
      openssl-dev \
      python-dev && \
    \
    echo "==> Upgrading apk and system..."  && \
    apk update && apk upgrade && \
    \
    echo "==> Adding Python runtime..."  && \
    apk add --no-cache ${BUILD_PACKAGES} && \
    pip install --upgrade pip && \
    pip install python-keyczar docker-py && \
    \
    echo "==> Installing Ansible..."  && \
    pip install ansible==${ANSIBLE_VERSION} && \
    mkdir -p /etc/ansible /ansible && \
    \
    echo "==> Cleaning up..."  && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* && \
    \
    echo "==> Adding resource_pool cli..."  && \
    pip3 install click prettytable && \
    mkdir /etc/resource_pool_cli/ && \
    wget https://raw.githubusercontent.com/glaracuente/resource_pool_cli/master/resource_pool_cli/resource_pool_cli.py \
    -O /etc/resource_pool_cli/resource_pool_cli.py && \
    wget https://raw.githubusercontent.com/glaracuente/resource_pool_cli/master/resource_pool_cli/pool_helpers.py \
    -O /etc/resource_pool_cli/pool_helpers.py && \
    chmod 755 /etc/resource_pool_cli/resource_pool_cli.py && \
    chmod 755 /etc/resource_pool_cli/pool_helpers.py


ENTRYPOINT ["/etc/resource_pool_cli/resource_pool_cli.py"]

