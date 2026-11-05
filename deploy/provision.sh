#!/usr/bin/env bash
set -euo pipefail
apt-get update
apt-get install -y docker.io docker-compose-v2 python3
systemctl enable --now docker
usermod -aG docker vagrant
install -d -o vagrant -g vagrant /opt/tor-base
cp -a /vagrant/. /opt/tor-base/
cd /opt/tor-base
python3 scripts/configure.py
# Bind on the VM interface so VirtualBox NAT forwarding reaches it.
# The host-side forwarded port remains loopback-only.
sed -i 's/127.0.0.1:8080:8000/0.0.0.0:8080:8000/' compose.yaml
docker compose up -d --build
chown -R vagrant:vagrant /opt/tor-base
printf '\nReady: http://127.0.0.1:8080 . Create a user as described in README.md.\n'
