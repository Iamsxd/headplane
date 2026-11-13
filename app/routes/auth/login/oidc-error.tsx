import { AlertCircle } from "lucide-react";

import Card from "~/components/card";
import Code from "~/components/code";

export function OidcErrorNotice({ code }: { code: string }) {
  return (
    <Card className="m-4 mb-4 max-w-md border border-red-500 sm:m-0 sm:mb-4">
      <div className="flex items-center justify-between gap-4">
        <Card.Title className="text-red-500">配置问题</Card.Title>
        <AlertCircle className="mb-2 h-6 w-6 text-red-500" />
      </div>
      {getErrorMessage(code)}
    </Card>
  );
}

function getErrorMessage(code: string) {
  switch (code) {
    case "error_no_query":
      return (
        <Card.Text>
          单点登录提供方未携带必需的参数返回 Headplane，请检查提供方的配置。
        </Card.Text>
      );

    case "error_no_session":
    case "error_invalid_session":
      return (
        <Card.Text>
          会话数据缺失或无效，无法完成单点登录。请检查 Headplane 的 Cookie 配置，并允许浏览器接收 Cookie。
        </Card.Text>
      );

    case "error_no_sub":
      return (
        <Card.Text>
          单点登录提供方未返回有效的用户标识，请确保其正确提供 <Code>sub</Code> 声明。
        </Card.Text>
      );

    case "error_auth_failed":
      return (
        <Card.Text>
          向单点登录提供方认证失败，请稍后重试。更多信息见 Headplane 日志。
        </Card.Text>
      );

    default:
      return (
        <Card.Text>
          OIDC 认证时发生未知错误，请稍后重试。
        </Card.Text>
      );
  }
}
