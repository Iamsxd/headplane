import cn from "~/utils/cn";

import Chip from "../chip";
import Tooltip from "../tooltip";

export function HeadplaneAgentTag() {
  return (
    <Tooltip content="此设备正在运行 Headplane Agent，可在管理后台提供主机信息。">
      <Chip
        text="Headplane Agent"
        className={cn("bg-purple-300 text-purple-900 dark:bg-purple-900 dark:text-purple-300")}
      />
    </Tooltip>
  );
}
