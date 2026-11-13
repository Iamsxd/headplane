import { useEffect, useState } from "react";

import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Text from "~/components/text";
import Title from "~/components/title";
import { isValidHostName } from "~/utils/acl-policy";

interface HostDialogProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  name?: string;
  value?: string;
  existingNames: string[];
  onSave: (name: string, value: string) => void;
}

export default function HostDialog({
  isOpen,
  setIsOpen,
  name,
  value,
  existingNames,
  onSave,
}: HostDialogProps) {
  const [draftName, setDraftName] = useState(name ?? "");
  const [draftValue, setDraftValue] = useState(value ?? "");

  useEffect(() => {
    if (isOpen) {
      setDraftName(name ?? "");
      setDraftValue(value ?? "");
    }
  }, [isOpen, name, value]);

  const isDuplicate = draftName !== name && existingNames.includes(draftName);
  const nameIsInvalid = !isValidHostName(draftName) || isDuplicate;
  const valueIsInvalid = draftValue.trim().length === 0;

  return (
    <Dialog isOpen={isOpen} onOpenChange={setIsOpen}>
      <DialogPanel
        isDisabled={nameIsInvalid || valueIsInvalid}
        onSubmit={(event) => {
          event.preventDefault();
          onSave(draftName, draftValue.trim());
          setIsOpen(false);
        }}
      >
        <Title>{name ? `编辑主机 ${name}` : "新建主机"}</Title>
        <Text>
          主机条目为 IP 地址或 CIDR 网段命名，以便在规则中引用。
        </Text>
        <Input
          errorMessage={
            isDuplicate
              ? "同名主机已存在。"
              : "主机名只能包含小写字母、数字和连字符。"
          }
          invalid={nameIsInvalid}
          label="名称"
          onChange={setDraftName}
          placeholder="office"
          value={draftName}
        />
        <Input
          invalid={draftValue.length > 0 && valueIsInvalid}
          label="地址"
          onChange={setDraftValue}
          placeholder="100.64.0.0/24"
          value={draftValue}
        />
      </DialogPanel>
    </Dialog>
  );
}
