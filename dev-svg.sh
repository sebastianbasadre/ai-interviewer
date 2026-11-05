#!/usr/bin/env bash
# Local SVG-avatar dev server. Run: bash dev-svg.sh
set -a
APP_MODE=mock
AVATAR_MODE=svg
REALTIME_ENABLED=true
ALLOW_MOCK_LAN_HTTP=true
WHISPER_DEVICE=cpu
WHISPER_MODEL=tiny
PUBLIC_BASE_URL=https://192.168.2.6:8000
TLS_CERT_FILE=/tmp/devcert/cert.pem
TLS_KEY_FILE=/tmp/devcert/key.pem
ADMIN_API_KEY=devkey00000000000000000000000000
IP_HASH_SECRET=hashsecret000000000000000000000000
PRIVACY_CONTACT=dev@local
PYTHONPATH=src
set +a
exec /home/workbench/.venvs/ai-interviewer/bin/python -m ai_interviewer
