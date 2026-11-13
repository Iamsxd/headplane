import { type } from "arktype";

import Code from "~/components/code";
import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Text from "~/components/text";
import Title from "~/components/title";
import { useForm } from "~/hooks/use-form";
import type { Machine } from "~/types";

const renameSchema = type({
  name: "string > 0",
});

const dnsLabelPattern = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;

function validateMachineName(values: Record<string, unknown>) {
  const name = String(values.name ?? "").toLowerCase();
  if (!dnsLabelPattern.test(name)) {
    return {
      name: "请输入有效的 DNS 名称：仅允许小写字母、数字和连字符，且必须以字母或数字开头和结尾。",
    };
  }
}

interface RenameProps {
  machine: Machine;
  isOpen: boolean;
  magic?: string;
  setIsOpen: (isOpen: boolean) => void;
}

export default function Rename({ machine, magic, isOpen, setIsOpen }: RenameProps) {
  const form = useForm({
    schema: renameSchema,
    defaultValues: { name: machine.givenName },
    validate: validateMachineName,
  });
  const name = form.values.name as string;

  return (
    <Dialog isOpen={isOpen} onOpenChange={setIsOpen}>
      <DialogPanel isDisabled={!form.canSubmit}>
        <Title>编辑 {machine.givenName} 的设备名称</Title>
        <Text className="mb-6">
          此名称会显示在管理面板和 Tailscale 客户端中，并用于生成 MagicDNS 名称。
        </Text>
        <input name="action_id" type="hidden" value="rename" />
        <input name="node_id" type="hidden" value={machine.id} />
        <Input {...form.field("name")} required label="设备名称" placeholder="设备名称" />
        {magic ? (
          name.length > 0 && name !== machine.givenName ? (
            <p className="mt-2 text-sm leading-tight text-mist-600 dark:text-mist-300">
              此设备将可通过以下主机名访问：{" "}
              <Code className="text-sm">{name.toLowerCase().replaceAll(/\s+/g, "-")}</Code>
              {"。"}
              主机名 <Code className="text-sm">{machine.givenName}</Code> 将不再指向此设备。
            </p>
          ) : (
            <p className="mt-2 text-sm leading-tight text-mist-600 dark:text-mist-300">
              此设备可通过以下主机名访问：{" "}
              <Code className="text-sm">{machine.givenName}</Code>。
            </p>
          )
        ) : undefined}
      </DialogPanel>
    </Dialog>
  );
}
