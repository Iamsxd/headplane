import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class AcceptanceChecks(unittest.TestCase):
    def test_cookie_denial_handles_case_and_duplicate_fields(self):
        from checks import disabled_login_response
        for headers in [[('set-cookie', 'test')], [('X-Test','1'),('SET-Cookie','test')],
                        [('Set-Cookie','first'),('set-cookie','second')]]:
            with self.assertRaises(RuntimeError):
                disabled_login_response(403, headers)
        disabled_login_response(403, [('Cache-Control','no-store')])
        with self.assertRaises(RuntimeError):
            disabled_login_response(200, [])

    def test_spoof_denial_requires_an_authentication_redirect(self):
        from checks import protected_response
        for status, target in [(302,'/admin/machines'),(302,'https://evil.test/login'),(200,None)]:
            with self.assertRaises(RuntimeError):
                protected_response(status, target)
        protected_response(302, '/admin/login')
        protected_response(401, None)

    def test_bilingual_probe_requires_visible_translation(self):
        from checks import logged_out_response
        with self.assertRaises(RuntimeError):
            logged_out_response(200, '<html lang="en">中文</html>', 'en')
        with self.assertRaises(RuntimeError):
            logged_out_response(302, 'lang="zh-CN" 登录', 'zh-CN')

    def test_rejected_provider_fails_even_with_python_optimization(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for filename in ['verify-enrollment.py','checks.py']:
                source=Path(__file__).with_name(filename)
                if source.exists():shutil.copyfile(source,root/filename)
            (root/'state').mkdir()
            (root/'state/credentials.json').write_text('{"maintenance_password":"test-only","client_id":"test-only","client_secret":"test-only"}')
            (root/'prepare.py').write_text('''from pathlib import Path
ROOT=Path(__file__).parent/'state'
class Api:
 def ok(self,route,payload=None):
  return {'isAdmin':False} if 'get-user' in route else None
 def request(self,route,payload=None,form=False):
  if 'initiate' in route:return {'status':'ok','data':{'secret':'JBSWY3DPEHPK3PXP','recoveryCodes':['test-only']}}
  if '/verify' in route:return {'status':'error'}
  if '/enable' in route:return {'status':'ok'}
  if 'access_token' in route:return {'id_token':'test-only'}
  return {'status':'ok','data':'RequiredMfa' if payload.get('username') else 'test-authorization-code'}
''')
            # Only private receipt output is redirected; paths remain inside the sandbox.
            script=root/'verify-enrollment.py'
            script.write_text(script.read_text().replace("Path('/root/headplane-mfa-20261113/enrollment-acceptance.json')", "ROOT / 'receipt.json'"))
            # Parentheses keep the original method call binding after substituting the receipt path.
            script.write_text(script.read_text().replace("ROOT / 'receipt.json'.write_text", "(ROOT / 'receipt.json').write_text"))
            result=subprocess.run([sys.executable,'-O',str(script)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0,result.stdout)
            self.assertIn('Candidate failed mandatory enrollment acceptance',result.stderr)


if __name__=='__main__':unittest.main()
