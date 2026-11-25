# Private relay selection and adding a second relay

## Production history

On 2026-11-13 the operator requested removal of all public Tailscale DERP regions. Production `/etc/headscale/config.yaml` has `derp.urls: []` and `derp.paths: []`, with the existing embedded region `999 / tencent-cn` enabled and automatically added. The automatic refresh setting remains enabled with an empty URL list. Since the [2026-11-25 domain cutover](DOMAIN.md), the relay advertises `hs.lovecanl.cn` with the existing public IPv4 `140.143.127.180`.

The reference [DERP configuration fragment](templates/headscale-derp-private.yaml) contains no credentials. It is not a complete Headscale configuration and must not overwrite unrelated control/DNS/policy/database settings.

Before the change, the consistent backup completed at `/var/backups/headscale/20261113T091049535091Z`; the private original configuration is also in `/root/headscale-private-derp-20261113/config-before.yaml`. Configuration validation passed before restarting only Headscale. Device IDs 3/4/5, their keys and server identity/DERP keys were unchanged; all three clients reconnected. Existing Nginx/Headplane/Casdoor/Komari services stayed active.

At the time of the November 13 change, the Windows Tailscale 1.104.7 client received exactly one DERP region, `999 / tencent-cn`. Its DERP diagnostic established an authenticated relay connection and received an IPv4 STUN response. The Windows-to-phone probe returned `via DERP(tencent-cn)` at 181 ms, 78 ms and 68 ms. Public HTTPS health, control routing, DERP upgrade/server-key frame and STUN binding checks passed. Those checks established IPv4 connectivity.

## Adding another public server

Another server needs a standalone `derper` service; it does not need a second Headscale control server or a second dashboard. Joining a machine as an ordinary Tailscale client alone does not make it a DERP relay.

1. Use a stable public server, with reachable TCP 443 and UDP 3478. TCP 80 supports certificate issuance/renewal and HTTP connectivity checks when configured. Configure its host/cloud firewalls, real DERP HTTP-upgrade support and STUN service. Avoid a CDN proxy in front of DERP.
2. Install and pin the official Tailscale `derper`, configure a trusted TLS certificate and renewal. A domain can be used; an IP endpoint requires a publicly trusted certificate containing that IP, as with the current server. Do not disable certificate verification.
3. Enable client verification so the relay is not open to unrelated users. This can use a local `tailscaled` joined to this Headscale with `derper --verify-clients`, or Headscale's `/verify` endpoint via `--verify-client-url`. Evaluate the control-server outage behavior: the URL method's default fail-open must not be accepted silently; fail-closed also depends on the control server being reachable for new relay connections.
4. Give the new relay its own unique region ID/code, for example `998 / backup-2`, while retaining `999 / tencent-cn`. Copy the reviewed [additional map example](templates/derp-additional.example.yaml) to `/etc/headscale/derp-extra.yaml` only after replacing the documentation host/IP and validating the new relay. Never publish an untested example as a live node.
5. Add the map to Headscale's existing DERP section, preserving `urls: []` and the embedded server:

   ```yaml
   paths:
     - /etc/headscale/derp-extra.yaml
   ```

6. Extend the protected backup to include the additional map and back up the new relay's private configuration/key independently. Run `headscale configtest`, reload/restart Headscale, and inspect the received map on real clients using `tailscale debug derp-map`, `tailscale netcheck`, `tailscale debug derp backup-2` and actual peer probes. Test fallback by stopping only the relay service, not by disconnecting production control access.

Clients automatically choose usable home regions based on network conditions and latency. This is not a strict primary/standby order, a manual server picker, or a zero-interruption guarantee. Direct connections remain available. If avoiding overseas relay paths is a requirement, place and register only acceptable locations.

A second relay provides relay redundancy; the current Headscale control service remains on the Tencent server. Whole-host/control failure and verification behavior need their own acceptance checks before claiming end-to-end high availability.

Sources: [Headscale DERP configuration and verification](https://headscale.net/stable/ref/derp/) and [Tailscale custom DERP documentation](https://tailscale.com/docs/reference/derp-servers/custom-derp-servers).
