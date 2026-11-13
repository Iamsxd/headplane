import Dialog, { DialogPanel } from "~/components/dialog";
import Input from "~/components/input";
import Text from "~/components/text";
import Title from "~/components/title";
import { User } from "~/types";
import { USERNAME_PATTERN, USERNAME_RULE } from "~/utils/user";

interface RenameProps {
  user: User;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export default function RenameUser({ user, isOpen, setIsOpen }: RenameProps) {
  return (
    <Dialog isOpen={isOpen} onOpenChange={setIsOpen}>
      <DialogPanel>
        <Title>重命名 {user.name || user.displayName}？</Title>
        <Text className="mb-6">
          为 {user.name || user.displayName} 输入新用户名。更改用户名不会同步更新 ACL 策略中对旧用户名的引用。
        </Text>
        <input name="action_id" type="hidden" value="rename_user" />
        <input name="headscale_user_id" type="hidden" value={user.id} />
        <Input
          defaultValue={user.name}
          description={USERNAME_RULE}
          minLength={2}
          pattern={USERNAME_PATTERN}
          required
          title={USERNAME_RULE}
          label="用户名"
          name="new_name"
          placeholder="my-new-name"
        />
      </DialogPanel>
    </Dialog>
  );
}
