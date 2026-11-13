# Headplane installation plan

**Goal:** Add a usable authenticated Headplane dashboard to the existing IP HTTPS Headscale deployment.

**Architecture:** Pinned official Headplane0.8.2 OCI image, non-root service identity, loopback port3000, existing Nginx `/admin/` proxy. Nginx authenticates one administrator and overwrites trusted proxy identity headers. Keep application API key server-side, rotate it before its90-day expiry. Reuse existing IP/domain TLS and preserve registered nodes, Headscale state and DERP.

**Choices:** Docker host networking reaches native Headscale loopback without migrating it. Read-only access to Headscale config displays settings without allowing the container to rewrite/restart the native service. Agent/browser SSH and Docker socket access are unnecessary for device administration. API-backed device/user/key/route functions remain available. Password generated privately and delivered outside workspace. No changes to existing clients required.

- [x] Back up current services; install Docker and pin official image digest.
- [x] Configure non-root container, persistent data, proxy authentication and HTTPS admin routes on IP/domain virtual hosts.
- [x] Validate unauthorized denial, identity-header spoofing denial, authenticated device listing, existing control/DERP/STUN/blog and registered node preservation.
- [x] Configure90-day application key with monthly renewal and rollback on failed startup.
- [x] Extend private backup for dashboard data/config/credentials and validate snapshot.
- [x] Deliver private login file, document usage/recovery/limitations, perform final review.

Ruling: prior user acceptance and explicit installation request authorize this reversible deployment; no redundant design approval. This is a non-Git infrastructure workspace; use private rollback copies rather than worktree/commits. Focused tests cover credential rotation failure handling; live probes cover configuration and installed behavior.

## Verification record

- Docker26.1.5 and official Headplane0.8.2 installed; fixed digest recorded in private runtime environment and deployment docs. App reports Node24.22.1 and successful Headscale0.29.7 connection.
- Initial startup exposed a required schema field even for disabled Kubernetes integration; added `pod_name: headscale` as in the release sample. App now healthy.
- Backups of pre-change Nginx/Headscale and registered nodes: `/root/headplane-setup-20261113/before` on server.
- Public trusted HTTPS: unauthenticated, spoofed-identity and wrong-password requests401; valid admin200 with Windows device rendered and53JS/CSS references loaded200. Proxy authentication does not create an application cookie on these requests; Nginx requires Basic authentication on every dashboard request.
- Real API key rotation service succeeded, exactly one active key remains, prior key expired. Three isolated rotation tests passed. Headplane and timer active/enabled.
- Current Windows node identity, IPs and user preserved. Existing public Headscale control route, DERP handshake and STUN passed; blog local trusted TLS/HTTP200 and Komari active.
- Final snapshot `/var/backups/headscale/20261113T061622309327Z`:35manifest hashes/private modes and both SQLite integrity checks passed. Evidence: `artifacts/tencent-headscale/headplane-final-20261113.txt`, `headplane-public-20261113.txt`.
- Credentials delivered outside workspace to `C:\Users\17610\.ssh\tencent-headplane-admin.txt` with current Windows account-only ACL. No runtime API keys or passwords printed.
- Static review by headplane_review found no important issues.
- User then requested mobile authorization: initial stale request rejected; fresh request approved as `findn3` (`100.64.0.4`). Initial Windows→phone probes timed out while Android had disconnected. After the phone reconnected, all3probes succeeded via its LAN endpoint in24–89ms. This verifies real Windows/Android encrypted connectivity by direct path; it does not force or claim cross-network use of the self-hosted DERP. Evidence: `artifacts/tencent-headscale/windows-phone-20261113.txt`.
- On the user's subsequent connected confirmation, initial probes timed out again with both clients online. Diagnostic check established trusted IPv4 DERP/STUN successfully. Subsequent actual Windows→Android probes returned via DERP(tencent-cn) twice,59ms/65ms, without any configuration changes. Two real clients' self-hosted relay use is now verified: `artifacts/tencent-headscale/windows-phone-derp-20261113.txt`.
