import { type } from "arktype";
import { Split } from "lucide-react";

import Button from "~/components/button";
import Chip from "~/components/chip";
import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Switch from "~/components/switch";
import Text from "~/components/text";
import Title from "~/components/title";
import Tooltip from "~/components/tooltip";
import { useForm } from "~/hooks/use-form";
import cn from "~/utils/cn";

const nsSchema = type({
  ns: "string.ip",
  split_name: "string > 0",
});

interface Props {
  nameservers: Record<string, string[]>;
}

export default function AddNameserver({ nameservers }: Props) {
  const form = useForm({
    schema: nsSchema,
    defaultValues: { split_name: "global" },
    validate: (values) => {
      const ns = values.ns as string;
      const domain = values.split_name as string;
      if (!ns) return undefined;

      const isSplit = domain !== "global";
      const isDuplicate = isSplit
        ? nameservers[domain]?.includes(ns)
        : Object.values(nameservers).some((nsList) => nsList.includes(ns));

      if (isDuplicate) {
        return { ns: "此 DNS 服务器已存在。" };
      }

      return undefined;
    },
  });
  const split = (form.values.split_name as string) !== "global";

  return (
    <Dialog onOpenChange={(isOpen) => !isOpen && form.reset()}>
      <Button>添加 DNS 服务器</Button>
      <DialogPanel>
        <Title className="mb-4">添加 DNS 服务器</Title>
        <input name="action_id" type="hidden" value="add_ns" />
        <Input
          {...form.field("ns")}
          description="使用此 IPv4 或 IPv6 地址解析域名。"
          required
          label="DNS 服务器"
          placeholder="1.2.3.4"
        />
        <div className="mt-8 flex items-center justify-between">
          <div className="block">
            <div className="inline-flex items-center gap-2">
              <Text className="font-semibold">限制到指定域名</Text>
              <Tooltip content="只有支持分流 DNS 的客户端（大多数平台为 Tailscale v1.8 或更高版本）才会使用此 DNS 服务器，旧版客户端会忽略它。">
                <Chip
                  className={cn("inline-flex items-center")}
                  leftIcon={<Split className="mr-0.5 h-3 w-3" />}
                  text="分流 DNS"
                />
              </Tooltip>
            </div>
            <Text className="text-sm">此 DNS 服务器仅用于部分域名。</Text>
          </div>
          <Switch
            label="分流 DNS"
            checked={split}
            onCheckedChange={(checked) => {
              form.setValue("split_name", checked ? "" : "global");
            }}
          />
        </div>
        {split ? (
          <>
            <Text className="mt-8 font-semibold">域名</Text>
            <Input
              {...form.field("split_name")}
              required
              label="域名"
              placeholder="example.com"
            />
            <Text className="text-sm">
              仅匹配此后缀的单标签查询或完全限定域名查询才使用此 DNS 服务器。
            </Text>
          </>
        ) : (
          <input name="split_name" type="hidden" value="global" />
        )}
      </DialogPanel>
    </Dialog>
  );
}
