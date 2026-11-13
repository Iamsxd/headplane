import Dialog, { DialogPanel } from "~/components/dialog";
import Notice from "~/components/notice";
import Text from "~/components/text";
import Title from "~/components/title";

interface TransferOwnershipProps {
  targetHeadplaneUserId: string;
  targetDisplayName: string;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export default function TransferOwnership({
  targetHeadplaneUserId,
  targetDisplayName,
  isOpen,
  setIsOpen,
}: TransferOwnershipProps) {
  return (
    <Dialog isOpen={isOpen} onOpenChange={setIsOpen}>
      <DialogPanel variant="destructive">
        <Title>将所有权转移给 {targetDisplayName}？</Title>
        <Text className="mb-6">
          {targetDisplayName} 将成为此 Headplane 实例的新所有者，您的角色将降为管理员。此操作难以撤销。
        </Text>
        <Notice variant="warning">
          只有所有者可以转移所有权。转移后，您将无法再管理所有权。
        </Notice>
        <input name="action_id" type="hidden" value="transfer_ownership" />
        <input name="headplane_user_id" type="hidden" value={targetHeadplaneUserId} />
      </DialogPanel>
    </Dialog>
  );
}
