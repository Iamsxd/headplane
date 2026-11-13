import { ArrowRight } from "lucide-react";

import Link from "~/components/link";
import PageError from "~/components/page-error";
import { headscaleConfigContext } from "~/server/context";

import type { Route } from "./+types/overview";

export async function loader({ context }: Route.LoaderArgs) {
  const headscaleConfig = context.get(headscaleConfigContext);

  return {
    config: headscaleConfig.writable(),
    hasOidcConfig: headscaleConfig.hasOIDCConfig(),
  };
}

export default function Page({ loaderData: { config, hasOidcConfig } }: Route.ComponentProps) {
  return (
    <div className="flex max-w-(--breakpoint-lg) flex-col gap-8">
      <div className="flex w-full flex-col sm:w-2/3">
        <h1 className="mb-4 text-2xl font-medium">设置</h1>
        <p>
          设置页面仍在完善中，后续功能将陆续添加到此处。如需其他功能，欢迎在 GitHub 仓库提交 issue。
        </p>
      </div>
      <div className="flex w-full flex-col sm:w-2/3">
        <h1 className="mb-4 text-2xl font-medium">预认证密钥</h1>
        <p>
          Headscale 完整支持预认证密钥，方便您将设备加入 Tailnet。有关预认证密钥的使用方法，请参阅{" "}
          <Link external styled to="https://tailscale.com/kb/1085/auth-keys/">
            Tailscale 文档
          </Link>
        </p>
      </div>
      <Link to="/settings/auth-keys">
        <div className="flex items-center text-lg font-medium">
          管理认证密钥
          <ArrowRight className="ml-2 h-5 w-5" />
        </div>
      </Link>
      <div className="flex w-full flex-col sm:w-2/3">
        <h1 className="mb-4 text-2xl font-medium">Headplane Agent</h1>
        <p>
          Headplane Agent 会同步 Tailnet 中节点的操作系统版本、连接详情等信息。
        </p>
      </div>
      <Link to="/settings/agent">
        <div className="flex items-center text-lg font-medium">
          Agent 设置
          <ArrowRight className="ml-2 h-5 w-5" />
        </div>
      </Link>
      {config && hasOidcConfig ? (
        <>
          <div className="flex w-full flex-col sm:w-2/3">
            <h1 className="mb-4 text-2xl font-medium">身份验证限制</h1>
            <p>
              Headscale 支持限制 OIDC 身份验证，仅允许指定邮箱域名、组或用户登录。您可以借此限定能够访问 Tailnet 的用户或组，Headplane 在验证身份时也会遵循这些设置。{" "}
              <Link external styled to="https://headscale.net/stable/ref/oidc/#basic-configuration">
                了解更多
              </Link>
            </p>
          </div>
          <Link to="/settings/restrictions">
            <div className="flex items-center text-lg font-medium">
              管理限制
              <ArrowRight className="ml-2 h-5 w-5" />
            </div>
          </Link>
        </>
      ) : undefined}
    </div>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  return <PageError error={error} page="设置" />;
}
