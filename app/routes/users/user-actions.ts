import { data } from "react-router";

import { authContext, headscaleLiveStoreContext, requestApiContext } from "~/server/context";
import { isDataWithApiError } from "~/server/headscale/api/error-client";
import { usersResource } from "~/server/headscale/live-store";
import { isUserPrincipal } from "~/server/web/auth";
import { Capabilities } from "~/server/web/roles";
import type { Role } from "~/server/web/roles";
import { isValidGroupName, parsePolicy, serializePolicy, setUserGroups } from "~/utils/acl-policy";
import { validateUsername } from "~/utils/user";

import type { Route } from "./+types/overview";

export async function userAction({ request, context }: Route.ActionArgs) {
  const auth = context.get(authContext);
  const getRequestApi = context.get(requestApiContext);
  const headscaleLiveStore = context.get(headscaleLiveStoreContext);

  const principal = await auth.require(request);
  const check = await auth.can(principal, Capabilities.write_users);
  if (!check) {
    throw data("您无权修改用户", {
      status: 403,
    });
  }

  const formData = await request.formData();
  const action = formData.get("action_id")?.toString();
  if (!action) {
    throw data("表单数据缺少 `action_id`。", {
      status: 404,
    });
  }

  const { api } = await getRequestApi(request);
  switch (action) {
    case "create_user": {
      const name = formData.get("username")?.toString();
      const displayName = formData.get("display_name")?.toString();
      const email = formData.get("email")?.toString();

      if (!name) {
        throw data("表单数据缺少 `username`。", {
          status: 400,
        });
      }

      const nameError = validateUsername(name);
      if (nameError) {
        throw data(nameError, { status: 400 });
      }

      await api.users.create({ name, email, displayName });
      await headscaleLiveStore.refresh(usersResource, api);
      return { message: "用户创建成功" };
    }
    case "delete_user": {
      const headscaleUserId = formData.get("headscale_user_id")?.toString();
      if (!headscaleUserId) {
        throw data("表单数据缺少 `headscale_user_id`。", {
          status: 400,
        });
      }

      await api.users.delete(headscaleUserId);
      for (const user of await auth.listUsers()) {
        if (user.headscale_user_id === headscaleUserId) {
          await auth.unlinkHeadscaleUser(user.id);
        }
      }

      await headscaleLiveStore.refresh(usersResource, api);
      return { message: "用户删除成功" };
    }
    case "rename_user": {
      const headscaleUserId = formData.get("headscale_user_id")?.toString();
      const newName = formData.get("new_name")?.toString();
      if (!headscaleUserId || !newName) {
        return data({ success: false }, 400);
      }

      const newNameError = validateUsername(newName);
      if (newNameError) {
        throw data(newNameError, { status: 400 });
      }

      const users = await api.users.list({ id: headscaleUserId });
      const user = users.find((user) => user.id === headscaleUserId);
      if (!user) {
        throw data(`未找到 ID 为 ${headscaleUserId} 的用户`, { status: 400 });
      }

      if (user.provider === "oidc") {
        // OIDC users cannot be renamed via this endpoint, return an error
        throw data("无法重命名由 OIDC 管理的用户", {
          status: 403,
        });
      }

      await api.users.rename(headscaleUserId, newName);
      await headscaleLiveStore.refresh(usersResource, api);
      return { message: "用户重命名成功" };
    }
    case "reassign_user": {
      const headplaneUserId = formData.get("headplane_user_id")?.toString();
      const newRole = formData.get("new_role")?.toString();
      if (!headplaneUserId || !newRole) {
        throw data("表单数据缺少 `headplane_user_id` 或 `new_role`。", {
          status: 400,
        });
      }

      const result = await auth.reassignUser(headplaneUserId, newRole as Role);
      if (!result) {
        throw data("更改用户角色失败。", { status: 500 });
      }

      return { message: "用户角色更改成功" };
    }
    case "transfer_ownership": {
      if (!isUserPrincipal(principal) || principal.user.role !== "owner") {
        throw data("只有所有者可以转移所有权。", { status: 403 });
      }

      const headplaneUserId = formData.get("headplane_user_id")?.toString();
      if (!headplaneUserId) {
        throw data("表单数据缺少 `headplane_user_id`。", { status: 400 });
      }

      const result = await auth.transferOwnership(principal.user.id, headplaneUserId);
      if (!result) {
        throw data("转移所有权失败。", { status: 500 });
      }

      return { message: "所有权转移成功" };
    }
    case "link_user": {
      const headplaneUserId = formData.get("headplane_user_id")?.toString();
      const headscaleUserId = formData.get("headscale_user_id")?.toString();
      if (!headplaneUserId || !headscaleUserId) {
        throw data("表单数据缺少 `headplane_user_id` 或 `headscale_user_id`。", {
          status: 400,
        });
      }

      const linked = await auth.linkHeadscaleUser(headplaneUserId, headscaleUserId);
      if (!linked) {
        throw data("该 Headscale 用户已关联其他账户。", { status: 409 });
      }

      return { message: "Headscale 用户关联成功" };
    }
    case "update_user_groups": {
      // Group membership lives in the policy, so `write_policy` is needed too.
      if (!auth.can(principal, Capabilities.write_policy)) {
        throw data("您无权修改 ACL 策略", { status: 403 });
      }

      const userName = formData.get("user_name")?.toString();
      if (!userName) {
        throw data("表单数据缺少 `user_name`。", { status: 400 });
      }

      const groups = (formData.get("groups")?.toString() ?? "")
        .split(",")
        .map((group) => group.trim())
        .filter((group) => group.length > 0);

      const invalid = groups.filter((group) => !isValidGroupName(group));
      if (invalid.length > 0) {
        return data({ error: `无效的组名：${invalid.join(", ")}` }, 400);
      }

      const { policy } = await api.policy.get();
      const parsed = parsePolicy(policy);
      if (!parsed.ok) {
        return data({ error: `无法解析 ACL 策略：${parsed.error}` }, 400);
      }

      try {
        await api.policy.set(serializePolicy(setUserGroups(parsed.policy, userName, groups)));
      } catch (error) {
        // Headscale refuses the write in `file` mode. The UI hides the action
        // then, but a stale page can still reach this point.
        const message = isDataWithApiError(error) ? error.data.rawData : String(error);
        if (message.includes("update is disabled")) {
          return data(
            {
              error:
                "ACL 策略为只读。请在 Headscale 配置中将 `policy.mode` 设置为 `database`，以便编辑组。",
            },
            403,
          );
        }

        return data({ error: `无法更新 ACL 策略：${message}` }, 500);
      }

      return { message: "组更新成功" };
    }
    default:
      throw data("提供的 `action_id` 无效。", {
        status: 400,
      });
  }
}
