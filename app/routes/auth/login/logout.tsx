import { Link as RouterLink } from "react-router";

import Button from "~/components/button";
import Card from "~/components/card";

export default function Logout() {
  return (
    <div className="flex h-screen w-screen items-center justify-center">
      <Card className="m-4 max-w-md sm:m-0">
        <Card.Title>你已退出登录</Card.Title>
        <Card.Text>现在可以关闭此窗口。</Card.Text>
        <RouterLink to="/login" prefetch="none" reloadDocument>
          <Button className="mt-8 w-full" variant="heavy">
            重新登录
          </Button>
        </RouterLink>
      </Card>
    </div>
  );
}
