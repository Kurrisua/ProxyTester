# ProxyTester 规划完成度审计

> 本文档用于对照 `docs/` 目录中的原始规划，梳理当前代码已经完成、部分完成和尚未完成的内容。  
> 审计日期：2026-04-26  
> 对照文档：  
> - `docs/project-architecture-audit.md`
> - `docs/next-build-plan.md`
> - `docs/database-design-plan.md`
> - `docs/frontend-redesign-plan.md`
> - `docs/next-thread-build-prompt.md`

## 1. 总体结论

当前项目已经完成了从“代理可用性检测工具”向“代理安全研究平台”的一大部分基础建设：

1. 后端已经有 checker / security checker / scorer / repository / service 的分层。
2. `CheckPipeline` 已经能执行基础检测、安全检测、评分，并为每个 checker 记录执行状态。
3. 数据库 migration 文件已经覆盖规划中的主要安全研究表。
4. 已有轻量蜜罐、直连与代理双路径访问、HTML/DOM 差分、资源完整性、证书 MITM、多轮观测雏形和安全评分。
5. 前端已经从单一代理池看板扩展为安全总览、代理详情、事件、批次、蜜罐目标和世界地图页面。

但规划中的完整形态还没有全部完成。当前更准确的状态是：

```text
第 0 阶段结构稳定化：大部分完成
安全检测 MVP：大部分完成
资源与证书增强：基础版完成，深度能力未完成
多轮动态观测：基础编排完成，策略化调度未完成
无头浏览器深度检测：未完成
任务化/异步调度：未完成
代理来源与基础历史分析：表已建，业务未启用
蜜罐管理与策略配置：表和展示有雏形，管理能力未完成
证据库与原始证据文件管理：未完成或仅有摘要索引
前端研究平台：主体页面已完成，配置/证据/深度交互仍未完成
```

## 2. 第 0 阶段结构稳定化完成度

规划位置：

- `docs/project-architecture-audit.md`
- `docs/next-thread-build-prompt.md`

### 2.1 已完成

1. **状态枚举基本固化**
   - 已有 `Applicability`、`ExecutionStatus`、`RiskLevel`、`ScanOutcome`、`BehaviorClass` 等稳定英文枚举。
   - 前端也有对应类型和中文展示映射。

2. **检测结果语义已扩展**
   - 当前 pipeline 已区分：
     - `completed`
     - `skipped`
     - `not_applicable`
     - `error`
     - `timeout`
   - 死代理进入安全检测时会记录为 `skipped`，而不是静默丢弃。
   - 不支持某 checker 的代理会记录为 `not_applicable`。

3. **批次与记录模型已建立**
   - 已有 `security_scan_batches`。
   - 已有 `security_scan_records`。
   - 已有 `security_behavior_events`。
   - pipeline 会创建批次，并为基础 checker 和安全 checker 写入记录。

4. **失败、跳过、不可适用记录已能保存**
   - `CheckPipeline` 会为 disabled、unsupported、previous blocking failed、proxy not usable 等状态生成记录。
   - 这解决了规划里提到的“未检测不能当成安全”的核心语义问题。

5. **前端结构已经拆分**
   - `daili/src/app/`
   - `daili/src/api/`
   - `daili/src/components/`
   - `daili/src/features/`
   - `daili/src/types/`
   - 已经不再把主要业务都堆在单个 `App.tsx` 中。

6. **中文乱码大体已修复**
   - 当前 README 和前端页面文本能以 UTF-8 正常显示。
   - 前端内部状态值使用英文枚举，展示层映射中文。

7. **基础回归测试已有覆盖**
   - 已有 `tests/test_phase0_semantics.py`。
   - 已有安全 API、资源完整性、MITM、动态观测、蜜罐、DOM/traffic checker 等测试。

### 2.2 部分完成

1. **Repository 初始化时自动改表问题**
   - 当前 `storage/mysql/proxy_repository.py` 中已经没有明显的运行时自动 `ALTER TABLE`。
   - 但仍需要确认历史版本中的隐式补列逻辑是否完全清理干净，以及部署流程是否明确要求先执行 migrations。

2. **每阶段检测记录持久化**
   - 基础 checker 和安全 checker 都会进入 `security_scan_records`。
   - 但基础检测历史专表 `proxy_check_records` 尚未被业务逻辑写入。
   - 也就是说，安全研究记录已落地，传统代理可用性历史还没有真正启用独立表。

3. **结构化字段回写**
   - 规划中建议逐步避免 pipeline 通过 checker 名称分支回写 `ProxyModel`。
   - 当前 `_apply_check_result()` 仍然依赖 checker 名称，例如 `tcp_checker`、`http_checker`、`business_availability_checker`。
   - 这对当前规模可用，但后续 checker 增多后仍会变脆。

### 2.3 未完成

1. **正式任务化执行模型**
   - 当前 `/api/refresh` 和 `/api/security/scans` 仍然是同步执行。
   - 规划中提到的任务队列、后台任务、批次状态轮询、取消任务、任务预算尚未实现。

2. **检测策略配置**
   - 当前 checker 是默认加载和顺序执行。
   - 还没有独立的 scan policy 配置层来决定哪些代理进入深度检测、哪些只做轻量检测。

3. **完整漏斗调度器**
   - 当前有 `funnel_stage` 字段和若干 checker 的阶段编号。
   - 但还没有一个独立的漏斗策略引擎来统一控制每层进入条件、抽样比例、预算和跳过原因。

## 3. 安全检测能力完成度

规划位置：

- `docs/next-build-plan.md`
- `docs/next-thread-build-prompt.md`

### 3.1 已完成

1. **蜜罐目标层**
   - 已有 `honeypot/` 模块。
   - 提供静态 HTML 页面、复杂 HTML 页面、CSS、JS、文本资源、SVG、下载样本。
   - 已有 `/honeypot/manifest`。
   - 已有 `/api/security/honeypot/manifest`。

2. **直连与代理双路径访问**
   - 已有 `security/access/client.py`。
   - 支持 direct / proxy 访问。
   - 记录状态码、响应头、body hash、body size、MIME、耗时、跳转链、错误类型。
   - 有 body 大小上限，避免无限保存响应内容。

3. **HTML / DOM 差分基础能力**
   - 已有 `security/diff/html_diff.py`。
   - 已有 `security/plugins/honeypot_checker.py`。
   - 已有 `security/plugins/dom_diff_checker.py`。
   - 能识别 hash 变化、状态码变化、新增 script、iframe、外部资源、事件属性、表单 action 改写等风险。

4. **风险规则基础能力**
   - 已有 `security/rules/risk_rules.py`。
   - 能输出结构化风险标签和风险等级。

5. **资源完整性检测基础能力**
   - 已有 `security/plugins/resource_integrity_checker.py`。
   - 能读取蜜罐 manifest。
   - 能对资源做 direct/proxy 访问。
   - 能比较 hash、大小、MIME、状态码。
   - 能写入 `security_resource_observations`。
   - 能生成资源替换类行为事件。

6. **HTTPS / SOCKS MITM 基础能力**
   - 已有 `security/access/cert_probe.py`。
   - 已有 `security/plugins/mitm_checker.py`。
   - 能采集 direct/proxy 两侧证书摘要。
   - 能比较证书指纹、issuer、subject、自签名、mismatch。
   - 能写入 `security_certificate_observations`。
   - 能生成 `mitm_suspected` 事件。

7. **多轮动态观测雏形**
   - 已有 `security/observation/dynamic_observation.py`。
   - 支持多 target、多 User-Agent、多 round 的同步执行。
   - 已有 `traffic_analysis_checker` 对多轮异常进行归纳。

8. **行为分类与安全评分**
   - 已有 `scoring/security_scorer.py`。
   - 能输出：
     - `security_risk`
     - `security_score`
     - `behavior_class`
     - `risk_tags`
     - `anomaly_trigger_count`
     - `security_check_count`
     - `anomaly_trigger_rate`
     - `has_content_tampering`
     - `has_resource_replacement`
     - `has_mitm_risk`

### 3.2 部分完成

1. **轻量蜜罐检测依赖环境变量**
   - `honeypot_checker` 需要 `HONEYPOT_BASE_URL`。
   - 不配置时会记录为 `skipped`。
   - 这符合语义要求，但默认运行 `main.py` 时不一定真的执行蜜罐内容对比。

2. **资源完整性检测依赖蜜罐 URL**
   - 不配置 `HONEYPOT_BASE_URL` 时会跳过。
   - 资源检测已实现基础版，但没有更复杂的 JS 可疑片段扫描。

3. **MITM 检测依赖 HTTPS 目标**
   - 需要 `MITM_TARGET_URL` 或 `HONEYPOT_HTTPS_URL`。
   - HTTP-only 代理会正确跳过或记录为不适用。
   - 但自建 HTTPS 蜜罐还没有完整落地，当前更多依赖外部或手动配置 HTTPS 目标。

4. **多轮检测有执行器，但不是默认策略**
   - `DynamicObservationRunner` 可以跑多轮。
   - 但 `main.py` 默认完整批量流程没有按策略自动挑选可疑代理进入多轮观测。
   - 也没有预算、抽样、触发条件配置。

5. **行为分类依赖已有 checker 输出**
   - 安全评分器能汇总风险。
   - 但如果蜜罐、MITM、资源检测因配置缺失而跳过，评分会变成较弱的 `unknown` 或低信息结果。

### 3.3 未完成

1. **无头浏览器深度检测**
   - 规划中的第 8 层没有实现。
   - 当前仓库没有 Playwright、Selenium 或等价浏览器检测模块。
   - 未实现：
     - 页面完整加载后 DOM 采集
     - JS 执行后 DOM 采集
     - 浏览器网络请求记录
     - 控制台错误记录
     - 页面截图
     - 点击、滚动、表单输入
     - browser 级 scan depth

2. **浏览器专属攻击识别**
   - 未实现 `browser_only_anomaly`。
   - 未实现 JS 执行后才出现的注入、跳转、资源加载异常检测。

3. **复杂 DOM 差分**
   - 当前 DOM/HTML 风险规则是基础版。
   - 未完整实现：
     - 隐藏元素细粒度检测
     - 广告容器识别
     - 弹窗容器识别
     - 链接 href 改写检测
     - 图片/脚本/CSS 资源地址替换的 DOM 级解释
     - 原有关键节点缺失检查
     - manifest 中 required selector / forbidden tags / forbidden attrs 的完整规则使用

4. **文本差分模块**
   - 规划中建议 `security/diff/text_diff.py`。
   - 当前没有独立 text diff 模块。
   - 目前更多是 hash、状态和结构化 HTML 线索。

5. **更完整的资源恶意规则**
   - 未实现 JS 内容可疑片段扫描，例如 `eval`、`document.write`、可疑 redirect。
   - 未实现真实的下载篡改风险分类扩展，例如 `suspicious_download_swap` 的更细规则。

6. **证书链深度分析**
   - 当前有基础证书比对。
   - 未完整实现：
     - 证书链完整性分析
     - 公钥算法与公钥摘要查询聚合
     - unknown issuer 的可信根判断
     - TLS validation bypass 级别判断
     - SOCKS5 DNS 解析位置影响分析

7. **能力路由层**
   - checker 自己有 `supports()`。
   - 但没有独立 capability router 汇总代理能力、稳定性、历史风险、来源风险来决定检测深度。

8. **漏斗调度层**
   - 有 `funnel_stage` 字段。
   - 没有完整“第 0 到第 9 层”的统一调度器。
   - 没有按成本从低到高自动缩小检测对象范围。

9. **高风险来源和低稳定代理抽样策略**
   - 规划建议对低稳定代理保留小比例抽样进入轻量安全检测。
   - 当前未实现抽样策略。

10. **伦理边界和目标白名单**
   - 规划要求只访问自建蜜罐或明确允许目标。
   - 当前通过环境变量手动指定目标，但没有目标白名单、策略校验或防误扫保护。

## 4. 九层漏斗完成度

规划漏斗为：

```text
第 0 层：采集与去重
第 1 层：基础连通性检测
第 2 层：协议与能力识别
第 3 层：轻量蜜罐与 hash 对比
第 4 层：DOM / HTML 结构化差分
第 5 层：资源完整性检测
第 6 层：HTTPS / SOCKS MITM 检测
第 7 层：多轮条件触发检测
第 8 层：无头浏览器深度检测
第 9 层：行为分类与安全评分
```

当前完成度：

| 层级 | 状态 | 说明 |
| --- | --- | --- |
| 第 0 层：采集与去重 | 已完成 | `ProxyWorkflowService`、collector、Deadpool、本地文件源已可用。 |
| 第 1 层：基础连通性检测 | 已完成 | `TcpChecker` 已实现。 |
| 第 2 层：协议与能力识别 | 已完成 | HTTP、HTTPS、SOCKS5 checker 和 aggregator 已实现。 |
| 第 3 层：轻量蜜罐与 hash 对比 | 部分完成 | `HoneypotChecker` 已实现，但依赖 `HONEYPOT_BASE_URL`，默认未必执行真实对比。 |
| 第 4 层：DOM / HTML 结构化差分 | 部分完成 | 基础 DOM 风险规则已实现，复杂 DOM/manifest 规则未完整实现。 |
| 第 5 层：资源完整性检测 | 部分完成 | hash/size/MIME/status 已实现，复杂恶意 JS/下载规则未完成。 |
| 第 6 层：HTTPS / SOCKS MITM 检测 | 部分完成 | 基础证书比对已实现，证书链深度分析和自建 HTTPS 蜜罐未完整完成。 |
| 第 7 层：多轮条件触发检测 | 部分完成 | 有同步多轮 runner 和归纳 checker，但没有自动策略化调度。 |
| 第 8 层：无头浏览器深度检测 | 未完成 | 没有浏览器自动化检测模块。 |
| 第 9 层：行为分类与安全评分 | 已完成基础版 | `SecurityScorer` 已实现，但依赖前面检测信号质量。 |

结论：九层漏斗不是全部完成。当前完成的是“漏斗记录语义 + 多个核心检测层的基础版”，不是完整自动漏斗系统。

## 5. 数据库规划完成度

规划位置：

- `docs/database-design-plan.md`

### 5.1 已完成

1. **migration 目录已建立**
   - 已有 `migrations/001` 到 `migrations/011`。

2. **规划中的主要表结构都已有 SQL**
   - `security_scan_batches`
   - `security_scan_records`
   - `security_behavior_events`
   - `security_evidence_files`
   - `security_certificate_observations`
   - `security_resource_observations`
   - `proxy_sources`
   - `proxy_check_records`
   - `honeypot_targets`
   - `honeypot_request_logs`

3. **安全批次与安全记录 repository 已实现**
   - `MySQLSecurityRepository` 能创建 batch、保存 record、finish batch。

4. **行为事件、证据、资源观测、证书观测写入已实现**
   - `save_behavior_event()`
   - `save_evidence_file()`
   - `save_resource_observation()`
   - `save_certificate_observation()`

5. **蜜罐请求日志写入已实现**
   - `MySQLHoneypotRepository.log_request()` 已能写入 `honeypot_request_logs`。

6. **安全查询 repository 已实现大量聚合查询**
   - 包括 overview、batch、events、geo、trend、risk distribution、resource/certificate detail 等。

### 5.2 部分完成

1. **表结构不等于数据库已实际迁移**
   - 仓库里有 SQL 文件。
   - 但当前工作区无法仅凭代码确认目标 MySQL 中是否已经全部执行。
   - 如果数据库没有执行 migrations，运行时仍会失败。

2. **proxies 主表扩展字段**
   - SQL 中已有 `001_extend_proxies_security_fields.sql`。
   - `ProxyModel` 和 `MySQLProxyRepository` 已使用安全汇总字段。
   - 但需要确认线上/本地实际数据库表已执行该 migration。

3. **证据文件表**
   - 代码会保存 `inline://security_scan_records/.../evidence` 形式的摘要索引。
   - 但规划中的本地 evidence 目录、完整 HTML 快照、DOM diff 文件、network log、cert.json 文件管理尚未完整实现。

4. **honeypot_targets 表**
   - SQL 已有。
   - 但当前蜜罐目标主要仍是代码中固定 manifest。
   - 表没有真正成为蜜罐目标管理的数据源。

5. **honeypot_request_logs 外键**
   - 表设计包含 target 外键。
   - 当前 `log_request()` 写入 path、hash、headers 等，但没有明显解析并填充 `target_id`。
   - 如果表约束要求 target_id 或后续查询依赖 target_id，仍需补齐映射。

### 5.3 未完成

1. **proxy_sources 业务启用**
   - 表已建。
   - 当前代理来源仍主要来自 `DefaultProxySourceProvider` 的代码定义。
   - 未实现：
     - 来源入库
     - 来源启用/禁用
     - 来源质量统计
     - 前端来源管理

2. **proxy_check_records 业务启用**
   - 表已建。
   - 当前没有看到基础检测历史写入该表的业务逻辑。
   - 传统代理可用性历史、长期稳定性分析尚未启用。

3. **正式迁移执行器**
   - 有 SQL 文件。
   - 没有 Alembic 或自定义 migration runner。
   - README 仍要求用户手动按顺序执行 SQL。

4. **数据保留策略**
   - 规划建议保留最近 30-90 天基础记录、长期保存行为事件等。
   - 当前没有自动归档、清理、压缩或导出策略。

5. **证据存储策略完整落地**
   - 未完成完整证据目录：
     - `evidence/security/{batch_id}/{proxy_ip}_{port}/`
     - `direct.html`
     - `proxy.html`
     - `dom_diff.json`
     - `network_log.json`
     - `cert.json`

## 6. API 规划完成度

规划位置：

- `docs/next-build-plan.md`
- `docs/frontend-redesign-plan.md`

### 6.1 已完成

1. **代理基础 API**
   - `GET /api/proxies`
   - `GET /api/proxies/<ip>:<port>`
   - `DELETE /api/proxies/<ip>:<port>`
   - `GET /api/stats`
   - `GET /api/filters`
   - `POST /api/refresh`

2. **安全总览 API**
   - `GET /api/security/overview`

3. **安全代理 API**
   - `GET /api/security/proxies`
   - `GET /api/security/proxies/<ip>:<port>`
   - `GET /api/security/proxies/<ip>:<port>/history`
   - `GET /api/security/proxies/<ip>:<port>/events`
   - `POST /api/security/proxies/<ip>:<port>/scan`

4. **批次 API**
   - `GET /api/security/batches`
   - `GET /api/security/batches/<batch_id>`
   - `POST /api/security/batches`
   - 兼容 `/api/security/scans`

5. **事件 API**
   - `GET /api/security/events`
   - `GET /api/security/events/<event_id>`

6. **地理聚合 API**
   - `GET /api/security/geo`
   - `GET /api/security/geo/<country>`

7. **分析 API**
   - `GET /api/security/stats/behavior`
   - `GET /api/security/stats/risk-trend`
   - `GET /api/security/analytics/trend`
   - `GET /api/security/analytics/event-types`
   - `GET /api/security/analytics/risk-distribution`

8. **蜜罐 manifest API**
   - `GET /api/security/honeypot/manifest`

### 6.2 部分完成

1. **同步批次创建**
   - `POST /api/security/batches` 会同步运行扫描。
   - 返回 `batchId`。
   - 但没有异步状态流转、后台队列、取消或进度查询机制。

2. **错误模型**
   - API 能返回一些结构化 error，例如 `scan_batch_not_found`。
   - 但还没有统一错误响应模型、错误 code 体系和前端统一处理策略。

3. **地理区域查询**
   - 已有国家/地区聚合。
   - 但国家编码、国家名、地图 TopoJSON ID 之间的映射需要继续验证稳定性。

### 6.3 未完成

1. **任务化 API**
   - 未实现：
     - 创建任务后立即返回
     - 轮询任务状态
     - 任务取消
     - 任务进度
     - 任务预算
     - 并发限制

2. **检测策略 API**
   - 未实现：
     - scan policy 列表
     - 创建策略
     - 修改策略
     - 按策略运行批次

3. **证据库 API**
   - 事件详情能看到部分 evidence files。
   - 但没有完整证据库列表、证据文件下载、原始证据查看、diff 文件查看 API。

4. **代理来源管理 API**
   - 未实现 proxy source 的 CRUD、启用/禁用、质量统计。

5. **研究数据导出 API**
   - 未实现 CSV / JSON 导出。

## 7. 前端规划完成度

规划位置：

- `docs/frontend-redesign-plan.md`

### 7.1 已完成

1. **基础重构**
   - 已有路由。
   - 已有 `AppShell`。
   - 已拆分 API client。
   - 已拆分 types。
   - 已有 loading、error、badge 等基础 UI 组件。

2. **安全总览页**
   - 已有 `SecurityOverviewPage`。
   - 已展示风险指标、行为分类、漏斗统计、趋势、协议分布、主要事件、国家风险排行、最近批次。
   - 已有多种基础图表组件：
     - `TrendLineChart`
     - `HorizontalBarChart`
     - `DonutChart`
     - `FunnelChart`

3. **代理资产列表页**
   - 已有 `ProxyListPage`。
   - 支持国家、协议、状态、安全风险、行为分类等筛选。
   - 表格中展示安全字段。

4. **代理详情页**
   - 已有 `ProxyDetailPage`。
   - 展示基础信息、安全摘要、漏斗路径、事件、批次、资源观测、证书观测、检测记录。

5. **FunnelStepper**
   - 已有 `components/security/FunnelStepper.tsx`。
   - 能展示 stage、funnel stage、执行状态、结果数量。

6. **安全事件页**
   - 已有 `SecurityEventsPage`。
   - 已有 `SecurityEventDetailPage`。
   - 支持事件列表和详情证据展示。

7. **检测批次页**
   - 已有 `SecurityBatchesPage`。
   - 能查看批次列表、批次详情、阶段统计和记录。

8. **蜜罐目标页**
   - 已有 `HoneypotTargetsPage`。
   - 能查看 manifest 中的蜜罐目标。

9. **世界地图页**
   - 已有 `WorldMapPage`。
   - 支持国家级地图、区域数据、选中区域详情、跳转代理/事件列表。

### 7.2 部分完成

1. **地图交互**
   - 已有国家级地图和区域详情。
   - 仍需确认 hover tooltip 是否完整达到规划要求：
     - 代理总数
     - 活跃数
     - 未检测数
     - 正常/可疑/恶意数量
     - 平均响应时间
     - 协议分布
     - 最高风险等级
     - 主要异常类型

2. **图表体系**
   - 已有自定义基础图表。
   - 规划中提到可以考虑 ECharts。
   - 当前没有引入 ECharts，复杂交互、缩放、联动、tooltip 能力有限。

3. **Badge 体系**
   - 有通用 `Badge` 和 labels 映射。
   - 但规划中明确命名的 `RiskBadge`、`BehaviorClassBadge`、`ExecutionStatusBadge`、`ApplicabilityBadge` 似乎没有单独组件化。

4. **空状态和错误状态**
   - 已有 `LoadingState`、`ErrorState`。
   - 但各页面的空状态、半失败状态、局部重试体验还可继续统一。

5. **“未检测不等于安全”的展示**
   - 部分页面已经有这类提示。
   - 但需要全站一致检查，尤其是列表、地图、图表 tooltip 中是否都区分 unknown / skipped / not_applicable。

### 7.3 未完成

1. **证据库页面**
   - 规划第六阶段要求证据库页面。
   - 当前没有独立 evidence library 页面。

2. **蜜罐目标管理**
   - 当前能查看 manifest。
   - 未实现新增、编辑、禁用、启用蜜罐目标。
   - 后端也未真正把 `honeypot_targets` 表作为管理源。

3. **检测策略配置**
   - 未实现策略配置页面。
   - 未实现检测深度、预算、抽样比例、目标 URL、UA 组合配置。

4. **检测批次创建表单**
   - 未看到完整前端表单用于选择代理、检测深度、策略并创建批次。
   - 当前更多是展示已有批次。

5. **研究数据导出**
   - 未实现 CSV / JSON 导出入口。

6. **完整证据 diff 查看器**
   - 未实现 HTML diff、DOM diff、资源 diff、证书 diff 的可视化对比查看器。

7. **浏览器截图查看**
   - 因为后端浏览器检测未完成，前端也没有截图/浏览器 DOM 证据展示。

8. **权限系统**
   - 规划中暂不做，当前也未实现。

## 8. 工程与运行层面未完成项

### 8.1 依赖管理

当前根目录没有看到：

1. `requirements.txt`
2. `pyproject.toml`
3. `setup.py`

这意味着 Python 依赖安装流程不够稳定。README 中写了 `pip install -r requirements.txt`，但仓库根目录没有该文件。

需要补齐：

1. Python 依赖清单。
2. 最小 Python 版本说明。
3. 测试依赖说明。
4. SOCKS 支持依赖说明，例如 `requests[socks]` 或等价方案。

### 8.2 配置命名不一致

README 中写的是：

```text
PROXYTESTER_DB_HOST
PROXYTESTER_DB_PORT
PROXYTESTER_DB_USER
PROXYTESTER_DB_PASSWORD
PROXYTESTER_DB_NAME
```

实际 `storage/mysql/connection.py` 使用的是：

```text
DB_HOST
DB_PORT
DB_USER
DB_PASSWORD
DB_NAME
```

需要统一 README 和代码，否则部署时容易连错数据库。

### 8.3 migration 执行方式

当前是手动执行 SQL。

未完成：

1. migration runner。
2. 已执行 migration 记录表。
3. 重复执行保护。
4. 迁移前备份脚本。
5. migration 状态检查命令。

### 8.4 长耗时任务运行方式

安全检测会变慢，尤其是资源、证书、多轮、浏览器检测。

当前未完成：

1. 后台任务队列。
2. worker 进程。
3. 并发预算。
4. 任务超时治理。
5. scan policy 预算。
6. 浏览器检测并发限制。

### 8.5 测试覆盖缺口

已有测试覆盖核心语义，但仍缺：

1. API 端到端集成测试连接测试数据库或 fake repository。
2. 前端组件测试。
3. 前端路由 smoke test。
4. migration SQL 自动校验。
5. 真实蜜罐 direct/proxy 对比的集成测试。
6. 证书探针更完整的异常场景测试。

## 9. 按优先级排列的未完成清单

### P0：影响当前可运行性和可信度

1. 补齐 Python 依赖文件。
2. 统一数据库环境变量命名，修正 README 或代码。
3. 确认并记录 migrations 是否已在目标 MySQL 执行。
4. 为 migration 增加最小执行/检查脚本。
5. 给 `HONEYPOT_BASE_URL`、`MITM_TARGET_URL`、`HONEYPOT_HTTPS_URL` 写清楚配置说明和默认运行效果。

### P1：补齐安全检测平台核心闭环

1. 实现正式 scan policy / capability router。
2. 实现完整漏斗调度器，统一控制每层进入条件和跳过原因。
3. 让 `main.py` 或 API 支持选择检测深度。
4. 自建 HTTPS 蜜罐目标，减少 MITM 检测对外部目标的依赖。
5. 完善 DOM/manifest 规则，真正使用 required selectors、forbidden tags、forbidden attrs。
6. 完善证据文件保存策略，落地 evidence 目录和原始证据索引。
7. 启用 `proxy_check_records`，保存基础检测历史。

### P2：补齐研究分析能力

1. 启用 `proxy_sources`，统计代理来源质量。
2. 完成证据库 API 和前端页面。
3. 完成检测批次创建表单。
4. 完成检测策略配置页面。
5. 完成 CSV / JSON 导出。
6. 完成资源/证书聚合查询和前端筛选。
7. 完成数据保留、归档和清理策略。

### P3：深度检测能力

1. 实现无头浏览器检测模块。
2. 采集浏览器渲染后 DOM。
3. 采集浏览器网络请求。
4. 采集控制台错误。
5. 支持简单点击、滚动、表单输入。
6. 支持浏览器截图证据。
7. 实现 browser-only anomaly 识别。
8. 为浏览器检测设置预算和并发限制。

### P4：产品化增强

1. 前端图表交互增强。
2. 世界地图 tooltip 和联动筛选增强。
3. 单独 Badge 组件体系。
4. 更统一的空状态、错误状态、局部重试。
5. 登录与权限控制。
6. 多用户或团队研究工作流。

## 10. 建议下一步执行顺序

如果接下来继续开发，建议按下面顺序推进：

1. **先补运行可信度**
   - 补 Python 依赖文件。
   - 统一 DB 环境变量。
   - 增加 migration 检查方式。

2. **再补安全检测策略层**
   - 做 capability router。
   - 做 scan policy。
   - 做漏斗调度器。
   - 让安全检测不是“所有 checker 顺序跑一遍”，而是“按代理能力和策略逐层推进”。

3. **然后补证据链**
   - 完整保存 direct/proxy HTML 摘要和异常样本。
   - 保存 DOM diff、resource diff、cert diff 文件。
   - 做证据库 API 和前端页面。

4. **再启用来源和历史分析**
   - 写入 `proxy_sources`。
   - 写入 `proxy_check_records`。
   - 前端增加来源质量和稳定性趋势。

5. **最后做高成本深度检测**
   - 浏览器检测。
   - 多轮策略化调度。
   - 截图、网络日志、交互行为模拟。

## 11. 简短验收视角

当前版本已经能证明：

1. 代理检测 pipeline 可以承载安全 checker。
2. 安全结果可以结构化入库。
3. 前端可以展示安全态势和漏斗记录。

当前版本还不能完全证明：

1. 系统已经实现完整九层漏斗。
2. 系统能自动按策略选择轻量/深度检测。
3. 系统能发现浏览器专属攻击。
4. 系统已经具备完整证据库和原始证据追溯能力。
5. 系统已经适合长时间、大规模、异步化安全研究任务。

因此，下一步重点不应再只是增加单个 checker，而应优先补齐“策略调度 + 证据链 + 任务化执行”这三块。它们是从安全检测 MVP 走向完整研究平台的关键缺口。
