#!/bin/bash
# This script runs during PostgreSQL container initialization.
# It configures pg_hba.conf to allow md5 connections from Docker bridge network.
set -e

# Append a rule allowing all connections with md5 auth
# This is needed because Docker containers connect from non-localhost IPs
cat >> "$PGDATA/pg_hba.conf" << EOF

# Docker bridge network — allow md5 auth from all IPv4 addresses
host    all             all             0.0.0.0/0               md5
EOF

echo "pg_hba.conf updated to allow Docker bridge connections"
