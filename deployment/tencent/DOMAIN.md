# Tencent domain cutover

On 2026-11-25 the Headscale server URL moved to `https://hs.lovecanl.cn` after the blog's ICP filing was completed. Use the domain as the custom login server for new Tailscale clients. Devices configured with `https://140.143.127.180` can continue to connect on their existing settings.

| Service | URL |
| --- | --- |
| Headscale control | `https://hs.lovecanl.cn` |
| Headplane dashboard | `https://hs.lovecanl.cn/admin/` |
| Casdoor account and MFA settings | `https://hs.lovecanl.cn/auth/account` |
| Blog | `https://lovecanl.cn/` |

The IP HTTPS virtual host keeps the Headscale protocol routes and IP certificate. Its `/admin` and `/auth` entries redirect to the new dashboard and account pages, respectively, without carrying old query parameters. Browser sessions are scoped to the host, so dashboard users sign in again at the new URL. Casdoor continues to use its existing users, signing keys, client credentials and MFA enrollment. Headplane keeps its existing owner mapping. The only relay in the map remains `999 / tencent-cn`, now advertised as `hs.lovecanl.cn` with the existing public IPv4. Both certificate timers remain active.

## Deployment and rollback

The [cutover script](ops/switch-headscale-domain.py) moves Casdoor's app and organization URLs in one SQLite transaction while the provider is stopped. It updates the provider origin, Headplane URLs, protected login note and Nginx routes. After checking the new issuer and PKCE callback over trusted HTTPS it calls the existing `headscale-endpoint` helper to validate and switch `server_url`. The helper preserves the DERP settings and the rest of the Headscale configuration.

The provider database changes were rehearsed and reversed on a consistent copy. The pre- and post-cutover backups are `/var/backups/headscale/20261125T132019641121Z` and `/var/backups/headscale/20261125T133152492336Z`. Configuration rollback files are under `/root/headscale-domain-20261125.ikttTirE/` on the server. If the migration validation fails, the script restores these configuration files and only the affected URL fields. To undo this specific cutover while those configuration backups are current, run the following as root:

```sh
python3 /root/headscale-domain-20261125.ikttTirE/switch-headscale-domain.py rollback /root/headscale-domain-20261125.ikttTirE
```

Rollback uses the IP endpoint again and can briefly interrupt dashboard access and Headscale control connections. Review later configuration changes before using the rollback. Retain the live databases, which contain later registrations and account activity.

## Verification

- Public trusted HTTPS, Headscale control routing, DERP upgrade and UDP STUN passed using both the domain and the IP. The public blog still returned HTTP 200 with the ICP footer.
- Two disposable userspace clients, one using the domain and one using the IP, registered and exchanged encrypted probes via `DERP(tencent-cn)`. Both ran on the server. Their map contained only region 999 with `hs.lovecanl.cn`, and the test user, nodes and keys were removed.
- The new public OIDC discovery, authorization and callback use the domain. A temporary ordinary account signed in through Headplane, enrolled TOTP, signed in with a dynamic code, and signed out through Casdoor. The temporary account was removed. The real administrator's existing enrollment was checked without using their authenticator.
- All three original device identities, the Headscale and relay keys, the dashboard user roles, and the existing owner password and TOTP data matched the pre-cutover snapshot. The Mac client was online at the post-cutover check. Three SQLite checks and all 43 post-cutover manifest hashes passed.
