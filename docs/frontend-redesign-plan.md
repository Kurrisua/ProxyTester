# ProxyTester 前端彻底重构规划

> 本文档用于规划 ProxyTester 前端从“代理池列表看板”重构为“代理安全研究与行为分析平台”的设计方案。  
> 当前阶段只做规划，不修改前端代码。  
> 最后更新：2026-04-17

## 1. 重构结论

当前前端不建议在原有 `App.tsx` 上继续堆功能。

原因是下一阶段前端承载的内容已经发生根本变化：过去主要展示代理是否可用、响应速度、协议和基础评分；后续要展示代理是否存在内容篡改、资源替换、脚本注入、MITM、中间人证书异常、隐蔽触发行为、多轮检测历史、漏斗式检测路径和证据链。

这不是简单增加几个表格列能解决的。前端需要重新设计信息架构、页面结构、数据模型和组件边界。

建议目标：

> 将前端重构为一个面向安全研究的分析控制台，既能管理代理池，也能解释每个代理为什么正常、可疑或恶意。

## 2. 当前前端问题分析

### 2.1 结构问题

当前 `daili/src` 目录很轻：

1. `App.tsx`
2. `types.ts`
3. `constants.ts`
4. `index.css`
5. `lib/api.ts`
6. `lib/utils.ts`

主要问题：

1. 大量组件、页面、状态、表格、筛选和业务逻辑集中在 `App.tsx`。
2. 目前没有明确的页面目录、组件目录、特性模块目录。
3. API 调用没有按业务域拆分。
4. 类型定义只覆盖基础代理池，不覆盖安全检测、批次、事件、证据、漏斗阶段。
5. 前端没有路由层面的信息架构。

### 2.2 产品问题

当前前端更像一个代理列表面板，适合回答：

1. 有多少代理。
2. 哪些代理可用。
3. 响应速度如何。
4. 来自哪些国家。
5. 支持哪些协议。

但后续安全研究平台需要回答：

1. 哪些代理可疑或恶意。
2. 哪些代理发生了脚本注入、广告注入、资源替换或 MITM。
3. 某个代理在哪一轮、哪个检测阶段发生异常。
4. 哪些检测没有执行，为什么没有执行。
5. 某个代理的漏斗检测路径是什么。
6. 某类异常是否集中在特定国家、协议、来源或时间段。
7. 某个异常事件背后的证据是什么。

当前页面结构无法清晰承载这些研究问题。

### 2.3 体验问题

当前前端存在这些体验风险：

1. 中文文本存在明显乱码，需要优先修复编码和文案源。
2. 状态反馈偏弱，刷新代理池只是等待接口返回。
3. 错误提示主要在控制台，不适合正式使用。
4. 表格列过多，且未来安全字段更多，继续横向扩展会失控。
5. 缺少详情页，无法解释一个代理为什么被判定为可疑。
6. 缺少任务视角，无法观察安全检测批次和漏斗进度。
7. 缺少证据视角，无法追踪异常来源。

## 3. 重构原则

### 3.1 产品原则

1. 前端不再只展示代理列表，而要展示安全研究过程。
2. 每个安全结论都要能追溯到检测阶段、事件和证据。
3. 必须区分“正常”“异常”“未检测”“不适用”“被跳过”“执行失败”。
4. 高风险信息优先展示，普通性能信息退为辅助。
5. 漏斗式检测路径必须成为核心可视化对象。

### 3.2 工程原则

1. 不继续在 `App.tsx` 中堆组件。
2. 页面、业务特性、通用组件、API 客户端和类型定义分层。
3. 每个页面只负责组合，不直接写复杂数据转换。
4. API response 到 UI model 的映射放在独立 adapter 中。
5. 加载、空状态、错误状态、刷新状态必须标准化。
6. 第一版不引入过重状态管理，优先使用 React state、hooks 和 URL query。

### 3.3 视觉原则

1. 保留专业、冷静、研究工具感。
2. 避免过度霓虹化和装饰化，安全分析界面要更像仪表台，而不是纯炫酷看板。
3. 使用清晰的风险色：低风险、可疑、高风险、严重风险。
4. 信息密度要高，但每屏必须有明确主任务。
5. 表格用于浏览，详情页用于解释，图表用于发现趋势。

## 4. 新前端定位

建议将前端定位为四个工作区：

1. **总览工作区**：快速判断代理池和安全检测整体状态。
2. **调查工作区**：查看代理、事件、证据和历史。
3. **检测工作区**：创建、查看、跟踪安全检测批次。
4. **配置工作区**：管理代理源、蜜罐目标和检测策略。

这四个工作区对应用户的真实使用路径：

1. 先看总体风险。
2. 再进入异常事件或代理详情调查。
3. 然后触发检测或复查。
4. 最后调整检测策略。

## 5. 信息架构

### 5.1 一级导航

建议一级导航如下：

1. 总览
2. 代理资产
3. 安全事件
4. 检测批次
5. 世界地图
6. 蜜罐目标
7. 证据库
8. 配置

### 5.2 页面清单

| 页面 | 路由建议 | 主要用途 |
| --- | --- | --- |
| 安全总览 | `/` 或 `/overview` | 展示全局风险、代理数量、检测状态、异常趋势 |
| 代理资产列表 | `/proxies` | 管理代理池，按基础属性和安全属性筛选 |
| 代理详情 | `/proxies/:proxyId` | 查看代理基础信息、安全结论、漏斗路径、多轮历史、事件 |
| 安全事件列表 | `/events` | 查看所有异常事件，按类型、风险、时间、代理筛选 |
| 安全事件详情 | `/events/:eventId` | 查看事件证据、差分摘要、关联代理和检测记录 |
| 检测批次列表 | `/scans` | 查看安全检测任务、状态、耗时、异常数量 |
| 检测批次详情 | `/scans/:batchId` | 查看本批次漏斗进度、失败原因、命中事件 |
| 世界地图 | `/map` | 以交互式世界地图展示代理地理分布、风险分布和区域摘要 |
| 蜜罐目标 | `/honeypot` | 查看或管理测试页面、资源、manifest |
| 证据库 | `/evidence` | 查看异常证据文件、快照、diff、证书链摘要 |
| 设置 | `/settings` | 配置 API 地址、刷新策略、检测深度、展示偏好 |

第一版可以先实现：

1. 安全总览。
2. 代理资产列表。
3. 代理详情。
4. 安全事件列表。
5. 检测批次列表。
6. 世界地图基础页。

蜜罐目标、证据库和设置可以后置。

## 6. 核心页面设计

### 6.1 安全总览页

目标：让用户在 30 秒内知道系统当前安全态势。

核心模块：

1. 风险概览指标：
   - 总代理数。
   - 活跃代理数。
   - 正常代理数。
   - 可疑代理数。
   - 恶意代理数。
   - 未完成安全检测代理数。

2. 异常类型分布：
   - 内容篡改。
   - 脚本注入。
   - 广告注入。
   - 资源替换。
   - MITM 可疑。
   - 浏览器专属异常。

3. 漏斗检测概览：
   - 基础可用性通过数量。
   - 轻量蜜罐检测数量。
   - DOM 差分检测数量。
   - 资源完整性检测数量。
   - MITM 检测数量。
   - 多轮检测数量。
   - 浏览器深度检测数量。

4. 最近检测批次：
   - 批次状态。
   - 开始时间。
   - 检测数量。
   - 异常数量。
   - 失败数量。

5. 趋势图：
   - 异常比例变化。
   - 高风险事件数量变化。
   - 活跃代理数量变化。

批判性建议：

1. 总览页不要放完整代理表格。
2. 总览页重点是态势和入口，不是解决所有问题。
3. `未检测` 和 `不适用` 必须单独展示，避免统计误导。

### 6.2 代理资产列表页

目标：用于查找、筛选和进入代理调查。

筛选条件：

1. IP / 端口搜索。
2. 协议类型：HTTP、HTTPS、SOCKS5。
3. 国家 / 地区。
4. 来源。
5. 可用状态。
6. 质量评分区间。
7. 安全风险等级。
8. 行为分类。
9. 风险标签。
10. 漏斗阶段。
11. 最近安全检测时间。

表格建议列：

1. 代理地址。
2. 协议。
3. 国家 / 城市。
4. 可用状态。
5. 响应时间。
6. 质量评分。
7. 安全风险。
8. 行为分类。
9. 最近事件。
10. 漏斗阶段。
11. 最近检测时间。

交互：

1. 点击代理地址进入详情。
2. 行内触发轻量复检。
3. 行内加入深度检测队列。
4. 批量选择代理创建检测批次。
5. 保存筛选条件到 URL query。

批判性建议：

1. 不要把所有安全事件都塞进代理列表列里。
2. 表格只显示摘要，解释性信息放到详情页。
3. 列显示应支持第一版固定、后续可配置。

### 6.3 代理详情页

目标：解释一个代理为什么被判定为正常、可疑或恶意。

建议布局：

1. 顶部摘要：
   - IP:Port。
   - 协议。
   - 国家 / ISP。
   - 当前安全风险。
   - 行为分类。
   - 安全评分。
   - 最近检测时间。

2. 风险结论卡片：
   - 当前结论。
   - 风险标签。
   - 置信度。
   - 关键证据摘要。

3. 漏斗路径：
   - 基础连通性。
   - 协议识别。
   - 蜜罐 hash。
   - DOM diff。
   - 资源完整性。
   - MITM。
   - 多轮。
   - 浏览器。

每一层都要显示：

1. 已完成。
2. 正常。
3. 异常。
4. 不适用。
5. 被跳过。
6. 执行失败。

4. 多轮检测历史：
   - 轮次。
   - User-Agent。
   - 目标类型。
   - 检测阶段。
   - 结果。
   - 风险标签。
   - 耗时。

5. 异常事件列表：
   - 事件类型。
   - 风险等级。
   - 目标 URL。
   - 影响节点或资源。
   - 首次出现时间。
   - 证据入口。

6. 证据摘要：
   - DOM 差分摘要。
   - 资源 hash 差异。
   - 证书指纹对比。
   - 跳转链对比。

批判性建议：

1. 代理详情页是前端最重要的解释页面。
2. 必须避免只展示“high risk”，要展示“为什么 high risk”。
3. 漏斗路径中的 `not_applicable` 和 `skipped` 要有明确说明。

### 6.4 安全事件列表页

目标：从异常行为角度调查系统。

筛选条件：

1. 事件类型。
2. 风险等级。
3. 置信度。
4. 协议。
5. 国家。
6. 来源。
7. 时间范围。
8. 外部域名。
9. 检测批次。

表格建议列：

1. 事件类型。
2. 风险等级。
3. 代理。
4. 目标类型。
5. 影响对象。
6. 外部域名。
7. 置信度。
8. 发生时间。
9. 证据状态。

典型用途：

1. 找出所有 `script_injection`。
2. 找出所有 MITM 可疑代理。
3. 查看是否有多个代理注入同一个外部域名。
4. 查看某个批次中所有高风险事件。

### 6.5 检测批次页

目标：观察安全检测任务和漏斗推进情况。

批次列表展示：

1. 批次 ID。
2. 检测策略。
3. 最大检测深度。
4. 状态。
5. 目标代理数。
6. 已完成数。
7. 跳过数。
8. 错误数。
9. 异常事件数。
10. 开始时间。
11. 耗时。

批次详情展示：

1. 批次参数。
2. 漏斗阶段统计。
3. 每一层通过、异常、跳过、不适用、错误数量。
4. 高风险事件列表。
5. 失败原因分布。
6. 代理检测记录表。

批判性建议：

1. 批次页是“检测过程”视角，不是代理详情视角。
2. 漏斗阶段统计必须可视化，否则很难看出检测策略是否合理。

### 6.6 世界地图页

目标：用交互式世界地图展示代理的全球分布、安全风险分布和区域级摘要，让用户不通过表格也能快速发现地理聚集现象。

核心定位：

1. 这是一个独立页面，不只是总览页里的小地图。
2. 地图用于探索“哪里代理多、哪里风险高、哪里异常集中”。
3. 地图应同时支持基础代理分布和安全风险分布。
4. 光标悬停到国家、地区或聚合点时，展示该区域代理基本信息。

地图展示模式：

1. 国家 / 地区着色图：按代理数量、活跃数量或异常比例给国家着色。
2. 聚合点地图：按城市、出口 IP 地理位置或国家中心点显示代理聚合点。
3. 风险热力图：突出高风险、MITM 可疑、脚本注入等异常密集区域。
4. 协议分布图层：按 HTTP、HTTPS、SOCKS5 过滤地图。
5. 漏斗阶段图层：显示不同地区代理进入到哪一层检测。

悬停信息卡片：

当光标放到某个国家、地区或聚合点时，显示：

1. 国家 / 地区名称。
2. 代理总数。
3. 活跃代理数。
4. 未检测代理数。
5. 正常代理数。
6. 可疑代理数。
7. 恶意代理数。
8. 平均响应时间。
9. 主要协议分布。
10. 最高风险等级。
11. 最常见异常类型。
12. 最近安全检测时间。

点击交互：

1. 点击国家或聚合点，打开右侧区域详情面板。
2. 区域详情面板展示该地区的代理列表摘要。
3. 支持从区域详情跳转到代理资产页，并自动带上国家、风险等级或协议筛选。
4. 支持从区域详情跳转到安全事件页，查看该地区的异常事件。

地图筛选：

1. 时间范围。
2. 协议类型。
3. 代理状态。
4. 安全风险等级。
5. 行为分类。
6. 异常事件类型。
7. 检测深度。
8. 漏斗阶段。

地图图例：

1. 代理数量色阶。
2. 异常比例色阶。
3. 风险等级颜色。
4. 数据缺失状态。
5. 未检测状态。

批判性建议：

1. 地图不要只做装饰，必须能回答实际问题。
2. 地图悬停信息要简洁，详细分析放在右侧面板。
3. `未检测`、`不适用` 和 `无数据` 要明确区分。
4. 第一版可以先做到国家级聚合，不必立即做到城市级精准定位。
5. 地理位置数据可能不稳定，地图必须展示“未知地区”统计，不能丢弃这部分代理。

### 6.7 图表体系

目标：用折线图、柱状图、堆叠柱状图、饼图或环形图等图表，把安全检测趋势和代理分布展示出来，减少纯表格阅读压力。

建议图表类型：

| 图表 | 使用位置 | 表达问题 |
| --- | --- | --- |
| 折线图 | 安全总览、批次详情 | 异常比例、活跃代理数、检测数量随时间变化 |
| 柱状图 | 总览、事件页 | 不同异常类型数量、不同国家代理数量 |
| 堆叠柱状图 | 地图页、总览页 | 各地区 normal / suspicious / malicious 占比 |
| 水平条形图 | 事件页、批次页 | Top 风险国家、Top 异常类型、Top 外部域名 |
| 环形图 | 总览页 | 行为分类分布、协议分布 |
| 面积图 | 趋势分析 | 安全事件量或代理存活量的时间趋势 |
| 漏斗图 | 批次详情、总览页 | 各检测层级进入数量、跳过数量、异常数量 |
| 散点图 | 代理分析 | 响应时间与安全评分、质量评分与异常触发率关系 |

优先图表：

1. 异常比例时间趋势折线图。
2. 异常类型柱状图。
3. 协议分布环形图。
4. 风险等级堆叠柱状图。
5. 漏斗阶段统计图。
6. 国家 / 地区风险排行条形图。

交互要求：

1. 图表支持悬停 tooltip。
2. 图表支持点击筛选，例如点击 `script_injection` 后跳到事件列表。
3. 图表显示空状态，不要在无数据时留白。
4. 图表的风险颜色必须和全站风险色一致。
5. 图表数据需要标注统计口径，例如最近 24 小时、最近 7 天或全部历史。

推荐组件：

1. `TrendLineChart`
2. `RiskBarChart`
3. `BehaviorDonutChart`
4. `FunnelChart`
5. `GeoRiskBarChart`
6. `ProtocolDistributionChart`

批判性建议：

1. 不要为了图表而图表，每个图表都要有明确问题。
2. 总览页图表数量要克制，更多分析图表可以放到事件页、批次页和地图页。
3. 第一版可以先使用轻量图表库，等需求稳定后再考虑复杂大屏式可视化。

## 7. 数据模型规划

### 7.1 前端类型目录

建议拆分类型：

```text
src/types/
  proxy.ts
  security.ts
  scan.ts
  event.ts
  evidence.ts
  api.ts
```

### 7.2 核心类型

建议前端核心类型包括：

```ts
type RiskLevel = 'unknown' | 'low' | 'medium' | 'high' | 'critical';

type BehaviorClass =
  | 'normal'
  | 'content_tampering'
  | 'ad_injection'
  | 'script_injection'
  | 'redirect_manipulation'
  | 'resource_replacement'
  | 'mitm_suspected'
  | 'stealthy_malicious'
  | 'unstable_but_non_malicious';

type Applicability = 'applicable' | 'not_applicable' | 'unknown';

type ExecutionStatus =
  | 'planned'
  | 'running'
  | 'completed'
  | 'skipped'
  | 'error'
  | 'timeout';

type ScanDepth = 'light' | 'standard' | 'deep' | 'browser';
```

代理摘要类型：

```ts
interface ProxySummary {
  id: string;
  ip: string;
  port: number;
  source: string;
  protocols: string[];
  country?: string;
  city?: string;
  isAlive: boolean;
  responseTimeMs?: number;
  qualityScore?: number;
  securityRisk: RiskLevel;
  securityScore?: number;
  behaviorClass?: BehaviorClass;
  riskTags: string[];
  funnelStage?: number;
  lastCheckTime?: string;
  lastSecurityCheckTime?: string;
}
```

漏斗阶段类型：

```ts
interface FunnelStep {
  stage: string;
  label: string;
  checkerName?: string;
  applicability: Applicability;
  executionStatus: ExecutionStatus;
  riskLevel?: RiskLevel;
  isAnomalous: boolean;
  skipReason?: string;
  evidenceCount?: number;
  elapsedMs?: number;
}
```

地图区域摘要类型：

```ts
interface GeoProxySummary {
  countryCode: string;
  countryName: string;
  latitude?: number;
  longitude?: number;
  totalProxies: number;
  activeProxies: number;
  uncheckedProxies: number;
  normalProxies: number;
  suspiciousProxies: number;
  maliciousProxies: number;
  avgResponseTimeMs?: number;
  protocols: {
    http: number;
    https: number;
    socks5: number;
  };
  topRiskLevel: RiskLevel;
  topEventTypes: Array<{
    eventType: string;
    count: number;
  }>;
  anomalyRate?: number;
  lastSecurityCheckTime?: string;
}
```

图表数据类型：

```ts
interface TimeSeriesPoint {
  timestamp: string;
  total?: number;
  normal?: number;
  suspicious?: number;
  malicious?: number;
  anomalyRate?: number;
}

interface DistributionPoint {
  key: string;
  label: string;
  value: number;
  riskLevel?: RiskLevel;
}
```

批判性建议：

1. 不要继续使用乱码中文作为枚举值，例如 `瀛樻椿`。
2. API 层可以接收后端字段，但 UI 层应使用稳定英文枚举。
3. 中文展示文案应由 label map 统一映射。

## 8. API 客户端规划

当前 `lib/api.ts` 应拆分为业务域 API：

```text
src/api/
  client.ts
  proxies.ts
  security.ts
  scans.ts
  events.ts
  evidence.ts
  geo.ts
  analytics.ts
  filters.ts
```

`client.ts` 负责：

1. base URL。
2. query 参数序列化。
3. JSON 解析。
4. 错误标准化。
5. 超时控制。

业务 API 负责：

1. `getProxies`
2. `getProxyDetail`
3. `getSecurityOverview`
4. `getSecurityEvents`
5. `getScanBatches`
6. `getScanBatchDetail`
7. `createSecurityScan`
8. `getEvidenceDetail`
9. `getGeoProxySummary`
10. `getGeoRegionDetail`
11. `getSecurityTrend`
12. `getRiskDistribution`
13. `getEventTypeDistribution`

建议统一错误模型：

```ts
interface ApiError {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
}
```

## 9. 组件架构

建议目录结构：

```text
src/
  app/
    App.tsx
    router.tsx
    layout/
      AppShell.tsx
      Sidebar.tsx
      Topbar.tsx
  api/
  components/
    ui/
      Button.tsx
      Badge.tsx
      Select.tsx
      Table.tsx
      Tabs.tsx
      EmptyState.tsx
      ErrorState.tsx
      LoadingState.tsx
    data-display/
      MetricTile.tsx
      RiskBadge.tsx
      ProtocolBadge.tsx
      StatusBadge.tsx
      FunnelStepper.tsx
      charts/
        TrendLineChart.tsx
        RiskBarChart.tsx
        BehaviorDonutChart.tsx
        FunnelChart.tsx
        GeoRiskBarChart.tsx
      maps/
        WorldProxyMap.tsx
        MapTooltip.tsx
        RegionDetailPanel.tsx
        MapLegend.tsx
  features/
    overview/
    proxies/
    events/
    scans/
    map/
    analytics/
    evidence/
    honeypot/
    settings/
  hooks/
  lib/
  types/
```

页面组件只做组合：

```text
features/proxies/pages/ProxyListPage.tsx
features/proxies/pages/ProxyDetailPage.tsx
features/proxies/components/ProxyTable.tsx
features/proxies/components/ProxyFilters.tsx
features/proxies/components/ProxyRiskSummary.tsx
```

安全事件模块：

```text
features/events/pages/EventListPage.tsx
features/events/pages/EventDetailPage.tsx
features/events/components/EventTable.tsx
features/events/components/EventFilters.tsx
features/events/components/EventEvidencePanel.tsx
```

检测批次模块：

```text
features/scans/pages/ScanListPage.tsx
features/scans/pages/ScanDetailPage.tsx
features/scans/components/ScanBatchTable.tsx
features/scans/components/FunnelStageStats.tsx
features/scans/components/ScanRecordTable.tsx
```

地图模块：

```text
features/map/pages/WorldMapPage.tsx
features/map/components/WorldMapToolbar.tsx
features/map/components/WorldMapFilters.tsx
features/map/components/WorldMapStats.tsx
features/map/components/RegionProxyPanel.tsx
features/map/components/GeoRiskLegend.tsx
```

图表模块：

```text
features/overview/components/SecurityTrendPanel.tsx
features/overview/components/RiskDistributionPanel.tsx
features/events/components/EventTypeChart.tsx
features/scans/components/FunnelStageChart.tsx
features/map/components/GeoDistributionCharts.tsx
```

## 10. 设计系统建议

### 10.1 色彩

建议从当前深色霓虹风调整为更稳的研究工具风。

风险色：

1. `unknown`：中性灰。
2. `low`：绿色。
3. `medium`：黄色。
4. `high`：橙红。
5. `critical`：红色。

状态色：

1. `completed`：绿色或蓝色。
2. `running`：蓝色。
3. `skipped`：灰色。
4. `not_applicable`：灰色虚线或浅灰。
5. `error`：红色。
6. `timeout`：橙色。

批判性建议：

1. 不要让所有状态都使用蓝紫霓虹色。
2. 风险色要一致，不能在不同页面含义变化。
3. `not_applicable` 不应显示成错误红色。

### 10.2 布局

建议使用：

1. 左侧固定导航。
2. 顶部当前页面标题和全局操作。
3. 主内容区域滚动。
4. 详情页使用上下分区，而不是复杂弹窗。
5. 表格页面使用顶部筛选条 + 主表格 + 右侧可选详情抽屉。

### 10.3 关键组件

必须优先设计的组件：

1. `RiskBadge`
2. `BehaviorClassBadge`
3. `ExecutionStatusBadge`
4. `ApplicabilityBadge`
5. `ProtocolBadge`
6. `FunnelStepper`
7. `EvidenceLink`
8. `MetricTile`
9. `FilterBar`
10. `DataTable`

其中 `FunnelStepper` 是新前端的核心组件。它要表达：

1. 哪些阶段完成。
2. 哪些阶段异常。
3. 哪些阶段不适用。
4. 哪些阶段被跳过。
5. 哪些阶段执行失败。

## 11. 关键交互流程

### 11.1 调查一个高风险代理

流程：

1. 用户进入总览页。
2. 点击高风险代理数量。
3. 进入代理列表并自动筛选 `securityRisk=high`。
4. 点击某个代理。
5. 查看代理详情页顶部风险摘要。
6. 查看漏斗路径，定位异常发生在 DOM diff 或 MITM。
7. 查看异常事件列表。
8. 打开事件证据。

### 11.2 分析某类异常

流程：

1. 用户进入安全事件页。
2. 选择 `script_injection`。
3. 按风险等级、国家、协议筛选。
4. 查看是否多个代理注入相同外部域名。
5. 进入事件详情查看 DOM 差分证据。

### 11.3 查看检测批次质量

流程：

1. 用户进入检测批次页。
2. 打开最近一次批次。
3. 查看漏斗阶段统计。
4. 发现大量代理在 MITM 阶段 `not_applicable`。
5. 查看原因：代理不支持 HTTPS / SOCKS5。
6. 调整下一批检测策略。

## 12. 分阶段落地计划

### 第一阶段：前端基础重构

目标：先把结构拆清楚，修复乱码，建立新布局。

内容：

1. 新建目录结构。
2. 引入路由。
3. 拆分 API 客户端。
4. 拆分类型定义。
5. 建立 AppShell。
6. 修复中文乱码和文案映射。
7. 重做代理列表页。

验收标准：

1. `App.tsx` 不再承载大部分业务逻辑。
2. 中文正常显示。
3. 代理列表功能不退化。
4. API 错误有用户可见提示。

### 第二阶段：安全总览与安全字段

目标：让前端开始呈现安全研究平台形态。

内容：

1. 安全总览页。
2. 风险指标卡。
3. 行为分类分布。
4. 漏斗检测概览。
5. 代理列表增加安全风险、行为分类、漏斗阶段。
6. 异常比例时间趋势折线图。
7. 异常类型柱状图。
8. 协议分布环形图。

验收标准：

1. 用户能区分正常、可疑、恶意、未检测。
2. 用户能看到不同异常类型分布。
3. 用户能从总览跳到代理列表或事件列表。
4. 用户能通过图表看到风险变化趋势。

### 第三阶段：代理详情与漏斗路径

目标：解释单个代理的安全结论。

内容：

1. 代理详情页。
2. `FunnelStepper`。
3. 多轮检测记录表。
4. 异常事件列表。
5. 证据摘要面板。

验收标准：

1. 用户能看到代理在哪一层发生异常。
2. 用户能看到哪些检测不适用或被跳过。
3. 用户能从代理详情进入事件或证据。

### 第四阶段：事件与批次分析

目标：支持研究视角的横向分析。

内容：

1. 安全事件列表。
2. 事件详情页。
3. 检测批次列表。
4. 检测批次详情。
5. 漏斗阶段统计。
6. 失败原因分布。
7. 异常类型柱状图。
8. 漏斗阶段图。
9. 风险国家排行条形图。

验收标准：

1. 用户能按事件类型调查异常。
2. 用户能查看检测批次的执行质量。
3. 用户能区分检测策略导致的跳过和真实异常。
4. 用户能通过图表发现异常集中类型和高风险地区。

### 第五阶段：世界地图与地理分析

目标：将代理分布和安全风险放到地理空间中分析。

内容：

1. 世界地图页面。
2. 国家级代理分布着色。
3. 国家 / 地区 hover 信息卡片。
4. 区域详情面板。
5. 地图筛选器。
6. 地图图例。
7. 从地图跳转到代理列表或事件列表。
8. 地区风险排行图表。

验收标准：

1. 用户能在世界地图中查看每个国家或地区的代理摘要。
2. 光标悬停到地图区域时能看到代理总数、活跃数、风险分布和主要异常类型。
3. 用户能点击某个地区进入区域详情。
4. 用户能从地图快速跳转到对应筛选后的代理或事件列表。

### 第六阶段：证据库、蜜罐和策略配置

目标：补齐研究平台的配置和证据管理能力。

内容：

1. 证据库页面。
2. 蜜罐目标页面。
3. 检测策略配置。
4. 检测批次创建表单。
5. 导出研究数据。

验收标准：

1. 用户能查看关键证据文件。
2. 用户能管理或查看蜜罐目标。
3. 用户能按检测深度创建安全检测批次。

## 13. 第一版 MVP

如果要快速落地，第一版前端 MVP 建议只做：

1. 修复中文乱码。
2. 重构目录结构。
3. 建立 AppShell 和路由。
4. 重做代理列表页。
5. 新增安全总览页。
6. 新增代理详情页。
7. 实现 `RiskBadge`、`BehaviorClassBadge`、`ExecutionStatusBadge`、`ApplicabilityBadge`、`FunnelStepper`。
8. API 客户端按模块拆分。
9. 支持安全字段的 mock 或兼容空数据。
10. 页面能清楚展示 `not_applicable`、`skipped`、`error`。
11. 在总览页加入至少 2 个基础图表：风险趋势折线图和异常类型柱状图。
12. 新增世界地图基础页，先支持国家级代理数量和风险分布展示。
13. 地图支持 hover 信息卡片，展示国家级代理摘要。

暂不做：

1. 复杂图表联动系统。
2. 完整证据 diff 查看器。
3. 检测策略编辑器。
4. 蜜罐目标管理。
5. 浏览器截图查看。
6. 登录权限系统。
7. 城市级地图精细定位。
8. 复杂热力图动画。

## 14. 需要后端配合的 API

为了让新前端顺利落地，后端至少需要逐步提供：

1. `GET /api/security/overview`
2. `GET /api/proxies`
3. `GET /api/proxies/:id`
4. `GET /api/proxies/:id/security-history`
5. `GET /api/proxies/:id/events`
6. `GET /api/security/events`
7. `GET /api/security/scans`
8. `GET /api/security/scans/:batchId`
9. `POST /api/security/scans`
10. `GET /api/security/geo`
11. `GET /api/security/geo/:countryCode`
12. `GET /api/security/analytics/trend`
13. `GET /api/security/analytics/event-types`
14. `GET /api/security/analytics/risk-distribution`

第一版如果后端还没完成，可以前端先以兼容模式运行：

1. 已有 `/api/proxies`、`/api/stats`、`/api/filters` 继续使用。
2. 安全字段为空时显示“未检测”。
3. 安全总览暂时通过已有 stats + mock security summary 过渡。
4. 世界地图先用国家字段聚合已有代理列表数据，后端地理聚合 API 完成后再切换。

## 15. 待确认问题

重构前建议确认：

1. 是否保留当前 Vite + React 技术栈。
2. 是否继续使用 Tailwind CSS。
3. 是否引入图表库，例如 Recharts、ECharts 或 Tremor。
4. 是否引入数据请求库，例如 TanStack Query。
5. 是否需要登录和权限控制。
6. 是否先完全修复中文乱码。
7. 安全总览第一版需要哪些指标。
8. 代理详情页是否作为独立页面，而不是抽屉。
9. 事件证据第一版展示摘要还是完整 diff。
10. 前端是否需要支持导出 CSV / JSON。
11. 图表库优先选择 Recharts、ECharts 还是其他方案。
12. 世界地图使用 SVG 地图、ECharts 地图，还是 Leaflet / MapLibre 这类地图引擎。
13. 第一版地图做到国家级还是城市级。
14. 地图 hover 信息卡片第一版展示哪些指标。
15. 地图是否需要支持点击联动筛选代理列表和事件列表。

## 16. 我的建议

我建议这次前端重构不要追求一次性把所有安全研究功能都做完，而是先完成结构性重建：

1. 先把前端从单文件大组件拆成可维护架构。
2. 先修复中文乱码。
3. 先建立安全总览、代理列表和代理详情三条主线。
4. 先把 `FunnelStepper` 做好，因为它是漏斗式检测最核心的表达。
5. 总览页先加入少量高价值图表，让安全态势更直观。
6. 世界地图建议作为第一版可见亮点，但先做国家级聚合，不要一开始追求城市级精准。
7. 等后端安全检测 API 成熟后，再补事件、证据、批次和策略配置。

前端的核心价值不是把更多字段堆到表格里，而是把“代理为什么可疑”解释清楚。只要这个方向抓住，后续页面扩展会自然很多。

## 17. 决策记录

| 日期 | 决策 | 原因 | 影响 |
| --- | --- | --- | --- |
| 2026-04-17 | 前端建议彻底重构为安全研究分析平台 | 后续能力已从代理可用性展示升级为行为分析、漏斗检测和证据追踪 | 前端需要重建信息架构、路由、类型、API 客户端和核心页面 |
| 2026-04-17 | 将图表体系和交互式世界地图纳入前端核心规划 | 用户希望增加折线图、柱状图等图表，并单独开设世界地图页 | 前端新增地图页、地理数据模型、图表组件、地理聚合 API 规划 |

## 18. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-04-17 | 初始化前端重构规划文档 |
| 2026-04-17 | 增加图表体系与交互式世界地图页面规划 |

## 与当前架构审计的配合要求

前端重构应当先阅读 `docs/project-architecture-audit.md`。审计文档已经指出，当前前端不适合继续在单个入口文件中叠加复杂图表、世界地图、代理详情、安全事件和检测批次页面。

因此，前端实施时需要把以下内容作为前置任务：

1. 修复当前中文乱码问题。
2. API 返回值内部使用稳定英文枚举，中文文案在前端映射展示。
3. 拆分 `App.tsx` 中的页面、状态、请求和展示逻辑。
4. 建立 `app`、`api`、`components`、`features`、`hooks`、`lib`、`types` 等目录边界。
5. 图表和世界地图不要直接绑定临时字段，应对齐数据库和 API 中的风险等级、行为类别、执行状态、适用性、检测批次等稳定模型。
6. 世界地图第一版只做国家级聚合，确保数据语义准确，再逐步考虑城市级或更复杂的地图交互。

前端不是单纯美化任务，而是安全研究结果的解释层。它必须能够清楚表达：某个代理为什么正常、可疑或恶意；某个检测为什么执行、跳过、失败或不适用。
