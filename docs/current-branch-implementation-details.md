# 当前分支内容实现说明

生成日期：2026-05-05

## 1. 分支结论

本次核对后，远端最新整合点是 `origin/main`，它包含 `codex/organize-project-structure` 的合并提交；当前工作区所在分支是 `codex/proxytester-complete-build`。从已提交历史看，`codex/proxytester-complete-build` 的 HEAD 少一个项目结构整理提交，但当前工作区已经包含该整理方向的大部分内容，并额外叠加了扫描策略、checker 契约、API 参数和测试更新。

因此，发布对象应是当前工作区所在的 `codex/proxytester-complete-build`。发布后，该分支会成为当前功能最完整的候选分支：它保留代理采集、检测、评分、入库和查询能力，同时补齐安全扫描平台、蜜罐观测、行为事件、证据持久化、前端看板和运行文档。

## 2. 总体定位

ProxyTester 已从单纯的免费代理可用性检测工具，扩展为代理安全研究平台基础版。系统不只判断代理是否连通，还会把代理作为可观察对象，记录其协议能力、匿名性、出口地理位置、业务可用性、安全风险、扫描批次、行为事件、证据摘要、证书观测、资源观测和蜜罐访问日志。

核心目标包括：

- 采集免费代理源并转换为统一代理模型。
- 对代理进行 TCP、HTTP、HTTPS、SOCKS5、匿名性、出口地理和业务可用性检测。
- 对可用代理执行安全 checker，发现 MITM、DOM 篡改、资源替换、异常流量和蜜罐访问行为。
- 将检测过程拆成批次、记录、事件、证据和观测表，便于后续审计和趋势分析。
- 提供 Flask API 给前端读取代理资产、扫描批次、安全事件、地图聚合和风险趋势。
- 提供 React + Vite + TypeScript 前端，用于安全总览、代理列表、代理详情、扫描批次、事件详情、蜜罐目标和世界地图。

## 3. 后端架构

后端入口是 `api.py` 和 `api/app_factory.py`。应用工厂创建 Flask 应用，启用 CORS，并注册三个蓝图：

- `api.routes.proxy_routes`：代理列表、过滤器、统计、高质量代理、代理详情、删除和刷新工作流。
- `api.routes.security_routes`：安全总览、代理安全详情、历史、事件、批次、地理聚合、趋势、风险分布、蜜罐 manifest 和手动安全扫描。
- `honeypot.routes`：本地蜜罐页面、资源、下载样本和提交入口。

服务层位于 `services/`：

- `ProxyWorkflowService` 负责从外部源和 Deadpool 源刷新代理、规范化数据、写入 canonical 文件，并触发检测。
- `ProxyCheckService` 负责装配默认 checker、security checker、scorer、MySQL repository 和扫描 repository，然后执行完整检测。
- `ProxyQueryService` 负责代理资产查询、筛选、统计、详情和删除。
- `SecurityQueryService` 负责安全总览、批次、事件、地理、趋势和风险分布查询。

## 4. 检测管线

检测管线由 `scheduler/check_pipeline.py` 实现。它以 `CheckContext` 为运行上下文，按顺序执行基础 checker、安全 checker 和评分器。

基础 checker 的执行规则：

- checker 按 `order` 排序。
- 禁用 checker 会记录 `skipped` 结果。
- 不支持当前代理能力的 checker 会记录 `not_applicable`。
- 阻断型 checker 失败后，后续基础 checker 会被跳过。
- 每个结果会被标准化为 `completed`、`skipped`、`timeout` 或 `error`。
- TCP、协议聚合、匿名性、地理和业务可用性结果会回写到代理模型。

安全 checker 的执行规则：

- 只有代理 `is_usable` 时才进入安全阶段。
- `ScanPolicy` 从运行时参数构建，控制最大扫描深度、成本等级、启用/禁用 checker 和配置依赖。
- `CapabilityRouter` 根据 checker 元数据判断是否运行，不能运行时记录结构化跳过原因。
- 安全结果会统一写入扫描记录，并在异常时索引证据摘要、资源观测、证书观测和行为事件。

批次执行使用 `ThreadPoolExecutor` 并发处理代理。批次开始时写入 `SecurityScanBatch`，结束时标记完成；可用代理会串行保存到 MySQL，降低并发写库风险。

## 5. Checker 契约和策略路由

`core/interfaces/checker_base.py` 定义了基础 checker、security checker、scorer 和 repository 接口。安全 checker 现在具备显式元数据：

- `funnel_stage`：漏斗阶段，用于前端展示和过程归因。
- `scan_depth`：`light`、`standard`、`deep`、`multi_round`、`browser`。
- `cost_level`：`low`、`medium`、`high`。
- `required_capabilities`：例如 `usable`、`http`、`https`、`web`、`socks5`、`tls_proxy`。
- `required_config`：例如 `HONEYPOT_BASE_URL`、`MITM_TARGET_URL`。
- `required_results`：依赖前置安全 checker 的完成结果。
- `produces_events`：声明可能产生的事件类型。
- `description`：描述 checker 的检测目的。

`security/policy.py` 实现 `ScanPolicy`、`PolicyDecision` 和 `CapabilityRouter`。策略路由解决了两个问题：

- 避免把缺少配置、缺少能力或超出扫描深度的 checker 误判为检测失败。
- 让前端或 API 可以通过 `maxScanDepth`、`scanPolicy.enabledCheckers`、`scanPolicy.disabledCheckers`、`allowedCostLevels` 精准控制扫描成本和范围。

`security/registry.py` 会加载 `security.plugins` 下的安全 checker，并使用 `validate_security_checker` 校验名称、深度、成本等级和依赖声明。重复名称或非法元数据会在启动阶段暴露出来。

## 6. 安全检测能力

当前安全模块覆盖以下方向：

- `mitm_checker`：对目标 HTTPS URL 做证书探测，记录证书观测和 MITM 风险。
- `dom_diff_checker`：通过代理访问蜜罐页面并比较 HTML/DOM 差异，识别注入、替换和异常片段。
- `resource_integrity_checker`：观测 CSS、JS、SVG、下载样本等资源完整性，记录资源观测。
- `traffic_analysis_checker`：分析访问行为和响应特征，输出流量异常标签。
- `honeypot_checker`：访问本地蜜罐 manifest 中的目标，记录命中、行为事件和风险证据。
- `dynamic_observation`：提供动态观测能力，用于按步骤访问页面、资源或下载目标。
- `security.diff`：提供 HTML、证书和资源差异计算。
- `security.rules`：将低层结果映射为风险等级、风险标签和行为分类。

这些 checker 不是孤立执行，而是通过 `CheckPipeline` 统一进行策略判断、结果归一化、证据保存和评分聚合。

## 7. 数据模型和持久化

核心模型位于 `core/models/`：

- `ProxyModel` 描述代理地址、协议能力、匿名性、地理位置、响应时间、业务评分、安全风险和更新时间。
- `CheckResult` 和 `SecurityResult` 描述基础检测和安全检测结果。
- `SecurityScanBatch` 和 `SecurityScanRecord` 描述批次和单条扫描记录。
- `ResourceObservation` 描述资源请求、哈希、状态码、差异和异常标签。
- 枚举集中放在 `core/models/enums.py`，避免不同模块硬编码状态字符串。

MySQL 持久化位于 `storage/mysql/`：

- `connection.py` 支持 `PROXYTESTER_DB_*` 环境变量，并兼容旧的 `DB_*` 变量。
- `proxy_repository.py` 保存和查询代理主表。
- `security_repositories.py` 保存批次、扫描记录、证据、证书观测、资源观测和行为事件。
- `security_query_repository.py` 面向前端查询安全总览、列表、事件、批次、趋势和地图数据。
- `honeypot_repository.py` 保存蜜罐请求日志和目标命中记录。

数据库 migration 位于 `migrations/001` 到 `011`。它们覆盖代理安全字段、扫描批次、扫描记录、行为事件、证据文件、证书观测、资源观测、代理来源、代理检测记录、蜜罐目标和蜜罐请求日志。

## 8. API 能力

代理 API：

- `GET /api/proxies`：分页查询代理，支持国家、类型、状态、业务分、风险等级、行为分类和风险标签过滤。
- `GET /api/filters`：返回筛选项。
- `GET /api/stats`：返回代理统计。
- `GET /api/proxies/high-quality`：查询高质量代理。
- `GET /api/proxies/<ip>:<port>`：查询代理详情。
- `DELETE /api/proxies/<ip>:<port>`：删除代理。
- `POST /api/refresh`：刷新代理源并执行检测工作流。

安全 API：

- `GET /api/security/overview`：安全总览。
- `GET /api/security/proxies`：安全视角代理列表。
- `GET /api/security/proxies/<ip>:<port>`：代理安全详情。
- `GET /api/security/proxies/<ip>:<port>/history`：代理扫描历史。
- `GET /api/security/proxies/<ip>:<port>/events`：代理相关安全事件。
- `GET /api/security/scans` / `GET /api/security/batches`：扫描批次列表。
- `GET /api/security/scans/<batch_id>` / `GET /api/security/batches/<batch_id>`：批次详情。
- `GET /api/security/events`：安全事件列表。
- `GET /api/security/events/<id>`：事件详情。
- `GET /api/security/geo`：地理聚合。
- `GET /api/security/geo/<country>`：区域详情。
- `GET /api/security/stats/behavior`：行为统计。
- `GET /api/security/stats/risk-trend`：风险趋势。
- `GET /api/security/analytics/event-types`：事件类型分布。
- `GET /api/security/analytics/risk-distribution`：风险分布。
- `GET /api/security/honeypot/manifest`：蜜罐目标 manifest。
- `POST /api/security/proxies/<ip>:<port>/scan`：扫描单个代理。
- `POST /api/security/batches` / `POST /api/security/scans`：创建安全扫描批次。

手动扫描 API 支持 `maxWorkers`、`maxScanDepth` 和 `scanPolicy`。这让调用方可以从轻量扫描逐步扩展到标准或深度扫描。

## 9. 前端实现

前端项目位于 `daili/`，技术栈为 Vite、React、TypeScript 和 Tailwind。主要结构：

- `src/app/App.tsx`：路由和页面挂载。
- `src/app/layout/AppShell.tsx`：应用外壳、导航和布局。
- `src/api/` 与 `src/lib/api.ts`：API client 和请求封装。
- `src/components/charts/`：折线、漏斗、环图、条形图等图表组件。
- `src/components/security/FunnelStepper.tsx`：安全扫描漏斗展示。
- `src/components/ui/`：Badge、LoadingState、ErrorState 等通用组件。
- `src/features/overview/pages/SecurityOverviewPage.tsx`：安全总览。
- `src/features/proxies/pages/ProxyListPage.tsx`：代理列表和筛选。
- `src/features/proxies/pages/ProxyDetailPage.tsx`：代理详情、历史和事件。
- `src/features/security/pages/SecurityBatchesPage.tsx`：扫描批次。
- `src/features/security/pages/SecurityEventsPage.tsx`：安全事件列表。
- `src/features/security/pages/SecurityEventDetailPage.tsx`：事件详情。
- `src/features/security/pages/HoneypotTargetsPage.tsx`：蜜罐目标。
- `src/features/map/pages/WorldMapPage.tsx`：世界地图聚合视图。

前端关注的是安全运营台体验：可扫描、可筛选、可追踪批次、可查看事件证据、可从地图维度观察风险分布。

## 10. 脚本和项目结构整理

当前分支将旧的根目录脚本整理到 `scripts/`：

- `scripts/run/start_all.ps1`：Windows PowerShell 一键启动脚本。
- `scripts/run/start_servers.bat`：Windows 批处理启动脚本。
- `scripts/diagnostics/chart.py`：诊断图表脚本。
- `scripts/diagnostics/check_db.py`：数据库诊断脚本。
- `scripts/check_migrations.py`：migration 文件和数据库结构检查脚本。
- `scripts/compat/`：保留旧入口兼容文件。

旧的 Deadpool 和 UI/UX 技能包材料被整理到 `third_party/`，用于离线参考和复现历史集成来源；运行时核心逻辑不依赖它们直接作为业务模块导入。

## 11. 测试覆盖

测试目录位于 `tests/`。当前覆盖重点包括：

- 阶段 0 语义和结果归一化。
- MITM 证书检测。
- DOM 和流量 checker。
- 动态观测。
- 资源完整性。
- 蜜罐 MVP。
- 安全 API 路由。
- 安全 rollup 查询。
- 代理详情路由。
- 扫描策略和能力路由。

这些测试验证了安全平台最重要的边界：缺少配置时应跳过而不是误报失败，checker 元数据应被校验，API 应能返回前端需要的结构化数据。

## 12. `.gitignore` 发布规则

本次发布前已扩展根目录 `.gitignore`，重点忽略：

- Python 缓存和测试覆盖产物。
- 虚拟环境目录。
- 本地 `.env` 与私密环境文件，同时保留 `.env.example`。
- 日志文件。
- Node/Vite 构建和依赖目录。
- SQLite、dump、备份和压缩 SQL 产物。
- 系统临时文件。

这些规则可以避免把本地环境、缓存、构建输出、数据库导出和私密配置发布到远端。

## 13. 发布建议

建议以 `codex/proxytester-complete-build` 作为功能分支发布。该分支发布后可作为下一步合并到 `main` 的候选分支。合并前建议再次执行：

```powershell
python -m pytest
cd daili
npm run build
```

如果数据库可用，再执行：

```powershell
python scripts\check_migrations.py --check-db
```

这三步分别覆盖 Python 单元测试、前端构建和数据库 schema 健康检查。
