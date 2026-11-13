import http.client
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import time

stage = Path('/root/headplane-mfa-20261113/app-candidate')
stage.mkdir(mode=0o700, exist_ok=True)
env = dict(line.split('=',1) for line in Path('/etc/headplane/runtime.env').read_text().splitlines() if '=' in line)
uid, gid = int(env['HEADPLANE_UID']), int(env['HEADPLANE_GID'])
data = stage/'data'; data.mkdir(mode=0o700,exist_ok=True);os.chown(data,uid,gid)
with sqlite3.connect('file:/var/lib/headplane/hp_persist.db?mode=ro',uri=True) as src:
    with sqlite3.connect(data/'hp_persist.db') as dst:
        src.backup(dst)
        assert dst.execute('pragma integrity_check').fetchone()[0]=='ok'
os.chown(data/'hp_persist.db',uid,gid);os.chmod(data/'hp_persist.db',0o600)
config = Path('/etc/headplane/config.yaml').read_text()
assert config.count('port: 3000')==1 and 'oidc:' not in config
config=config.replace('port: 3000','port: 3002')
config,count=re.subn(r'(?m)^(\s+)enabled: true$',r'\1enabled: false',config)
assert count==1, 'Expected exactly one enabled proxy-auth setting'
config+='\noidc:\n  issuer: https://140.143.127.180/auth\n  client_id: candidate-only\n  client_secret: candidate-only-not-a-real-credential\n  disable_api_key_login: true\n  use_end_session: true\n'
path=stage/'config.yaml';path.write_text(config);os.chown(path,0,gid);os.chmod(path,0o640)
name='headplane-mfa-boundary-candidate'
subprocess.run(['docker','run','-d','--name',name,'--init','--network','host','--user',f'{uid}:{gid}',
    '--group-add',env['HEADSCALE_GID'],'--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=32m',
    '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','512m',
    '--log-opt','max-size=5m','--log-opt','max-file=2','-e','HEADPLANE_CONFIG_PATH=/candidate-config.yaml',
    '--mount','type=bind,src=/etc/headplane,dst=/etc/headplane,readonly',
    '--mount','type=bind,src=/etc/headscale,dst=/etc/headscale,readonly',
    '--mount',f'type=bind,src={path},dst=/candidate-config.yaml,readonly',
    '--mount',f'type=bind,src={data},dst=/var/lib/headplane',
    'headplane-local:0.8.2-mfa-prepared-20261113'],check=True,stdout=subprocess.DEVNULL)


def request(path, body=None, content_type='application/x-www-form-urlencoded',cookie=''):
    c=http.client.HTTPConnection('127.0.0.1',3002,timeout=10)
    c.request('GET' if body is None else 'POST',path,body,{
        'Host':'140.143.127.180','Origin':'https://140.143.127.180',
        'X-Forwarded-Proto':'https','Content-Type':content_type,'Cookie':cookie,
        'Remote-User':'admin','Remote-Email':'admin@headplane.local',
        'Authorization':'Basic ZHVtbXk6ZHVtbXk=',
    })
    r=c.getresponse();status=r.status;headers=dict(r.getheaders());body=r.read().decode();c.close()
    return status,headers,body


try:
    for _ in range(40):
        try:
            request('/admin/login?s=logout');break
        except OSError:time.sleep(0.25)
    results={}
    for path in ['/admin/login','/admin/login.data']:
        for body,kind in [('api_key=irrelevant','application/x-www-form-urlencoded'),
                          ('invalid multipart','multipart/form-data')]:
            status,headers,_=request(path,body,kind)
            assert status==403 and 'Set-Cookie' not in headers,(path,status)
        results[path+' disabled POSTs']=True
    for lang,marker in [('', 'lang="zh-CN"'),('hp_language=ImVuIg%3D%3D','lang="en"')]:
        status,headers,body=request('/admin/login?s=logout',cookie=lang)
        assert status==200 and marker in body,('bilingual logged-out view',status,marker)
    results['bilingual_logged_out_pages']=True
    status,_,_=request('/admin/machines')
    assert status in [302,303,401,403],('spoofed principal denial',status)
    results['basic_and_spoofed_principal_denied']=True
    (stage.parent/'app-boundary-acceptance.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
finally:
    subprocess.run(['docker','stop',name],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['docker','rm',name],check=True,stdout=subprocess.DEVNULL)
