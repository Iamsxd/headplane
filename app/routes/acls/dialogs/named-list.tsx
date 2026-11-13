import { useEffect, useState } from "react";

import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Text from "~/components/text";
import Title from "~/components/title";
import TokenList from "~/components/token-list";
import { isValidGroupName, isValidTagName } from "~/utils/acl-policy";

export type NamedListKind = "group" | "tag";

interface NamedListDialogProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  kind: NamedListKind;
  // Present when editing, absent when creating a new entry.
  name?: string;
  members?: string[];
  existingNames: string[];
  suggestions: string[];
  onSave: (name: string, members: string[]) => void;
}

const COPY = {
  group: {
    title: "组",
    prefix: "group:",
    field: "成员",
    fieldDescription: "属于此组的 Headscale 用户。",
    empty: "暂无成员",
    placeholder: "alice@",
    validate: isValidGroupName,
    hint: "组名必须以 group: 开头，且只能包含小写字母、数字和连字符。",
  },
  tag: {
    title: "标签",
    prefix: "tag:",
    field: "标签所有者",
    fieldDescription: "允许将此标签分配给节点的用户和组。",
    empty: "暂无所有者",
    placeholder: "group:ops",
    validate: isValidTagName,
    hint: "标签名必须以 tag: 开头，且只能包含小写字母、数字和连字符。",
  },
} as const;

export default function NamedListDialog({
  isOpen,
  setIsOpen,
  kind,
  name,
  members,
  existingNames,
  suggestions,
  onSave,
}: NamedListDialogProps) {
  const copy = COPY[kind];
  const [draftName, setDraftName] = useState(name ?? copy.prefix);
  const [draftMembers, setDraftMembers] = useState<string[]>(members ?? []);

  useEffect(() => {
    if (isOpen) {
      setDraftName(name ?? copy.prefix);
      setDraftMembers(members ? [...members] : []);
    }
  }, [isOpen, name, members, copy.prefix]);

  const trimmedName = draftName.trim();
  const isDuplicate = trimmedName !== name && existingNames.includes(trimmedName);
  const nameIsInvalid = !copy.validate(trimmedName) || isDuplicate;
  // The field opens pre-filled with the `group:`/`tag:` prefix, which is not a
  // valid name yet. Saving stays blocked, but nothing is flagged until it is edited.
  const isPristine = trimmedName.length === 0 || trimmedName === copy.prefix;
  const showNameError = !isPristine && nameIsInvalid;

  return (
    <Dialog isOpen={isOpen} onOpenChange={setIsOpen}>
      <DialogPanel
        isDisabled={nameIsInvalid}
        onSubmit={(event) => {
          event.preventDefault();
          onSave(trimmedName, draftMembers);
          setIsOpen(false);
        }}
      >
        <Title>{name ? `编辑${copy.title} ${name}` : `新建${copy.title}`}</Title>
        <Text>{copy.hint}</Text>
        <Input
          errorMessage={isDuplicate ? `同名${copy.title}已存在。` : copy.hint}
          invalid={showNameError}
          label="名称"
          onChange={setDraftName}
          placeholder={`${copy.prefix}example`}
          value={draftName}
        />
        <TokenList
          description={copy.fieldDescription}
          emptyText={copy.empty}
          label={copy.field}
          onChange={setDraftMembers}
          placeholder={copy.placeholder}
          suggestions={suggestions}
          values={draftMembers}
        />
      </DialogPanel>
    </Dialog>
  );
}
