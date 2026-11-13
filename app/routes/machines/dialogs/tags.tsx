import { AlertTriangle, Plus, TagsIcon, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useFetcher } from "react-router";

import Button from "~/components/button";
import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Link from "~/components/link";
import TableList from "~/components/table-list";
import Text from "~/components/text";
import Title from "~/components/title";
import type { Machine } from "~/types";
import cn from "~/utils/cn";

interface TagsProps {
  machine: Machine;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  existingTags?: string[];
  // Tags declared under `tagOwners`. Others are assignable but match no rule.
  policyTags?: string[];
}

export default function Tags({ machine, isOpen, setIsOpen, existingTags, policyTags }: TagsProps) {
  const fetcher = useFetcher();
  const submittingRef = useRef(false);
  const [tags, setTags] = useState([...machine.tags]);
  const [tag, setTag] = useState("tag:");
  const tagOptions = useMemo(
    () => (existingTags ?? []).filter((existingTag) => !tags.includes(existingTag)),
    [existingTags, tags],
  );
  const tagIsInvalid = useMemo(
    () => tag.length === 0 || !tag.startsWith("tag:") || tags.includes(tag),
    [tag, tags],
  );
  const undeclaredTags = useMemo(
    () => (policyTags === undefined ? [] : tags.filter((entry) => !policyTags.includes(entry))),
    [policyTags, tags],
  );

  const error = fetcher.data && !fetcher.data.success ? fetcher.data.error : null;

  useEffect(() => {
    if (fetcher.data?.success) {
      submittingRef.current = false;
      setIsOpen(false);
    }

    if (fetcher.state === "idle" && fetcher.data && !fetcher.data.success) {
      submittingRef.current = false;
    }
  }, [fetcher.data, fetcher.state]);

  useEffect(() => {
    if (isOpen) {
      setTags([...machine.tags]);
    }
  }, [isOpen]);

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open && submittingRef.current) {
          return;
        }
        setIsOpen(open);
      }}
    >
      <DialogPanel
        onSubmit={(event) => {
          event.preventDefault();
          submittingRef.current = true;
          const form = new FormData();
          form.set("action_id", "update_tags");
          form.set("node_id", machine.id);
          form.set("tags", tags.filter((t) => t !== "").join(","));
          fetcher.submit(form, { method: "POST" });
        }}
        isDisabled={fetcher.state !== "idle"}
      >
        <Title>编辑 {machine.givenName} 的 ACL 标签</Title>
        <Text>
          ACL 标签可用于在 ACL 策略中引用设备。请参阅{" "}
          <Link external styled to="https://tailscale.com/kb/1068/acl-tags">
            Tailscale 文档
          </Link>{" "}
          了解更多信息。
        </Text>
        {error ? (
          <p className="mt-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </p>
        ) : null}
        <TableList className="mt-4">
          {tags.length === 0 ? (
            <TableList.Item className="flex flex-col items-center gap-2.5 py-4 opacity-70">
              <TagsIcon />
              <p className="font-semibold">此设备尚未设置标签</p>
            </TableList.Item>
          ) : (
            tags.map((item) => (
              <TableList.Item className="font-mono" id={item} key={item}>
                <span className="flex items-center gap-1.5">
                  {item}
                  {undeclaredTags.includes(item) ? (
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                  ) : null}
                </span>
                <Button
                  className="rounded-md p-0.5"
                  onClick={() => {
                    setTags(tags.filter((tag) => tag !== item));
                  }}
                  type="button"
                >
                  <X className="p-1" />
                </Button>
              </TableList.Item>
            ))
          )}
        </TableList>

        <div className="mt-2 flex items-center gap-2">
          <Input
            aria-label="添加标签"
            className="w-full"
            value={tag}
            onChange={setTag}
            invalid={tag.length > 0 && tagIsInvalid}
            placeholder="tag:example"
            label="标签"
            labelHidden
          />
          <Button
            className={cn("rounded-md p-1", tagIsInvalid && "opacity-50 cursor-not-allowed")}
            disabled={tagIsInvalid}
            onClick={() => {
              setTags([...tags, tag]);
              setTag("tag:");
            }}
            type="button"
          >
            <Plus className="p-1" size={30} />
          </Button>
        </div>
        {tagOptions.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {tagOptions.map((option) => (
              <Button
                className="px-2 py-1 font-mono text-xs"
                key={option}
                onClick={() => setTags([...tags, option])}
                type="button"
                variant="ghost"
              >
                {option}
              </Button>
            ))}
          </div>
        ) : null}
        {undeclaredTags.length > 0 ? (
          <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
            {undeclaredTags.join(", ")} {undeclaredTags.length === 1 ? "未" : "均未"}在策略的
            <code className="font-mono">tagOwners</code> 中声明，因此没有规则会匹配{" "}
            {undeclaredTags.length === 1 ? "该标签" : "这些标签"}。请将{" "}
            {undeclaredTags.length === 1 ? "该标签" : "这些标签"}添加到{" "}
            <Link styled to="/acls">
              访问控制
            </Link>
            中。
          </p>
        ) : null}
        <p className="mt-2 text-sm opacity-50">
          找不到需要的标签？请先在访问控制策略中定义标签，然后再将其分配给设备。
        </p>
      </DialogPanel>
    </Dialog>
  );
}
