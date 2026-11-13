import cn from "~/utils/cn";

import Chip from "../chip";
import Tooltip from "../tooltip";

export function TailscaleSSHTag() {
  return (
    <Tooltip content="此设备已启用 Tailscale SSH，可使用 Tailscale 账号验证 SSH 访问，并通过 Headplane 管理后台连接。">
      <Chip
        text="Tailscale SSH"
        className={cn("bg-lime-500 text-lime-900 dark:bg-lime-900 dark:text-lime-500")}
      />
    </Tooltip>
  );
}
