"""Render the reviewed private native-OIDC configuration; no output at import."""
import json

ORIGIN = 'https://140.143.127.180'
IMAGE = 'sha256:8548bee3872a70b3cab2c8bfc30262bd5ebeeb0bd5bcd9cf357c85188e56c25f'


def render(client_id, port=3000, candidate_secret=None):
    cookie = ('cookie_secret: ' + candidate_secret) if candidate_secret else 'cookie_secret_path: /etc/headplane/cookie-secret'
    return f'''server:
  host: 127.0.0.1
  port: {port}
  base_url: {ORIGIN}
  {cookie}
  cookie_secure: true
  cookie_max_age: 28800
  data_path: /var/lib/headplane
  proxy_auth:
    enabled: false
headscale:
  url: http://127.0.0.1:8081
  public_url: {ORIGIN}
  config_path: /etc/headscale/config.yaml
  api_key_path: /etc/headplane/headscale-api-key
oidc:
  issuer: {ORIGIN}/auth
  client_id: {json.dumps(client_id)}
  client_secret_path: /etc/headplane/oidc-client-secret
  disable_api_key_login: true
  use_pkce: true
  use_end_session: true
  subject_claims: [sub]
  default_role: member
  token_endpoint_auth_method: client_secret_post
  post_logout_redirect_uri: {ORIGIN}/admin/login?s=logout
integration:
  agent:
    enabled: false
  docker:
    enabled: false
  kubernetes:
    enabled: false
    pod_name: headscale
  proc:
    enabled: false
'''
