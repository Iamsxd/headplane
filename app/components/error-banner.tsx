import { AlertCircle } from "lucide-react";
import { isRouteErrorResponse } from "react-router";

import { isApiError, isConnectionError } from "~/server/headscale/api/error-client";
import cn from "~/utils/cn";

import Card from "./card";
import Code from "./code";
import Link from "./link";

export function getErrorMessage(error: Error | unknown): {
  title: string;
  jsxMessage: React.ReactNode;
} {
  if (isRouteErrorResponse(error)) {
    if (isApiError(error.data)) {
      const { statusCode, rawData, data, requestUrl } = error.data;
      if (statusCode >= 500) {
        return {
          jsxMessage: (
            <>
              <Card.Text>
                与 Headscale API 通信时出错。
                <br />
                服务器返回的状态码为 <strong>{statusCode}</strong>，表示服务端出现问题。请检查 Headscale 服务状态后重试。
              </Card.Text>
              {(error.data.data != null || error.data.rawData != null) && (
                <pre className="mt-2 overflow-x-auto rounded-lg bg-mist-100 p-2 dark:bg-mist-800">
                  {error.data.data != null ? (
                    <code>{JSON.stringify(error.data.data, null, 2)}</code>
                  ) : (
                    <code>{error.data.rawData}</code>
                  )}
                </pre>
              )}
            </>
          ),
          title: "Headscale API 错误",
        };
      }

      const authError = error.data.statusCode === 401 || error.data.statusCode === 403;

      return {
        jsxMessage: (
          <>
            <Card.Text className="leading-snug">
              Headscale API 返回了异常响应。
              {authError ? (
                <>
                  {" "}
                  状态码表示认证失败。请检查 API 密钥及 Headplane 配置。
                </>
              ) : (
                <> 可能是 Headscale 版本不受支持，也可能是软件缺陷。</>
              )}
            </Card.Text>
            <ul className="mt-2 list-inside list-disc">
              <li>
                请求地址： <Code>{requestUrl}</Code>
              </li>
              <li>
                状态码：{" "}
                <Code>
                  {/* @ts-expect-error */}
                  {data === null ? (
                    <>
                      {statusCode} {rawData}
                    </>
                  ) : (
                    <>
                      {statusCode} {error.statusText}
                    </>
                  )}
                </Code>
              </li>
            </ul>
            <Card.Text className="mt-4 text-lg font-semibold">错误详情</Card.Text>
            <pre className="mt-2 overflow-x-auto rounded-lg bg-mist-100 p-2 dark:bg-mist-800">
              <code>{JSON.stringify(error.data, null, 2)}</code>
            </pre>
          </>
        ),
        title: "Headscale API 响应异常",
      };
    }

    if (isConnectionError(error.data)) {
      const { requestUrl, errorCode, errorMessage, extraData } = error.data;
      return {
        jsxMessage: (
          <>
            <Card.Text className="leading-snug">
              Headplane 无法访问 Headscale API。请检查网络和配置，确保两者能够连接。
            </Card.Text>
            <Card.Text className="mt-4 text-lg font-semibold">错误详情</Card.Text>
            <pre className="mt-2 overflow-x-auto rounded-lg bg-mist-100 p-2 dark:bg-mist-800">
              {requestUrl}
              <br />
              {errorCode}: {errorMessage}
              {extraData != null && (
                <>
                  <br />
                  <br />
                  <code>{JSON.stringify(extraData, null, 2)}</code>
                </>
              )}
            </pre>
          </>
        ),
        title: "无法连接 Headscale API",
      };
    }

    return {
      jsxMessage: (
        <>
          处理请求时出错。
          <br />
          状态码： <strong>{error.status}</strong>
          <br />
          状态说明： <strong>{error.data}</strong>
        </>
      ),
      title: `错误 ${error.status}`,
    };
  }

  if (!(error instanceof Error)) {
    return {
      jsxMessage: (
        <>
          <Card.Text>
            发生了未知错误，可能是软件缺陷。请在{" "}
            <Link external styled to="https://github.com/tale/headplane/issues">
              Headplane GitHub
            </Link>{" "}
            仓库提交问题，并附上下方详情。
          </Card.Text>
          <Card.Text className="mt-4 text-lg font-semibold">错误详情</Card.Text>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-mist-100 p-2 dark:bg-mist-800">
            <code>{JSON.stringify(error, null, 2)}</code>
          </pre>
        </>
      ),
      title: "未知错误",
    };
  }

  // Traverse the error chain to find the root cause
  let rootError = error;
  if (error.cause != null) {
    rootError = error.cause as Error;
    while (rootError.cause != null) {
      rootError = rootError.cause as Error;
    }
  }

  // TODO: If we are aggregate, concat into a single message
  if (rootError instanceof AggregateError) {
    throw new Error("AggregateError handling not implemented yet");
  }

  return {
    jsxMessage: rootError.message,
    title:
      rootError.name.length > 0 && rootError.name !== "Error"
        ? `错误：${rootError.name}`
        : "错误",
  };
}

interface ErrorBannerProps {
  error: unknown;
  className?: string;
}

export function ErrorBanner({ error, className }: ErrorBannerProps) {
  const { title, jsxMessage } = getErrorMessage(error);

  return (
    <Card className={cn("w-screen", className)} variant="flat">
      <div className="flex items-center justify-between gap-4">
        <Card.Title>{title}</Card.Title>
        <AlertCircle className="mb-2 h-6 w-6 text-red-500" />
      </div>
      {jsxMessage}
    </Card>
  );
}
