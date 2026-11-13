import { Form } from "react-router";

import Button from "~/components/button";
import Card from "~/components/card";
import Code from "~/components/code";
import Input from "~/components/input";
import Link from "~/components/link";

interface UserPromptProps {
  hostname: string;
}

export default function UserPrompt({ hostname }: UserPromptProps) {
  return (
    <div className="flex h-screen items-center justify-center">
      <Card>
        <Card.Title>输入用户名</Card.Title>
        <Card.Text className="mb-4">
          请输入用于连接以下设备的用户名： <Code>{hostname}</Code>
          {". "}
          网页 SSH 遵循 Headscale 中相同的 SSH 访问规则，仅允许已授权的用户名。
          <br />
          <br />
          常见问题见{" "}
          <Link external styled to="https://headplane.net/features/ssh#troubleshooting">
            故障排查指南
          </Link>{" "}
          。
        </Card.Text>
        <Form
          method="GET"
          onSubmit={(e) => {
            const formData = new FormData(e.currentTarget);
            const username = formData.get("user");
            if (!username) {
              e.preventDefault();
              return;
            }

            // We have to do a full navigation, since the page needs a full
            // reload to initialize the SSH connection due to us disabling the
            // revalidator.
            const url = new URL(window.location.href);
            url.searchParams.set("user", username.toString());
            window.location.assign(url.toString());
          }}
        >
          <Input
            labelHidden
            type="text"
            label="用户名"
            name="user"
            placeholder="用户名"
            className="mb-2"
            required
          />
          <Button type="submit" variant="heavy" className="w-full">
            连接
          </Button>
        </Form>
      </Card>
    </div>
  );
}
