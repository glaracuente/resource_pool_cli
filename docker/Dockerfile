FROM alpine:3.7

ENV ANSIBLE_VERSION 2.8.0

ENV BUILD_PACKAGES \
  bash \
  curl \
  tar \
  openssh-client \
  sshpass \
  git \
  python \
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
    \
    echo "==> Cleaning up..."  && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* && \
    \
    echo "==> Adding hosts for convenience..."  && \
    mkdir -p /etc/ansible /ansible && \
    echo "[local]" >> /etc/ansible/hosts && \
    echo "localhost" >> /etc/ansible/hosts \
    \
    echo "==> Adding resource_pool cli..."  && \
    apk add python3 && \
    pip3 install click && \
    pip3 install prettytable && \
    apk add wget && \
    apk add vim && \
    mkdir /etc/resource_pool_cli/ && \
    wget https://raw.githubusercontent.com/glaracuente/resource_pool_cli/develop/resource_pool_cli/resource_pool.py -O /etc/resource_pool_cli/resource_pool.py
# change to master for final release

ENV ANSIBLE_GATHERING smart
ENV ANSIBLE_HOST_KEY_CHECKING false
ENV ANSIBLE_RETRY_FILES_ENABLED false
ENV ANSIBLE_ROLES_PATH /ansible/playbooks/roles
ENV ANSIBLE_SSH_PIPELINING True
ENV PYTHONPATH /ansible/lib
ENV PATH /ansible/bin:$PATH
WORKDIR /etc/resource_pool_cli/

RUN chmod 755 /etc/resource_pool_cli/resource_pool.py
ENTRYPOINT ["/etc/resource_pool_cli/resource_pool.py"]

