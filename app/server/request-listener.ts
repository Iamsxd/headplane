import { createRequestListener } from "@react-router/node";
import { RouterContextProvider } from "react-router";
import * as build from "virtual:react-router/server-build";

import {
  type AppContext,
  agentsContext, appConfigContext, authContext, dbContext, headscaleContext,
  headscaleApiKeyContext, headscaleConfigContext, headscaleLiveStoreContext,
  integrationContext, oidcContext, requestApiContext,
} from "./context";

// Both compiled views inject the same initialized services into their own
// React Router context keys. Creating a view never creates another database,
// auth service, polling loop, agent or network listener.
export function createAppRequestListener(ctx: AppContext) {
  return createRequestListener({
    build,
    mode: import.meta.env.MODE,
    getLoadContext(request: Request, client: { address?: string }) {
      ctx.auth.registerRequestClientAddress(request, client.address);
      const routerContext = new RouterContextProvider();
      routerContext.set(agentsContext, ctx.agents);
      routerContext.set(appConfigContext, ctx.config);
      routerContext.set(authContext, ctx.auth);
      routerContext.set(dbContext, ctx.db);
      routerContext.set(headscaleContext, ctx.headscale);
      routerContext.set(headscaleApiKeyContext, ctx.headscaleApiKey);
      routerContext.set(headscaleConfigContext, ctx.hs);
      routerContext.set(headscaleLiveStoreContext, ctx.hsLive);
      routerContext.set(integrationContext, ctx.integration);
      routerContext.set(oidcContext, ctx.oidc);
      routerContext.set(requestApiContext, ctx.apiForRequest);
      return routerContext;
    },
  });
}
