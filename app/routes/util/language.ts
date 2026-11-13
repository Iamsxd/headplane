import { data, redirect } from "react-router";

import { isLanguage, languageRedirect, setLanguage } from "~/utils/language";

import type { Route } from "./+types/language";

export async function action({ request }: Route.ActionArgs) {
  if (request.headers.get("Origin") !== new URL(request.url).origin) {
    throw data("Forbidden", { status: 403 });
  }
  const form = await request.formData();
  const language = form.get("language");
  if (!isLanguage(language)) {
    throw data("Bad Request", { status: 400 });
  }
  return redirect(languageRedirect(form.get("returnTo")), {
    status: 303,
    headers: { "Set-Cookie": await setLanguage(language) },
  });
}
