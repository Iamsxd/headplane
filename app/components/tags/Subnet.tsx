import { Info } from "lucide-react";

import cn from "~/utils/cn";

import Chip from "../chip";
import Tooltip from "../tooltip";

export interface SubnetTagProps {
  isEnabled?: boolean;
}

export function SubnetTag({ isEnabled }: SubnetTagProps) {
  return (
    <Tooltip
      content={
        isEnabled ? (
          <>此设备正在发布子网路由。</>
        ) : (
          <>
            此设备有未发布的子网路由。请在设备菜单的“编辑路由设置…”中查看。
          </>
        )
      }
    >
      <Chip
        text="子网路由"
        className={cn("bg-blue-300 text-blue-900 dark:bg-blue-900 dark:text-blue-300")}
        rightIcon={isEnabled ? undefined : <Info className="h-full w-fit" />}
      />
    </Tooltip>
  );
}
