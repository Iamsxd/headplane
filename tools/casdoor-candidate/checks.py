"""Fail-closed acceptance checks; also enforced by optimized Python."""
from urllib.parse import urlsplit


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def disabled_login_response(status, headers):
    require(status == 403, 'Disabled login was not rejected with 403')
    require(not any(name.lower() == 'set-cookie' for name, _ in headers),
            'Disabled login issued a session cookie')


def protected_response(status, location):
    if status in [401, 403]:
        return
    target = urlsplit(location or '')
    require(status in [302, 303] and not target.scheme and not target.netloc
            and target.path in ['/admin/login', '/admin/oidc/start'],
            'Spoofed principal was not redirected to authentication')


def logged_out_response(status, body, language):
    text = {'zh-CN': '你已退出登录', 'en': 'You have been logged out'}[language]
    require(status == 200 and f'lang="{language}"' in body and text in body,
            'Translated logged-out page was not rendered')


def enrollment_results(results):
    required = ['password_only_requires_enrollment', 'invalid_setup_code_rejected',
                'unverified_enable_rejected', 'code_issuance_blocked_after_unverified_enable',
                'id_token_denied_after_unverified_enable', 'ordinary_test_user_is_not_admin']
    require(all(results.get(key) is True for key in required),
            'Candidate failed mandatory enrollment acceptance; production cutover forbidden')
