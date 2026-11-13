import Chip from "../chip";
import Tooltip from "../tooltip";

export interface ExpiryTagProps {
  variant: "expired" | "no-expiry";
  expiry?: string;
}

export function ExpiryTag({ variant, expiry }: ExpiryTagProps) {
  const formatter = new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Tooltip
      content={
        variant === "expired" ? (
          <>
            此设备已过期，无法连接网络。请在设备的 Tailscale 客户端中重新认证以恢复连接。
          </>
        ) : (
          <>此设备已关闭密钥到期，无需因密钥过期而重新认证。</>
        )
      }
    >
      <Chip
        text={
          variant === "expired" ? `已于 ${formatter.format(new Date(expiry!))} 过期` : "永不过期"
        }
        className="bg-mist-200 text-mist-800 dark:bg-mist-800 dark:text-mist-200"
      />
    </Tooltip>
  );
}
