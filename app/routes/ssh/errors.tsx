import { AlertCircle } from "lucide-react";

import Card from "~/components/card";
import Link from "~/components/link";

export const sshErrors = {
  wasm_missing: {
    title: "浏览器 SSH 不可用",
    message: "此 Headplane 构建未包含浏览器 SSH 支持。",
    anchor: "#ssh-not-available",
  },

  agent_required: {
    title: "浏览器 SSH 需要 Headplane 探针",
    message: "启用 Headplane 探针集成后，才能使用浏览器 SSH。",
    anchor: "#agent-required",
  },

  oidc_required: {
    title: "浏览器 SSH 需要 OIDC 认证",
    message: "启用 OIDC 认证后，才能使用浏览器 SSH。",
    anchor: "#oidc-required",
  },

  node_not_found: (hostname: string) => ({
    title: "未找到设备",
    message: `未找到主机名为 ${hostname} 的设备。`,
    anchor: "#node-not-found",
  }),

  user_not_linked: {
    title: "用户账号尚未关联",
    message:
      "使用浏览器 SSH 前，需要将账号关联到 Headscale 用户。",
    anchor: "#user-not-linked",
  },
} as const;

interface SSHErrorBoundaryProps {
  title: string;
  message: string;
  anchor: string;
}

export function isSSHError(error: unknown): error is SSHErrorBoundaryProps {
  return (
    typeof error === "object" &&
    error !== null &&
    "title" in error &&
    "message" in error &&
    "anchor" in error &&
    typeof error.title === "string" &&
    typeof error.message === "string" &&
    typeof error.anchor === "string"
  );
}

const DOCS_BASE = "https://headplane.net/features/ssh";

export function SSHErrorBoundary({ title, message, anchor }: SSHErrorBoundaryProps) {
  return (
    <Card className="w-screen" variant="flat">
      <div className="flex items-center justify-between gap-4">
        <Card.Title>{title}</Card.Title>
        <AlertCircle className="mb-2 h-6 w-6 text-red-500" />
      </div>
      <Card.Text>
        {message}
        <br />
        <br />
        <Link to={`${DOCS_BASE}${anchor}`} external styled>
          Headplane SSH 文档
        </Link>{" "}
      </Card.Text>
    </Card>
  );
}
