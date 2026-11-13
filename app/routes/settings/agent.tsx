import { featureReason } from "~/utils/feature-reason";
import { useFetcher } from "react-router";

import Button from "~/components/button";
import Link from "~/components/link";
import Notice from "~/components/notice";
import StatusCircle from "~/components/status-circle";
import Text from "~/components/text";
import Title from "~/components/title";
import { agentsContext, authContext } from "~/server/context";
import { formatTimeDelta } from "~/utils/time";

import type { Route } from "./+types/agent";

export async function loader({ request, context }: Route.LoaderArgs) {
  const agents = context.get(agentsContext);
  const auth = context.get(authContext);

  await auth.require(request);

  if (agents.state !== "enabled") {
    return { enabled: false as const, reason: featureReason(agents.reason) };
  }

  const sync = agents.value.lastSync();
  return {
    enabled: true as const,
    syncedAt: sync.syncedAt?.toISOString() ?? null,
    nodeCount: sync.nodeCount,
    error: sync.error,
    authUrl: sync.authUrl,
  };
}

export async function action({ request, context }: Route.ActionArgs) {
  const agents = context.get(agentsContext);
  const auth = context.get(authContext);

  await auth.require(request);

  if (agents.state !== "enabled") {
    return { success: false, error: featureReason(agents.reason) };
  }

  await agents.value.triggerSync();
  const sync = agents.value.lastSync();
  return {
    success: !sync.error,
    error: sync.error,
    authUrl: sync.authUrl,
  };
}

export default function Page({ loaderData }: Route.ComponentProps) {
  const fetcher = useFetcher<typeof action>();
  const isSyncing = fetcher.state !== "idle";

  if (!loaderData.enabled) {
    return (
      <div className="flex max-w-(--breakpoint-lg) flex-col gap-8">
        <Title>Headplane Agent</Title>
        <Notice title="Agent 未启用">
          {loaderData.reason}。有关 Agent 的配置方法，请参阅{" "}
          <Link external styled to="https://headplane.net/features/agent">
            文档
          </Link>
        </Notice>
      </div>
    );
  }

  const isPending = !loaderData.syncedAt && loaderData.authUrl;
  const hasError = Boolean(loaderData.error);

  return (
    <div className="flex max-w-(--breakpoint-lg) flex-col gap-8">
      <div className="flex w-full flex-col sm:w-2/3">
        <Title>Headplane Agent</Title>
        <Text>
          Headplane Agent 会同步 Tailnet 中节点的操作系统版本、连接详情等信息。
        </Text>
      </div>

      <div className="flex items-center gap-3">
        <StatusCircle isOnline={!hasError && !isPending} className="h-5 w-5" />
        <span className="text-lg font-medium">
          {hasError ? "错误" : isPending ? "等待批准" : "正常"}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <Text>
          <span className="font-medium">上次同步：</span>
          {loaderData.syncedAt ? (
            <span suppressHydrationWarning>{formatTimeDelta(new Date(loaderData.syncedAt))}</span>
          ) : (
            "从未同步"
          )}
        </Text>
        <Text>
          <span className="font-medium">已同步节点数：</span>
          {loaderData.nodeCount}
        </Text>
      </div>

      {isPending ? (
        <Notice variant="warning" title="Agent 需要批准">
          Agent 正在等待批准其 Tailnet 注册申请。Headplane 将尝试自动批准；如未成功，您可以访问{" "}
          <Link external styled to={loaderData.authUrl!}>
            此链接完成批准
          </Link>
          。
        </Notice>
      ) : undefined}

      {loaderData.error ? (
        <Notice variant="error" title="同步错误">
          {loaderData.error}
        </Notice>
      ) : undefined}

      <fetcher.Form method="post">
        <Button type="submit" variant="heavy" disabled={isSyncing}>
          {isSyncing ? "正在同步…" : "立即同步"}
        </Button>
      </fetcher.Form>
    </div>
  );
}
