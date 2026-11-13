import { data } from "react-router";

import Link from "~/components/link";
import Notice from "~/components/notice";
import { authContext, headscaleConfigContext } from "~/server/context";
import { Capabilities } from "~/server/web/roles";

import type { Route } from "./+types/overview";
import { restrictionAction } from "./actions";
import AddDomain from "./dialogs/add-domain";
import AddGroup from "./dialogs/add-group";
import AddUser from "./dialogs/add-user";
import RestrictionTable from "./table";

export async function loader({ request, context }: Route.LoaderArgs) {
  const auth = context.get(authContext);
  const headscaleConfig = context.get(headscaleConfigContext);

  const principal = await auth.require(request);
  const check = auth.can(principal, Capabilities.read_users);
  if (!check) {
    throw data("您无权查看 IAM 设置。", {
      status: 403,
    });
  }

  const oidc = headscaleConfig.getOIDCConfig();
  if (!oidc) {
    throw data("此 Headscale 实例尚未配置 OIDC。", {
      status: 501,
    });
  }

  return {
    access: auth.can(principal, Capabilities.configure_iam),
    settings: {
      domains: [...new Set(oidc.allowedDomains)],
      groups: [...new Set(oidc.allowedGroups)],
      users: [...new Set(oidc.allowedUsers)],
    },
    writable: headscaleConfig.writable(),
  };
}

export const action = restrictionAction;

export default function Page({ loaderData: { access, writable, settings } }: Route.ComponentProps) {
  const isDisabled = writable ? !access : true;

  return (
    <div className="flex max-w-(--breakpoint-lg) flex-col gap-4">
      <div className="flex w-full flex-col sm:w-2/3">
        <p className="text-md mb-4">
          <Link className="font-medium" to="/settings">
            设置
          </Link>
          <span className="mx-2">/</span> 身份验证限制
        </p>
        {!access ? (
          <Notice title="身份验证权限受限" variant="warning">
            您无权编辑身份验证限制设置。请联系管理员申请权限，或请管理员修改这些设置。
          </Notice>
        ) : !writable ? (
          <Notice title="配置已锁定" variant="error">
            无法通过网页界面编辑 Headscale 配置文件。请确认已为 Headplane 正确授予该文件的写入权限。
          </Notice>
        ) : undefined}
        <h1 className="mt-4 mb-2 text-2xl font-medium">身份验证限制</h1>
        <p>
          Headscale 支持限制 OIDC 身份验证，仅允许指定邮箱域名、组或用户登录。您可以借此限定能够访问 Tailnet 的用户或组，Headplane 在验证身份时也会遵循这些设置。{" "}
          <Link external styled to="https://headscale.net/stable/ref/oidc/#basic-configuration">
            了解更多
          </Link>
        </p>
      </div>
      <RestrictionTable isDisabled={isDisabled} type="domain" values={settings.domains}>
        <AddDomain domains={settings.domains} isDisabled={isDisabled} />
      </RestrictionTable>
      <RestrictionTable isDisabled={isDisabled} type="group" values={settings.groups}>
        <AddGroup groups={settings.groups} isDisabled={isDisabled} />
      </RestrictionTable>
      <RestrictionTable isDisabled={isDisabled} type="user" values={settings.users}>
        <AddUser isDisabled={isDisabled} users={settings.users} />
      </RestrictionTable>
    </div>
  );
}
