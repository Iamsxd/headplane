import type { RequestListener } from "node:http";

import { getLanguage } from "~/utils/language";

export function languageDispatch(chinese: RequestListener, english: RequestListener): RequestListener {
  return (request, response) => {
    void getLanguage(request.headers.cookie).then((language) => {
      (language === "en" ? english : chinese)(request, response);
    }).catch(() => {
      if (!response.headersSent) response.writeHead(500);
      response.end();
    });
  };
}
