// Backend feature state is shared by both views; translate only its presentation.
const reasons: Record<string, string> = {
  "Agent is not enabled in the configuration": "配置中未启用 Headplane Agent",
  "Agent requires headscale.api_key to be configured": "Headplane Agent 需要配置 headscale.api_key",
  "Agent requires Headscale 0.28 or newer": "Headplane Agent 需要 Headscale 0.28 或更新版本",
  "Agent failed to initialize (see logs)": "Headplane Agent 初始化失败（请查看日志）",
  "OIDC is not configured": "尚未配置 OIDC",
  "OIDC is disabled in the configuration": "配置中已禁用 OIDC",
  "OIDC requires headscale.api_key to be configured": "OIDC 需要配置 headscale.api_key",
  "OIDC requires server.base_url to be configured": "OIDC 需要配置 server.base_url",
};

export function featureReason(reason: string): string {
  return reasons[reason] ?? reason;
}
