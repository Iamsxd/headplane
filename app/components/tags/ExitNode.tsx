import { Info } from "lucide-react";

import cn from "~/utils/cn";

import Chip from "../chip";
import Tooltip from "../tooltip";

export interface ExitNodeTagProps {
  isEnabled?: boolean;
}

export function ExitNodeTag({ isEnabled }: ExitNodeTagProps) {
  return (
    <Tooltip
      content={
        isEnabled ? (
          <>此设备正在作为出口节点使用。</>
        ) : (
          <>
            此设备申请作为出口节点。请在设备菜单的“编辑路由设置…”中审核。
          </>
        )
      }
    >
      <Chip
        text="出口节点"
        className={cn("bg-blue-300 text-blue-900 dark:bg-blue-900 dark:text-blue-300")}
        rightIcon={isEnabled ? undefined : <Info className="h-full w-fit" />}
      />
    </Tooltip>
  );
}
