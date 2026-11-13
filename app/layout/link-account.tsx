import { Form } from "react-router";

import Button from "~/components/button";
import Card from "~/components/card";
import cn from "~/utils/cn";

interface LinkAccountProps {
  headscaleUsers: { id: string; name: string }[];
}

export default function LinkAccount({ headscaleUsers }: LinkAccountProps) {
  return (
    <div className="mx-auto mt-6 flex max-w-xl flex-col items-center justify-center py-36">
      <Card variant="flat" className="max-w-xl items-center gap-4">
        <Card.Title>关联 Headscale 账号</Card.Title>
        <Card.Text>
          Headplane 无法自动将你的单点登录身份匹配到已有 Headscale 用户。请从下方列表选择用户，关联账号后继续。
        </Card.Text>
        <Form method="POST" className="mt-4">
          <select
            className={cn(
              "mb-4 w-full rounded-lg border p-2",
              "border-mist-200 dark:border-mist-700",
              "bg-mist-50 dark:bg-mist-900",
            )}
            name="headscale_user_id"
            required
          >
            <option value="">选择用户…</option>
            {headscaleUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
          <Button className="w-full" type="submit" variant="heavy">
            关联并继续
          </Button>
        </Form>
        <Card.Text className="mt-8 text-center text-xs text-mist-600 dark:text-mist-300">
          如果列表中没有你的用户，请联系管理员。如需自动关联新用户，请确保 Headscale 用户的邮箱与单点登录身份的邮箱一致。
        </Card.Text>
      </Card>
    </div>
  );
}
