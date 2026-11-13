import { describe, expect, test, vi } from "vitest";
import { appConfigContext, authContext, oidcContext } from "~/server/context";

vi.mock("~/utils/log", () => ({
  default: { warn: vi.fn(), error: vi.fn(), debug: vi.fn(), info: vi.fn() },
}));

describe("login page availability", () => {
  test.each([true, false])("API-key availability respects disabled=%s during an OIDC outage", async (disabled) => {
    const { loader } = await import("~/routes/auth/login/page");
    const url = new URL("https://example.test/admin/login");
    const response = await loader({
      request: new Request(url), url, params: {},
      context: { get(key: unknown) {
        if (key === appConfigContext) return { server: { cookie_secure: true }, oidc: { disable_api_key_login: disabled } };
        if (key === authContext) return { require: async () => { throw new Error("No session"); } };
        if (key === oidcContext) return { state: "enabled", value: {
          discover: async () => ({ ok: false, error: { code: "discovery_failed", message: "Unavailable" } }),
          status: () => ({ state: "error", error: { code: "discovery_failed", message: "Unavailable" } }),
        } };
        throw new Error("Unexpected context");
      } },
    } as any);
    expect(response).toMatchObject({ isApiKeyLoginEnabled: !disabled, oidcErrorCodes: ["discovery_failed"] });
  });
});
