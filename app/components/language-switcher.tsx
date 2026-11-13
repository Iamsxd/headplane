import { Languages } from "lucide-react";
import { Form, useLocation } from "react-router";

import { UI_LANGUAGE } from "~/utils/ui-language";

export default function LanguageSwitcher() {
  const location = useLocation();
  return (
    <Form method="post" action="/api/language" reloadDocument className="flex shrink-0 items-center gap-1">
      <Languages aria-hidden="true" className="size-4" />
      <select
        aria-label="语言 / Language"
        name="language"
        defaultValue={UI_LANGUAGE}
        className="max-w-28 rounded-md bg-transparent px-1 py-1 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/40 dark:bg-mist-950"
        onChange={(event) => event.currentTarget.form?.requestSubmit()}
      >
        <option value="zh-CN">简体中文</option>
        <option value="en">English</option>
      </select>
      <input type="hidden" name="returnTo" value={location.pathname + location.search + location.hash} />
      <noscript><button type="submit">切换 / Apply</button></noscript>
    </Form>
  );
}
