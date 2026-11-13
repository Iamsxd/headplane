import { AlertCircle, CloudOff } from "lucide-react";

import Card from "~/components/card";
import Code from "~/components/code";
import Link from "~/components/link";
import type { OidcErrorCode } from "~/server/oidc/provider";

export function OidcDiscoveryFailedNotice() {
  return (
    <Card className="m-4 mb-4 max-w-md border border-yellow-500 sm:m-0 sm:mb-4">
      <div className="flex items-center justify-between gap-4">
        <Card.Title className="text-yellow-500">单点登录暂不可用</Card.Title>
        <CloudOff className="mb-2 h-6 w-6 text-yellow-500" />
      </div>
      <Card.Text className="text-sm">
        无法连接身份提供方。连接恢复后即可使用单点登录，也可使用 API 密钥登录。
      </Card.Text>
    </Card>
  );
}

export function OidcConfigErrorNotice({ errors }: { errors: OidcErrorCode[] }) {
  return (
    <Card className="m-4 mb-4 max-w-md border border-red-500 sm:m-0 sm:mb-4">
      <div className="flex items-center justify-between gap-4">
        <Card.Title className="text-red-500">认证错误</Card.Title>
        <AlertCircle className="mb-2 h-6 w-6 text-red-500" />
      </div>
      <Card.Text className="text-sm">
        OpenID Connect（OIDC）单点登录（SSO）配置存在问题：{" "}
        <ul className="mt-2 mb-1 list-inside list-disc">
          {mapOidcErrorsToMessages(errors).map((code) => (
            <li key={code.key}>{code.node}</li>
          ))}
        </ul>{" "}
        <Link external styled to="https://headplane.net/features/sso#troubleshooting">
          了解详情
        </Link>
      </Card.Text>
    </Card>
  );
}

function mapOidcErrorsToMessages(errors: OidcErrorCode[]) {
  const messages: {
    key: string;
    node: React.ReactNode;
  }[] = [];

  for (const error of errors) {
    switch (error) {
      case "invalid_api_key": {
        messages.push({
          key: error,
          node: (
            <Card.Text className="inline">
              用于 OIDC 认证的 API 密钥无效。请确保{" "}
              <Code>headscale.api_key</Code> 为有效的 API 密钥。
            </Card.Text>
          ),
        });
        break;
      }

      case "missing_endpoints": {
        messages.push({
          key: error,
          node: (
            <Card.Text className="inline">
              OIDC 提供方缺少必需的端点。请确认发现地址正确，或在配置中手动指定端点。
            </Card.Text>
          ),
        });
        break;
      }

      case "discovery_failed": {
        messages.push({
          key: error,
          node: (
            <Card.Text className="inline">
              无法连接 OIDC 提供方进行发现。下次登录时会重试。
            </Card.Text>
          ),
        });
        break;
      }

      default: {
        messages.push({
          key: error,
          node: (
            <Card.Text className="inline">
              OIDC 配置出现未知错误，请查看 Headplane 日志了解详情。
            </Card.Text>
          ),
        });
        break;
      }
    }
  }

  return messages;
}
