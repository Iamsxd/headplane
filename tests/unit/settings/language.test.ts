import { describe, expect, test } from "vitest";

import { getLanguage, isLanguage, languageRedirect, setLanguage } from "~/utils/language";

describe("dashboard language preference", () => {
  test("remembers the chosen language without changing other browser cookies", async () => {
    const serialized = await setLanguage("en");
    const preference = serialized.split(";", 1)[0];
    expect(await getLanguage(`session=private; ${preference}; color_scheme=existing`)).toBe("en");
    const chinese = (await setLanguage("zh-CN")).split(";", 1)[0];
    expect(await getLanguage(chinese)).toBe("zh-CN");
    expect(serialized).toMatch(/Path=\/admin(?:;|$)/);
    expect(serialized).toContain("Max-Age=31536000");
    expect(serialized).toContain("HttpOnly");
    expect(serialized).toContain("Secure");
    expect(serialized).toContain("SameSite=Lax");
  });

  test.each([undefined, null, "", "hp_language=broken", "hp_language=ImZyIg%3D%3D"])(
    "defaults safely for absent, damaged or unsupported cookie: %s",
    async (header) => expect(await getLanguage(header)).toBe("zh-CN"),
  );

  test.each(["fr", "en-US", "EN", "", null, 1, {}])(
    "rejects an unsupported language: %s",
    (value) => expect(isLanguage(value)).toBe(false),
  );

  test("rejects an array masquerading as a language", () => {
    expect(isLanguage(["en"])).toBe(false);
  });

  test("keeps the current administrative page and filters", () => {
    expect(languageRedirect("/machines?status=offline&user=owner")).toBe(
      "/machines?status=offline&user=owner",
    );
    expect(languageRedirect("/machines/3#details")).toBe("/machines/3#details");
  });

  test.each([null, "//evil.example", "https://evil.example", "/\\evil.example", "/../outside",
    "/%2e%2e/outside", "/x\r\nLocation: https://evil.example",
    "/x/..//evil.example", "/.//evil.example", "/a/%2e%2e//evil.example"])(
    "never redirects outside the dashboard: %s",
    (value) => expect(languageRedirect(value)).toBe("/"),
  );
});
