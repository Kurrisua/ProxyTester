# ProxyTester 当前逻辑与扩展性审计

> 本文档用于承接前三份规划文档，在真正进入编码实现前，先检查当前项目已有逻辑是否完整、结构是否适合后续扩展，并给出必须先处理的结构性问题。  
> 最后更新：2026-04-17

## 1. 审计结论

当前项目已经具备代理池系统的基本骨架：

1. 已有采集、去重、基础检测、协议识别、评分、MySQL 入库、Flask API、React 前端展示等能力。
2. 后端已经出现了比较好的扩展雏形，例如 checker、security checker、scorer、repository、service 等分层。
3. 安全检测插件目录已经存在，说明项目已经预留了“安全检测能力”的入口。
4. MySQL 连接配置已经存在，并且可以连接到当前数据库 `proxy_pool`。

但是，如果要继续实现“代理安全研究平台”，当前结构还不能直接承载后续复杂能力。主要原因不是功能少，而是几个基础语义还没有稳定下来：

1. 检测结果粒度太粗，无法保存每轮、每阶段、每个 checker 的完整过程。
2. pipeline 只把“可用代理”作为主要持久化对象，不利于研究失败、异常、跳过、超时、不可适用等状态。
3. 安全插件目前还是占位逻辑，缺少统一访问结果、差分结果、证据结果和执行状态模型。
4. 数据库 schema 仍然以 `proxies` 单表为中心，并且 repository 中存在运行时自动 `ALTER TABLE` 的做法。
5. API 目前更像代理列表查询接口，还没有任务、批次、事件、历史、统计、地图等安全研究接口。
6. 前端目前偏单页看板，且存在中文乱码和单文件承载过多逻辑的问题，不适合继续堆叠复杂图表和地图。

因此，后续不建议直接开始实现 DOM diff、MITM、多轮检测或世界地图。更稳妥的顺序是先做一个“第 0 阶段结构稳定化”，再进入安全检测能力建设。

## 2. 当前已有结构

### 2.1 后端流程

当前主要流程可以概括为：

```text
采集代理
  -> 生成规范化代理列表
  -> CheckPipeline 执行基础 checker
  -> 如果代理可用，再执行 security checker
  -> scorer 汇总评分
  -> repository 保存代理最新状态
  -> API 查询代理列表、筛选项、统计数据
```

当前实现对“代理池基础管理”是可用的，但对“安全研究平台”还不够，因为安全研究需要保存过程、证据、异常事件、执行状态和跨轮次统计。

### 2.2 后端扩展点

当前已经存在以下可复用扩展点：

1. `BaseChecker`：基础检测器接口。
2. `BaseSecurityChecker`：安全检测器接口。
3. `BaseScorer`：评分器接口。
4. `CheckContext`：一次代理检测过程中的上下文。
5. `SecurityResult`：安全检测结果雏形。
6. `load_plugins()`：插件加载机制。
7. `MySQLProxyRepository`：MySQL 持久化入口。
8. `ProxyWorkflowService`：采集和检测编排入口。
9. `ProxyQueryService`：前端查询服务入口。

这些结构值得保留，但需要扩展其结果语义和持久化能力。

## 3. 主要问题

### 3.1 检测状态语义不足

当前 `CheckResult` 和 `SecurityResult` 主要表达：

1. 是否成功。
2. 风险等级。
3. 风险标签。
4. 证据摘要。
5. 错误信息。

这不足以支撑后续漏斗式检测。后续必须明确区分：

1. `planned`：该检测被计划执行。
2. `not_applicable`：该检测不适用于当前代理，例如纯 HTTP 代理不执行 HTTPS 证书比对。
3. `skipped`：该检测适用，但被策略跳过，例如只对可疑代理执行浏览器深度检测。
4. `running`：检测正在执行。
5. `completed`：检测完成。
6. `error`：检测执行失败。
7. `timeout`：检测超时。

同样，也必须明确区分“没有发现异常”和“没有执行检测”。这是后续数据库、API、前端都必须保持一致的核心语义。

### 3.2 Pipeline 持久化粒度过粗

当前检测流程更偏向保存代理的最新状态。这个模型对代理池展示足够，但对安全研究不够。

需要调整为：

1. 每次运行都生成 `scan_batch`。
2. 每个代理在批次中生成多条 `scan_record`。
3. 每个安全异常生成独立 `behavior_event`。
4. 证书、资源、响应摘要、DOM 差分等证据通过独立表或证据文件索引保存。
5. `proxies` 主表只保存最新汇总状态。

特别需要注意：失败代理、不可用代理、被跳过代理也有研究价值，不能只保存 alive proxies。

### 3.3 Security checker 仍是占位层

当前安全插件目录已经存在，但真实能力尚未落地。后续不应该直接把复杂逻辑全部写进三个插件文件里，而应该先拆出底层模块：

```text
security/access/
security/diff/
security/rules/
security/certificates/
security/resources/
honeypot/
```

插件本身只负责调度这些模块，并把结果封装为统一的安全记录。这样后续新增检测能力时，不会让单个 checker 文件变得越来越大。

### 3.4 Checker 结果回写方式偏脆弱

当前 pipeline 对不同 checker 的结果回写依赖 checker 名称和固定分支逻辑。这在基础检测阶段可以工作，但后续安全检测器数量增多后会变得脆弱。

建议后续逐步改为：

1. checker 输出结构化字段。
2. pipeline 不直接理解每个 checker 的内部含义。
3. 由 checker 自己或专门的 result applier 负责把结果映射到 `ProxyModel`。
4. 安全检测明细统一写入 `security_scan_records` 和 `security_behavior_events`。

### 3.5 数据库迁移机制缺失

当前 repository 初始化时会尝试补充列。这适合早期开发，不适合后续完整 schema。

后续需要：

1. 停止在 repository 初始化时自动执行 schema 修改。
2. 新增明确的 SQL migration 文件。
3. 一次性创建完整安全研究表结构。
4. 建表前备份当前数据库。
5. 建表或重建表前必须获得用户明确授权。

### 3.6 API 缺少任务化与历史查询

当前 `/api/refresh` 是同步触发完整流程，这在采集和基础检测阶段尚可接受，但安全检测会包含多轮访问、证书采集、资源对比、浏览器模拟，耗时和失败场景都会明显增加。

后续 API 应该逐步引入：

1. 批次创建。
2. 批次状态查询。
3. 批次详情查询。
4. 代理安全历史。
5. 安全事件列表。
6. 地理聚合统计。
7. 趋势统计。

第一版可以仍然同步执行最小闭环，但数据库和 API 命名必须按任务化模型设计，避免后续推倒重来。

### 3.7 前端不适合继续单文件堆叠

当前前端已经承担代理列表、筛选、统计、刷新等功能。后续还要增加：

1. 安全总览。
2. 风险趋势折线图。
3. 行为类型柱状图。
4. 漏斗图。
5. 地理分布地图。
6. 代理详情页。
7. 行为事件列表。
8. 检测批次详情。

如果继续把逻辑堆在单个 `App.tsx`，维护成本会快速失控。因此前端重构不是美化任务，而是后续功能可持续扩展的前置条件。

### 3.8 中文编码与用户展示语义需要修复

当前后端返回值和前端展示文本中存在中文乱码迹象。这个问题应在前端重构和 API 扩展前优先处理。

建议：

1. 源码文件统一为 UTF-8。
2. API 内部状态值使用英文枚举，例如 `alive`、`slow`、`dead`。
3. 前端负责把状态映射为中文展示文本。
4. 数据库中保存稳定枚举值，不保存容易受编码影响的展示文案。
5. 测试断言优先检查枚举值，而不是检查中文展示文案。

## 4. 当前结构中值得保留的部分

虽然需要整改，但当前项目并不是要推倒重来。以下部分建议保留并扩展：

1. 保留 `ProxyWorkflowService` 作为高层编排入口，但增加批次模型和任务结果。
2. 保留 `CheckPipeline`，但扩展为支持漏斗阶段、执行状态和每条记录持久化。
3. 保留 checker/scorer 插件思想，但补充统一结果模型。
4. 保留 `ProxyModel` 作为代理最新状态对象，但不要让它承载完整检测历史。
5. 保留 Flask API，但新增安全研究相关 blueprint 或 routes。
6. 保留 Vite + React + TypeScript 前端技术栈，但重构目录结构和组件边界。

## 5. 建议新增或调整的模块边界

### 5.1 后端建议结构

建议逐步形成以下结构：

```text
honeypot/
  app.py
  targets.py
  manifest.py
  request_logger.py

security/
  access/
    access_client.py
    access_result.py
    proxy_adapter.py
  diff/
    html_diff.py
    dom_diff.py
    resource_diff.py
  rules/
    risk_rules.py
    behavior_classifier.py
  certificates/
    certificate_observer.py
    certificate_compare.py
  resources/
    resource_observer.py
  plugins/
    honeypot_checker.py
    dom_diff_checker.py
    mitm_checker.py

storage/mysql/
  migrations/
  repositories/
    proxy_repository.py
    scan_repository.py
    event_repository.py
    evidence_repository.py
```

### 5.2 前端建议结构

建议前端改为：

```text
daili/src/
  app/
  api/
  components/
  features/
    overview/
    proxies/
    proxy-detail/
    security-events/
    scan-batches/
    world-map/
  hooks/
  lib/
  types/
```

这样图表、地图、代理详情、安全事件不会互相挤在一个文件里。

## 6. 第 0 阶段结构稳定化任务

在开始实现安全检测核心能力前，建议先完成以下任务：

1. 固化状态枚举：检测适用性、执行状态、风险等级、行为类别。
2. 建立数据库 migration 目录和执行方式。
3. 准备完整 MySQL schema，不再依赖 repository 运行时补列。
4. 新增 scan batch、scan record、behavior event 的 repository 雏形。
5. 让 pipeline 能生成批次记录和每阶段检测记录。
6. 保存失败、超时、跳过、不可适用的检测记录。
7. 修复 API 和前端中的中文乱码。
8. 前端拆出 API client、types、基础页面结构。
9. 为现有基础检测流程补一组最小回归测试。
10. 形成最小安全检测闭环：蜜罐目标、直连访问、代理访问、hash 对比、记录入库。

第 0 阶段的目标不是完成所有功能，而是防止后续功能建立在不稳定的语义和表结构上。

## 7. 与其他文档的配合关系

本文档是“实施前审计与整改清单”，其他三份文档分别负责功能规划、数据库设计和前端设计：

1. `docs/next-build-plan.md`：定义后续安全检测平台的总体能力。
2. `docs/database-design-plan.md`：定义 MySQL 表结构和持久化设计。
3. `docs/frontend-redesign-plan.md`：定义前端重构、图表和世界地图规划。
4. `docs/next-thread-build-prompt.md`：指导下一个线程如何基于这些文档进行实现。

后续实现线程应先阅读本文档，再阅读其他三份规划。原因是本文档指出了当前代码和规划之间的落差，能避免下一步直接在旧结构上堆复杂功能。

## 8. 推荐实施顺序

推荐顺序如下：

```text
当前结构审计
  -> 第 0 阶段结构稳定化
  -> 完整数据库 schema 与 migration
  -> 检测批次与记录持久化
  -> 蜜罐与双路径访问
  -> HTML / DOM / 资源 / 证书检测
  -> 风险规则与行为事件
  -> API 扩展
  -> 前端重构
  -> 图表和世界地图
  -> 多轮检测与浏览器模拟
```

其中数据库 schema 可以一次性建全，但业务功能应分阶段启用。这样既满足“一次建好表，减少后续改表风险”的需求，也避免一次性实现过多逻辑造成不可控复杂度。

## 9. 最重要的判断标准

后续每次实现前，都可以用下面几个问题检查方案是否可靠：

1. 这个检测是否明确记录了适用性？
2. 这个检测是否明确记录了执行状态？
3. 失败、跳过、超时、不可适用是否会被保存？
4. 代理主表是否只保存最新汇总，而不是塞入大量过程数据？
5. 安全事件是否可以追溯到具体批次、具体代理、具体检测记录？
6. 前端展示的是可解释结论，还是只在堆字段？
7. 这次改动是否让后续新增 checker、API、页面更容易？

如果答案是否定的，就应该先调整结构，再继续实现具体功能。
