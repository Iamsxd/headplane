import {
  AlertCircle,
  Construction,
  Eye,
  FlaskConical,
  Pencil,
  Shield,
  TagsIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { isRouteErrorResponse, useFetcher, useRevalidator } from "react-router";

import Button from "~/components/button";
import Card from "~/components/card";
import Code from "~/components/code";
import Link from "~/components/link";
import Notice from "~/components/notice";
import PageError from "~/components/page-error";
import { Tabs, TabsList, TabsPanel, TabsTab } from "~/components/tabs";
import { isApiError } from "~/server/headscale/api/error-client";
import {
  parsePolicy,
  policyDestinations,
  policySources,
  serializePolicy,
  type Policy,
} from "~/utils/acl-policy";
import toast from "~/utils/toast";

import type { Route } from "./+types/overview";
import { aclAction } from "./acl-action";
import { aclLoader } from "./acl-loader";
import Fallback from "./components/fallback";
import RulesEditor from "./components/rules-editor";
import TagsGroupsEditor from "./components/tags-groups-editor";

const LazyEditor = lazy(() =>
  import("./components/cm.client").then((m) => ({ default: m.Editor })),
);
const LazyDiffer = lazy(() =>
  import("./components/cm.client").then((m) => ({ default: m.Differ })),
);

export const loader = aclLoader;
export const action = aclAction;

export default function Page({
  loaderData: { access, writable, policy, users, tagUsage },
}: Route.ComponentProps) {
  const [codePolicy, setCodePolicy] = useState(policy);
  const fetcher = useFetcher<typeof action>();
  const { revalidate } = useRevalidator();
  const disabled = !access || !writable; // Disable if no permission or not writable

  const parsed = useMemo(() => parsePolicy(codePolicy), [codePolicy]);
  const sources = useMemo(
    () => (parsed.ok ? policySources(parsed.policy, users) : []),
    [parsed, users],
  );
  const destinations = useMemo(
    () => (parsed.ok ? policyDestinations(parsed.policy, users) : []),
    [parsed, users],
  );

  useEffect(() => {
    // Update the codePolicy when the loader data changes
    if (policy !== codePolicy) {
      setCodePolicy(policy);
    }
  }, [policy]);

  useEffect(() => {
    if (!fetcher.data) {
      // No data yet, return
      return;
    }

    if (fetcher.data.success === true) {
      toast("策略已更新");
      revalidate();
    }
  }, [fetcher.data]);

  // The structured editors round-trip through the policy text, so the file
  // editor, the diff view and Save all work off one source of truth.
  function applyPolicy(next: Policy) {
    setCodePolicy(serializePolicy(next));
  }

  function structuredPanel(render: (value: Policy) => ReactNode) {
    if (!parsed.ok) {
      return (
        <div className="p-4">
          <Notice title="无法以可视化方式编辑策略" variant="error">
            无法解析策略（{parsed.error}）。请在<Code>编辑文件</Code>{" "}
            选项卡中修复，之后即可恢复可视化编辑。
          </Notice>
        </div>
      );
    }

    return (
      <div className="flex flex-col gap-4 p-4">
        {parsed.hasComments ? (
          <Notice title="注释将被移除" variant="warning">
            此策略包含注释。保存可视化编辑器中的更改会重写策略并移除这些注释。
          </Notice>
        ) : null}
        {render(parsed.policy)}
      </div>
    );
  }

  return (
    <div>
      {!access ? (
        <Notice title="ACL 策略权限受限" variant="warning">
          您无权编辑访问控制列表策略。请联系管理员申请权限，或请管理员修改 ACL 策略。
        </Notice>
      ) : !writable ? (
        <Notice title="ACL 策略为只读" variant="error">
          Headscale 配置中的 ACL 策略模式很可能设置为 <Code>file</Code>，因此无法通过网页界面编辑 ACL 文件。
          请将 Headscale 配置中的 <Code>policy.mode</Code> 设置为{" "}
          <Code>database</Code>。
        </Notice>
      ) : undefined}
      <h1 className="mb-4 text-2xl font-medium">访问控制列表 (ACL)</h1>
      <p className="mb-4 max-w-prose">
        ACL 文件用于定义网络的访问控制规则。有关 ACL 文件的更多信息，请参阅{" "}
        <Link external styled to="https://tailscale.com/kb/1018/acls">
          Tailscale ACL 指南
        </Link>{" "}
        和{" "}
        <Link external styled to="https://headscale.net/stable/ref/acls/">
          Headscale 文档
        </Link>
        。
      </p>
      {fetcher.data?.error !== undefined ? (
        <Notice title={fetcher.data.error.split(":")[0] ?? "错误"} variant="error">
          {fetcher.data.error.split(":").slice(1).join(": ") ??
            "更新 ACL 策略时发生未知错误。"}
        </Notice>
      ) : undefined}
      <Tabs className="mb-4" label="ACL 编辑器" defaultValue="rules">
        <TabsList>
          <TabsTab value="rules">
            <div className="flex items-center gap-2">
              <Shield className="p-1" />
              <span>规则</span>
            </div>
          </TabsTab>
          <TabsTab value="tags">
            <div className="flex items-center gap-2">
              <TagsIcon className="p-1" />
              <span>标签与组</span>
            </div>
          </TabsTab>
          <TabsTab value="edit">
            <div className="flex items-center gap-2">
              <Pencil className="p-1" />
              <span>编辑文件</span>
            </div>
          </TabsTab>
          <TabsTab value="diff">
            <div className="flex items-center gap-2">
              <Eye className="p-1" />
              <span>预览更改</span>
            </div>
          </TabsTab>
          <TabsTab value="preview">
            <div className="flex items-center gap-2">
              <FlaskConical className="p-1" />
              <span>预览规则</span>
            </div>
          </TabsTab>
        </TabsList>
        <TabsPanel value="rules">
          {structuredPanel((value) => (
            <RulesEditor
              destinations={destinations}
              isDisabled={disabled}
              onChange={applyPolicy}
              policy={value}
              sources={sources}
            />
          ))}
        </TabsPanel>
        <TabsPanel value="tags">
          {structuredPanel((value) => (
            <TagsGroupsEditor
              isDisabled={disabled}
              onChange={applyPolicy}
              policy={value}
              tagUsage={tagUsage}
              users={users}
            />
          ))}
        </TabsPanel>
        <TabsPanel value="edit">
          <Suspense fallback={<Fallback />}>
            <LazyEditor isDisabled={disabled} onChange={setCodePolicy} value={codePolicy} />
          </Suspense>
        </TabsPanel>
        <TabsPanel value="diff">
          <Suspense fallback={<Fallback />}>
            <LazyDiffer left={policy} right={codePolicy} />
          </Suspense>
        </TabsPanel>
        <TabsPanel value="preview">
          <div className="flex flex-col items-center py-8">
            <Construction />
            <p className="mt-4 w-1/2 text-center">
              暂不支持预览规则。此功能实现较为复杂，仍在开发中，期待后续推出。
            </p>
          </div>
        </TabsPanel>
      </Tabs>
      <Button
        className="mr-2"
        disabled={
          disabled || fetcher.state !== "idle" || codePolicy.length === 0 || codePolicy === policy
        }
        onClick={() => {
          const formData = new FormData();
          formData.append("policy", codePolicy);
          fetcher.submit(formData, { method: "PATCH" });
        }}
        variant="heavy"
      >
        保存
      </Button>
      <Button
        disabled={disabled || fetcher.state !== "idle" || codePolicy === policy}
        onClick={() => {
          // Reset the editor to the original policy
          setCodePolicy(policy);
        }}
      >
        放弃更改
      </Button>
    </div>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  if (
    isRouteErrorResponse(error) &&
    isApiError(error.data) &&
    error.data.rawData.includes("reading policy from path") &&
    error.data.rawData.includes("no such file or directory")
  ) {
    return (
      <div className="flex flex-col gap-4">
        <Card className="max-w-2xl" variant="flat">
          <div className="flex items-center justify-between gap-4">
            <Card.Title>ACL 策略不可用</Card.Title>
            <AlertCircle className="mb-2 h-6 w-6 text-red-500" />
          </div>
          <Card.Text>
            服务器上不存在策略文件，因此 ACL 策略暂不可用。这通常表示 Headscale 的 ACL 正以 <Code>file</Code> 模式运行，但指定的策略文件缺失。
          </Card.Text>
        </Card>
        <Card className="max-w-2xl" variant="flat">
          <Card.Text>
            您可以通过以下两种方式解决此问题：
          </Card.Text>
          <ul className="mt-2 ml-4 list-outside list-disc space-y-1 text-sm">
            <li>
              在 Headscale 配置指定的路径创建 ACL 策略文件。
            </li>
            <li>
              也可以修改 Headscale 配置，将 ACL 切换为 <Code>database</Code> 模式，以便 Headplane 直接通过网页界面管理 ACL 策略。
            </li>
          </ul>
        </Card>
      </div>
    );
  }

  return <PageError error={error} page="访问控制" />;
}
