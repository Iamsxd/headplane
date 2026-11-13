import { CheckCircle, CircleSlash, Info, UserCircle } from "lucide-react";
import { useMemo, useState } from "react";
import { data } from "react-router";

import Attribute from "~/components/attribute";
import Button from "~/components/button";
import Card from "~/components/card";
import Chip from "~/components/chip";
import Link from "~/components/link";
import StatusCircle from "~/components/status-circle";
import Tooltip from "~/components/tooltip";
import {
  agentsContext,
  authContext,
  headscaleConfigContext,
  headscaleContext,
  headscaleLiveStoreContext,
  requestApiContext,
} from "~/server/context";
import { nodesResource, usersResource } from "~/server/headscale/live-store";
import { Capabilities } from "~/server/web/roles";
import cn from "~/utils/cn";
import { getOSInfo, getTSVersion } from "~/utils/host-info";
import { extractTagOwnerTags, isNoExpiry, mapNodes, sortAssignableTags } from "~/utils/node-info";
import { getUserDisplayName } from "~/utils/user";

import type { Route } from "./+types/machine";
import { mapTagsToComponents, uiTagsForNode } from "./components/machine-row";
import MenuOptions from "./components/menu";
import Routes from "./dialogs/routes";
import { machineAction } from "./machine-actions";

export async function loader({ request, params, context }: Route.LoaderArgs) {
  const agentsFeature = context.get(agentsContext);
  const auth = context.get(authContext);
  const getRequestApi = context.get(requestApiContext);
  const headscale = context.get(headscaleContext);
  const headscaleConfig = context.get(headscaleConfigContext);
  const headscaleLiveStore = context.get(headscaleLiveStoreContext);

  if (!params.id) {
    throw new Error("未提供设备 ID");
  }

  if (params.id.endsWith(".ico")) {
    throw data(null, { status: 204 });
  }

  const principal = await auth.require(request);

  if (!auth.can(principal, Capabilities.read_machines)) {
    throw new Error(
      "您没有权限查看此页面。请联系管理员。",
    );
  }

  const magic = headscaleConfig.getMagicDNSBaseDomain();

  const { api } = await getRequestApi(request);
  const [nodesSnap, usersSnap] = await Promise.all([
    headscaleLiveStore.get(nodesResource, api),
    headscaleLiveStore.get(usersResource, api),
  ]);
  const nodes = nodesSnap.data;
  const users = usersSnap.data;
  const node = nodes.find((node) => node.id === params.id);
  if (node == null) {
    throw data(null, { status: 404 });
  }

  const agents = agentsFeature.state === "enabled" ? agentsFeature.value : undefined;
  const [lookup, policyResult] = await Promise.allSettled([
    agents?.lookup([node.nodeKey]),
    api.policy.get(),
  ]);
  const stats = lookup.status === "fulfilled" ? lookup.value : undefined;
  const [enhancedNode] = mapNodes([node], stats);
  const tags = [...node.tags].toSorted();
  const supportsNodeOwnerChange = !headscale.capabilities.nodeOwnerIsImmutable;
  const supportsDisablingKeyExpiry = headscale.capabilities.keyExpiryCanBeDisabled;
  const agentSync = agents?.lastSync();
  const policy = policyResult.status === "fulfilled" ? policyResult.value.policy : undefined;

  return {
    agent: agentSync
      ? {
          syncedAt: agentSync.syncedAt?.toISOString() ?? null,
          nodeCount: agentSync.nodeCount,
          nodeKey: agents?.agentNodeKey(),
        }
      : undefined,
    existingTags: sortAssignableTags(nodes, policy),
    // `undefined` keeps the tag dialog from flagging every tag as undeclared.
    policyTags: extractTagOwnerTags(policy),
    magic,
    node: enhancedNode,
    stats: stats?.[enhancedNode.nodeKey],
    supportsNodeOwnerChange: supportsNodeOwnerChange,
    supportsDisablingKeyExpiry: supportsDisablingKeyExpiry,
    tags,
    users,
  };
}

export const action = machineAction;

export default function Page({
  loaderData: {
    node,
    tags,
    users,
    magic,
    agent,
    stats,
    existingTags,
    policyTags,
    supportsNodeOwnerChange,
    supportsDisablingKeyExpiry,
  },
}: Route.ComponentProps) {
  const [showRouting, setShowRouting] = useState(false);

  const uiTags = useMemo(() => {
    const tags = uiTagsForNode(node, agent?.nodeKey === node.nodeKey);
    return tags;
  }, [node, agent]);

  return (
    <div>
      <p className="text-md mb-8">
        <Link className="font-medium" to="/machines">
          所有设备
        </Link>
        <span className="mx-2">/</span>
        {node.givenName}
      </p>
      <div
        className={cn(
          "flex justify-between items-center pb-2",
          "border-b border-mist-100 dark:border-mist-800",
        )}
      >
        <span className="flex items-baseline gap-x-4 text-sm">
          <h1 className="text-2xl font-medium">{node.givenName}</h1>
          <StatusCircle className="h-4 w-4" isOnline={node.online} />
        </span>
        <MenuOptions
          existingTags={existingTags}
          policyTags={policyTags}
          isFullButton
          magic={magic}
          node={node}
          users={users}
          supportsNodeOwnerChange={supportsNodeOwnerChange}
          supportsDisablingKeyExpiry={supportsDisablingKeyExpiry}
        />
      </div>
      <div className="mb-4 flex gap-1">
        <div className="border-r border-mist-100 p-2 pr-4 dark:border-mist-800">
          <span className="flex items-center gap-x-1 text-sm text-mist-600 dark:text-mist-300">
            管理者
            <Tooltip content="默认情况下，设备的权限与其创建者的权限相同。">
              <Info className="p-1" />
            </Tooltip>
          </span>
          <div className="mt-1 flex items-center gap-x-2.5">
            <UserCircle />
            {node.user ? getUserDisplayName(node.user) : "由标签管理"}
          </div>
        </div>
        <div className="p-2 pl-4">
          <p className="text-sm text-mist-600 dark:text-mist-300">状态</p>
          <div className="mt-1 mb-8 flex gap-1">
            {mapTagsToComponents(node, uiTags)}
            {tags.map((tag) => (
              <Chip key={tag} text={tag} />
            ))}
          </div>
        </div>
      </div>
      <Routes isOpen={showRouting} node={node} setIsOpen={setShowRouting} />
      <h2 className="mt-8 text-xl font-medium">子网与路由</h2>
      <div className="mb-4 flex items-center justify-between">
        <p>
          子网功能可将物理网络的路由接入 Tailscale。{" "}
          <Link external styled to="https://tailscale.com/kb/1019/subnets">
            了解更多
          </Link>
        </p>
        <Button onClick={() => setShowRouting(true)}>审核</Button>
      </div>
      <Card
        className={cn(
          "w-full max-w-full grid sm:grid-cols-2",
          "md:grid-cols-4 gap-8 mr-2 text-sm mb-8",
        )}
        variant="flat"
      >
        <div>
          <span className="flex items-center gap-x-1 text-mist-600 dark:text-mist-300">
            已批准
            <Tooltip content="发往这些路由的流量将通过此设备转发。">
              <Info className="h-3.5 w-3.5" />
            </Tooltip>
          </span>
          <div className="mt-1">
            {node.customRouting.subnetApprovedRoutes.length === 0 ? (
              <span className="opacity-50">—</span>
            ) : (
              <ul className="leading-normal">
                {node.customRouting.subnetApprovedRoutes.map((route) => (
                  <li key={route}>{route}</li>
                ))}
              </ul>
            )}
          </div>
          <Button
            className="mt-1.5 px-1.5 py-0.5"
            onClick={() => setShowRouting(true)}
            variant="ghost"
          >
            编辑
          </Button>
        </div>
        <div>
          <span className="flex items-center gap-x-1 text-mist-600 dark:text-mist-300">
            等待批准
            <Tooltip content="此设备正在通告这些路由，但必须先批准，才能向其转发流量。">
              <Info className="h-3.5 w-3.5" />
            </Tooltip>
          </span>
          <div className="mt-1">
            {node.customRouting.subnetWaitingRoutes.length === 0 ? (
              <span className="opacity-50">—</span>
            ) : (
              <ul className="leading-normal">
                {node.customRouting.subnetWaitingRoutes.map((route) => (
                  <li key={route}>{route}</li>
                ))}
              </ul>
            )}
          </div>
          <Button
            className="mt-1.5 px-1.5 py-0.5"
            onClick={() => setShowRouting(true)}
            variant="ghost"
          >
            编辑
          </Button>
        </div>
        <div>
          <span className="flex items-center gap-x-1 text-mist-600 dark:text-mist-300">
            出口节点
            <Tooltip content="此设备是否可以作为您的 Tailnet 的出口节点。">
              <Info className="h-3.5 w-3.5" />
            </Tooltip>
          </span>
          <div className="mt-1">
            {node.customRouting.exitRoutes.length === 0 ? (
              <span className="opacity-50">—</span>
            ) : node.customRouting.exitApproved ? (
              <span className="flex items-center gap-x-1">
                <CheckCircle className="h-3.5 w-3.5 text-green-700" />
                已允许
              </span>
            ) : (
              <span className="flex items-center gap-x-1">
                <CircleSlash className="h-3.5 w-3.5 text-red-700" />
                等待批准
              </span>
            )}
          </div>
          <Button
            className="mt-1.5 px-1.5 py-0.5"
            onClick={() => setShowRouting(true)}
            variant="ghost"
          >
            编辑
          </Button>
        </div>
      </Card>
      <h2 className="text-xl font-medium">设备详情</h2>
      <p className="mb-4">
        此设备的网络信息，可用于排查连接问题。
      </p>
      <Card
        className="grid w-full max-w-full grid-cols-1 gap-y-2 sm:gap-x-12 lg:grid-cols-2"
        variant="flat"
      >
        <div className="flex flex-col gap-1">
          <Attribute
            name="创建者"
            value={node.user ? getUserDisplayName(node.user) : "由标签管理"}
          />
          <Attribute name="设备名称" value={node.givenName} />
          <Attribute
            name="操作系统主机名"
            tooltip="操作系统主机名由设备的操作系统提供，并用作设备的默认名称。"
            value={node.name}
          />
          {stats ? (
            <>
              <Attribute name="操作系统" value={getOSInfo(stats)} />
              <Attribute name="Tailscale 版本" value={getTSVersion(stats)} />
            </>
          ) : undefined}
          <Attribute
            name="ID"
            tooltip="此设备的 ID，用于 Headscale API。"
            value={node.id}
          />
          <Attribute
            isCopyable
            name="节点密钥"
            tooltip="用于唯一标识此设备的公钥。"
            value={node.nodeKey}
          />
          <Attribute name="创建时间" value={new Date(node.createdAt).toLocaleString("zh-CN")} />
          <Attribute
            name="最后在线"
            value={node.online ? "已连接" : new Date(node.lastSeen).toLocaleString("zh-CN")}
          />
          <Attribute
            name="密钥过期时间"
            value={!isNoExpiry(node.expiry) ? new Date(node.expiry!).toLocaleString("zh-CN") : "永不过期"}
          />
          {magic ? (
            <Attribute isCopyable name="域名" value={`${node.givenName}.${magic}`} />
          ) : undefined}
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold text-mist-600 uppercase dark:text-mist-300">
            地址
          </p>
          <Attribute
            isCopyable
            name="Tailscale IPv4"
            tooltip="此设备在您的 Tailnet（私有 Tailscale 网络）中的 IPv4 地址。"
            value={getIpv4Address(node.ipAddresses)}
          />
          <Attribute
            isCopyable
            name="Tailscale IPv6"
            tooltip="此设备在您的 Tailnet（私有 Tailscale 网络）中的 IPv6 地址。即使您的 ISP 不支持 IPv6，Tailnet 内部的连接也支持 IPv6。"
            value={getIpv6Address(node.ipAddresses)}
          />
          <Attribute
            isCopyable
            name="短域名"
            tooltip="您的 Tailnet 用户可以使用此 DNS 短名称访问此设备。"
            value={node.givenName}
          />
          {magic ? (
            <Attribute
              isCopyable
              name="完整域名"
              tooltip="您的 Tailnet 用户可以使用此 DNS 名称访问此设备。"
              value={`${node.givenName}.${magic}`}
            />
          ) : undefined}
          {stats?.Endpoints ? (
            <Attribute name="端点" value={stats?.Endpoints?.join("\n") ?? "—"} />
          ) : undefined}
          {stats ? (
            <>
              <p className="mt-4 text-sm font-semibold text-mist-600 uppercase dark:text-mist-300">
                客户端连接能力
              </p>
              <Attribute
                name="映射随目标变化"
                tooltip="此设备是否位于复杂的 NAT 后方，其映射的 IP 地址会随目标地址变化。"
                value={stats.NetInfo?.MappingVariesByDestIP ? "是" : "否"}
              />
              <Attribute
                name="NAT 回环"
                tooltip="此设备是否需要通过 NAT 回环进行穿透。"
                value={stats.NetInfo?.HairPinning ? "是" : "否"}
              />
              <Attribute name="IPv6" value={stats.NetInfo?.WorkingIPv6 ? "是" : "否"} />
              <Attribute name="UDP" value={stats.NetInfo?.WorkingUDP ? "是" : "否"} />
              <Attribute name="UPnP" value={stats.NetInfo?.UPnP ? "是" : "否"} />
              <Attribute name="PCP" value={stats.NetInfo?.PCP ? "是" : "否"} />
              <Attribute name="NAT-PMP" value={stats.NetInfo?.PMP ? "是" : "否"} />
            </>
          ) : undefined}
        </div>
      </Card>
    </div>
  );
}

function getIpv4Address(addresses: string[]) {
  for (const address of addresses) {
    if (address.startsWith("100.")) {
      // Return the first CGNAT address
      return address;
    }
  }

  return "—";
}

function getIpv6Address(addresses: string[]) {
  for (const address of addresses) {
    if (address.startsWith("fd")) {
      // Return the first IPv6 address
      return address;
    }
  }

  return "—";
}
