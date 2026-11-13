import { createCookie } from "react-router";

export type Language = "zh-CN" | "en";

const cookie = createCookie("hp_language", {
  path: __PREFIX__,
  maxAge: 31536000,
  httpOnly: true,
  secure: true,
  sameSite: "lax",
});

export function isLanguage(value: unknown): value is Language {
  return value === "zh-CN" || value === "en";
}

export async function getLanguage(header: string | null | undefined): Promise<Language> {
  try {
    const value: unknown = await cookie.parse(header ?? null);
    return isLanguage(value) ? value : "zh-CN";
  } catch {
    return "zh-CN";
  }
}

export function setLanguage(language: Language) {
  return cookie.serialize(language);
}

export function languageRedirect(value: FormDataEntryValue | null): string {
  const base = `${__PREFIX__}/`;
  const fallback = "/";
  // Reject separators and control characters before constructing a Location.
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") ||
      value.includes("\\") || Array.from(value).some((character) => {
        const code = character.charCodeAt(0);
        return code < 32 || code === 127;
      })) {
    return fallback;
  }
  const url = new URL(`${__PREFIX__}${value}`, "https://headplane.invalid");
  // React Router adds its basename to action redirects, including document POSTs.
  if (!url.pathname.startsWith(base)) return fallback;
  const path = url.pathname.slice(__PREFIX__.length);
  // Normalization can create a leading // even when the raw input lacked it.
  if (path.startsWith("//")) return fallback;
  return path + url.search + url.hash;
}
