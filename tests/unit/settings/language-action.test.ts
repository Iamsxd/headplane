import { expect, test } from "vitest";

import { action } from "~/routes/util/language";

function submit(origin: string | undefined, language = "en") {
  const headers = new Headers({ "Content-Type": "application/x-www-form-urlencoded" });
  if (origin !== undefined) headers.set("Origin", origin);
  const request = new Request("https://dashboard.example/admin/api/language", {
    method: "POST", headers,
    body: new URLSearchParams({ language, returnTo: "/machines?status=offline" }),
  });
  return action({ request } as Parameters<typeof action>[0]);
}

test("same-origin language changes set a preference and redirect to the current route", async () => {
  const response = await submit("https://dashboard.example");
  expect(response.status).toBe(303);
  expect(response.headers.get("Location")).toBe("/machines?status=offline");
  expect(response.headers.get("Set-Cookie")).toContain("hp_language=");
});

test.each([undefined, "null", "https://evil.example", "https://dashboard.example:444"])(
  "rejects missing or cross-origin language POST: %s",
  async (origin) => {
    await expect(submit(origin)).rejects.toMatchObject({ init: { status: 403 } });
  },
);
