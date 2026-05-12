#!/bin/bash
set -e

/usr/sbin/sshd

exec python -m uvicorn main:app --host 0.0.0.0 --port 3111
