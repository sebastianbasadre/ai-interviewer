#!/usr/bin/env bash
# Create a mock interview invitation. Run: bash invite.sh
/home/workbench/.venvs/ai-interviewer/bin/python - << 'EOF'
import urllib.request, json, ssl
ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    "https://192.168.2.6:8000/admin/interviews",
    data=json.dumps({"role_id": "pm_po"}).encode(),
    headers={"X-Admin-Key": "devkey00000000000000000000000000", "Content-Type": "application/json"},
    method="POST",
)
resp = urllib.request.urlopen(req, context=ctx)
data = json.loads(resp.read())
print("Open this URL in your browser:")
print(data.get("url") or json.dumps(data, indent=2))
EOF
