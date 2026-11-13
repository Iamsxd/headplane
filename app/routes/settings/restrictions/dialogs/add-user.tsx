import { type } from "arktype";

import Button from "~/components/button";
import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Text from "~/components/text";
import Title from "~/components/title";
import { useForm } from "~/hooks/use-form";

const userSchema = type({
  user: "string > 0",
});

interface AddUserProps {
  users: string[];
  isDisabled?: boolean;
}

export default function AddUser({ users, isDisabled }: AddUserProps) {
  const form = useForm({
    schema: userSchema,
    validate: (values) => {
      const user = (values.user as string).trim();
      if (user.length === 0) return undefined;

      if (users.includes(user)) {
        return { user: "此用户已在列表中。" };
      }

      return undefined;
    },
  });

  return (
    <Dialog>
      <Button disabled={isDisabled}>添加用户</Button>
      <DialogPanel>
        <Title>添加用户</Title>
        <Text className="mb-4">
          将此用户加入允许的用户列表，以便通过 OIDC 登录 Headscale。
        </Text>
        <input name="action_id" type="hidden" value="add_user" />
        <Input
          {...form.field("user")}
          description="允许通过 OIDC 进行身份验证的用户。"
          required
          label="用户"
          placeholder="john_doe"
        />
      </DialogPanel>
    </Dialog>
  );
}
