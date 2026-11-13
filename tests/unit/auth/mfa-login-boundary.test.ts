import { describe, expect, test, vi } from "vitest";

import { appConfigContext, authContext, headscaleContext } from "~/server/context";

// Helper to create a mock FormData with optional api_key
function mockFormData(apiKey?: string): FormData {
  const formData = new FormData();
  if (apiKey !== undefined) {
    formData.set("api_key", apiKey);
  }
  return formData;
}

// Helper to create mock request
function mockRequest(formData: FormData): Request {
  return {
    formData: () => Promise.resolve(formData),
  } as unknown as Request;
}

// Types for test clarity
interface LoginResult {
  success: boolean;
  message: string;
}

interface MockApiKey {
  prefix: string;
  expiration: string | null;
}

interface MockHeadscale {
  client: (apiKey?: string) => {
    apiKeys: {
      list: ReturnType<typeof vi.fn>;
    };
  };
}

interface MockAuth {
  createApiKeySession: ReturnType<typeof vi.fn>;
}

// React Router 7 provides context values through context.get(contextKey).
// This helper creates a fake AppLoadContext that returns the correct mock
// depending on the context key that is requested.
function createMockContext({ headscale, auth, disabled = false }: {
  headscale: MockHeadscale; auth: MockAuth; disabled?: boolean;
}) {
  return {
    get: (context: typeof authContext | typeof headscaleContext | typeof appConfigContext) => {
      if (context === appConfigContext) return { oidc: { disable_api_key_login: disabled } };
      if (context === authContext) return auth;
      if (context === headscaleContext) return headscale;
      return undefined;
    },
  };
}

// Mock the log module to avoid console spam during tests
vi.mock("~/utils/log", () => ({
  default: {
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

describe("OIDC-only login boundary", () => {
  test.each(["/admin/login", "/admin/login.data"])(
    "disabled API-key login rejects %s before parsing malformed input",
    async (path) => {
      const { loginAction } = await import("~/routes/auth/login/action");
      const request = new Request(`https://example.test${path}`, {
        method: "POST", body: "invalid multipart", headers: { "Content-Type": "multipart/form-data" },
      });
      const client = vi.fn();
      const createApiKeySession = vi.fn();
      const result = await loginAction({ request, params: {}, context: createMockContext({
        disabled: true, headscale: { client }, auth: { createApiKeySession },
      }) } as any);
      expect(result).toBeInstanceOf(Response);
      expect((result as Response).status).toBe(403);
      expect((result as Response).headers.has("Set-Cookie")).toBe(false);
      expect(client).not.toHaveBeenCalled();
      expect(createApiKeySession).not.toHaveBeenCalled();
    },
  );

  test("API-key login stays available when it is not disabled", async () => {
    const { loginAction } = await import("~/routes/auth/login/action");
    const result = await loginAction({ request: mockRequest(mockFormData("valid.secret")), params: {},
      context: createMockContext({
        headscale: { client: () => ({ apiKeys: { list: vi.fn().mockResolvedValue([
          { prefix: "valid", expiration: "2099-01-01T00:00:00Z" },
        ]) } }) },
        auth: { createApiKeySession: vi.fn().mockResolvedValue("valid-cookie") },
      }),
    } as any);
    expect(result).toBeInstanceOf(Response);
    expect((result as Response).status).toBe(302);
    expect((result as Response).headers.get("Set-Cookie")).toBe("valid-cookie");
  });

});
