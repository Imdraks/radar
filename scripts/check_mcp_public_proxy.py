"""Validate MCP/HTML Nginx dispatch with explicit local upstream fixtures.

Requires Docker and nginx:1.28-alpine already pulled. No published ports,
network access, volumes, tokens or production requests are used by the test.
"""
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
mapping = (ROOT / 'docker/nginx/snippets/radar-mcp-html.map.conf').read_text()
location = (ROOT / 'docker/nginx/snippets/radar-mcp-public.location.conf').read_text()
location = location.replace('127.0.0.1:13100', '127.0.0.1:18081').replace('127.0.0.1:3000', '127.0.0.1:18082')
location = location.replace('include proxy_params;', 'include /tmp/radar-proxy-params;')
configuration = '''pid /tmp/radar-nginx.pid;
error_log /dev/stderr warn;
events {}
http {
access_log off;
''' + mapping + '''
server { listen 127.0.0.1:18081; default_type application/json; return 401 '{"error":"fixture_auth_required"}'; }
server { listen 127.0.0.1:18082; default_type text/html; return 200 '<h1>fixture_public_page</h1>'; }
server { listen 127.0.0.1:18080;
''' + location + '''
location = /.well-known/oauth-protected-resource/mcp { return 200 'fixture_metadata_unchanged'; }
}
}
'''
shell = '''set -eu
cat > /tmp/radar-test.conf <<'RADAR_NGINX'
''' + configuration + '''RADAR_NGINX
cat > /tmp/radar-proxy-params <<'RADAR_PROXY'
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
RADAR_PROXY
nginx -t -c /tmp/radar-test.conf
nginx -c /tmp/radar-test.conf
trap 'nginx -s quit -c /tmp/radar-test.conf' EXIT
'''
cases = [
    ('GET', 'text/html', 200, 'fixture_public_page'),
    ('GET', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 200, 'fixture_public_page'),
    ('HEAD', 'text/html', 200, None),
    ('POST', 'text/html', 401, 'fixture_auth_required'),
    ('GET', 'application/json, text/event-stream', 401, 'fixture_auth_required'),
    ('GET', 'text/event-stream', 401, 'fixture_auth_required'),
    ('GET', '*/*', 401, 'fixture_auth_required'),
    ('DELETE', 'text/html', 401, 'fixture_auth_required'),
]
for method, accept, status, marker in cases:
    options = '--head' if method == 'HEAD' else f'-X {method}'
    shell += f"code=$(curl -sS {options} -H {shlex.quote('Accept: ' + accept)} -o /tmp/radar-body -w '%{{http_code}}' http://127.0.0.1:18080/mcp)\n"
    shell += f'[ "$code" = "{status}" ]\n'
    if marker:
        shell += f'grep -q {shlex.quote(marker)} /tmp/radar-body\n'
    shell += f'printf "%s\\n" {shlex.quote(f"PASS {method} Accept={accept}: {status}")}\n'
shell += "curl -fsS http://127.0.0.1:18080/.well-known/oauth-protected-resource/mcp | grep -q fixture_metadata_unchanged\n"
shell += "printf '%s\\n' 'PASS OAuth metadata route unchanged'\n"
subprocess.run(['docker', 'run', '--rm', '--pull=never', '--network=none', '-i',
                '--entrypoint', 'sh', 'nginx:1.28-alpine', '-s'], input=shell, text=True, check=True)
