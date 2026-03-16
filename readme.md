# ProxyTester

一个以 Python + Flask + MySQL 为后端、React + TypeScript 为前端的代理检测与管理系统。  
系统支持从文件加载代理，执行多阶段检测（连通性、协议、匿名性、地理位置、业务可用性、安全插件、评分），并通过 API 提供查询与管理能力。

## 1. 项目目标

`ProxyTester` 解决的是“代理是否可用、可用于什么场景、风险如何、如何筛选”的问题。核心目标：

- 批量检测代理可用性（多线程）
- 输出可读的质量评分与安全风险标签
- 持久化到 MySQL，支持分页、筛选、排序
- 提供前端面板用于查看和操作代理数据

---

## 2. 当前代码结构与模块作用

> 下方是按“职责域”组织的说明，重点覆盖当前主流程中实际使用的模块。

### 2.1 启动入口层

- `main.py`
  - 命令行入口，走完整检测流程（读取 `collectors/data/lastData.txt` -> 转换 JSON -> 检测 -> 输出结果）。
- `api.py`
  - Flask API 入口，启动 HTTP 服务，供前端调用。
- `api/app_factory.py`
  - Flask 应用工厂，注册 CORS 和路由蓝图。
- `api/routes/proxy_routes.py`
  - API 路由定义：代理列表、筛选项、统计、高质量代理、删除、刷新检测。

### 2.2 服务层（业务编排）

- `services/proxy_check_service.py`
  - 检测服务门面。
  - 负责：
    - 从文件收集代理（通过 `FileProxyCollector`）
    - 构建检测流水线（checkers + security checkers + scorers）
    - 批量执行检查并按需写库
- `services/proxy_query_service.py`
  - 查询服务门面。
  - 负责：
    - 读取仓储层数据
    - 转换 API 返回结构（状态文案、协议数组、成功率等）
    - 删除代理

### 2.3 调度层（流水线执行）

- `scheduler/check_pipeline.py`
  - 核心调度器。
  - 负责：
    - 按 `order` 顺序执行普通检测器
    - 执行阻断逻辑（`blocking=True` 且失败则停止后续普通检测）
    - 对可用代理执行安全插件
    - 执行评分器
    - 可选写入仓储层
  - 并发模型：
    - `ThreadPoolExecutor`，批量代理并发检测（`max_workers` 可配置）

### 2.4 核心抽象层（可扩展基础）

- `core/interfaces/checker_base.py`
  - 扩展接口定义：
    - `BaseChecker`：普通检测器
    - `BaseSecurityChecker`：安全检测插件
    - `BaseScorer`：评分器
    - `BaseProxyRepository`：仓储接口
- `core/interfaces/proxy_collection.py`
  - 代理采集层核心抽象：
    - `ProxySourceDefinition`：统一描述代理来源（`kind/location/metadata`，便于扩展到文件、API、插件等）
    - `BaseProxySourceProvider`：来源提供器接口
    - `BaseProxyCollector`：采集器接口
    - `BaseProxyDataTransformer`：数据格式转换接口
- `core/context/check_context.py`
  - 检测上下文容器：聚合单个代理在整个流水线中的中间结果。
- `core/models/proxy_model.py`
  - 代理核心实体 `ProxyModel`，包含协议能力、匿名性、地理信息、评分、安全风险等字段。
- `core/models/results.py`
  - 标准结果对象：
    - `CheckResult`
    - `SecurityResult`
    - `ScoreResult`

### 2.5 检测器层（普通检测）

- 注册入口：`checkers/registry.py`
  - `build_default_checkers()` 返回默认检测链顺序：
    1. `TcpChecker`
    2. `Socks5Checker`
    3. `HttpsChecker`
    4. `HttpChecker`
    5. `ProtocolAggregator`
    6. `AnonymityChecker`
    7. `ExitGeoChecker`
    8. `IpGeoFallbackChecker`
    9. `BusinessAvailabilityChecker`

- `checkers/connectivity/tcp_checker.py`
  - TCP 端口连通性测试，是首个阻断检查（失败后通常停止后续普通检测）。

- `checkers/protocol/`
  - `socks5_checker.py`：SOCKS5 握手检测
  - `https_checker.py`：CONNECT 隧道可用性检测
  - `http_checker.py`：HTTP 出口可用性检测（多目标探测）
  - `protocol_aggregator.py`：汇总协议能力并更新 `proxy_type`

- `checkers/anonymity/anonymity_checker.py`
  - 通过请求目标服务判断匿名级别（高匿/匿名/透明）。

- `checkers/geo/`
  - `exit_geo_checker.py`：通过代理出口查询地理位置（优先）
  - `ip_geo_fallback_checker.py`：出口 GEO 失败时按代理 IP 回退查询

- `checkers/business/business_availability_checker.py`
  - 业务目标可达性测试（Google/Baidu/GitHub）并计算 `business_score`。

### 2.6 安全插件层

- 注册入口：`security/registry.py`
  - 通过 `utils/plugin_loader.py` 自动扫描 `security/plugins` 下继承 `BaseSecurityChecker` 的类。
- 默认插件目录：`security/plugins/`
  - `honeypot_checker.py`
  - `dom_diff_checker.py`
  - `mitm_checker.py`
  - `traffic_analysis_checker.py`
- 当前状态：
  - 插件接口与加载机制已完整；默认插件实现偏占位（placeholder），便于后续替换为真实策略。

### 2.7 评分层

- `scoring/composite_scorer.py`
  - 默认评分器集合构建入口。
- `scoring/quality_scorer.py`
  - 质量分（0-100）：成功率 + 响应耗时 + 业务分。
- `scoring/security_scorer.py`
  - 汇总安全结果，给出 `security_risk`、`security_flags`、`security_evidence`。

### 2.8 采集与工具层

- `collectors/defaults.py`
  - 采集层默认路径定义（`collectors/data/lastData.txt` 与 `collectors/data/lastData.json`）。
- `collectors/source_provider.py`
  - 默认来源提供器，返回可扩展的来源定义（当前默认来源为 `lastData` 文件）。
- `collectors/file_collector.py`
  - 文件采集器实现，支持直接传路径或传 `ProxySourceDefinition`。
- `collectors/transformers/last_data_to_json.py`
  - `LastDataJsonTransformer`：将 `IP:PORT source_name` 文本行转换为结构化 JSON 数据集。
- `utils/http_client.py`
  - 网络请求与套接字工具封装（`requests` 代理参数、计时请求、TCP 连接等）。
- `utils/plugin_loader.py`
  - 插件动态发现与实例化。

### 2.9 存储层

- `storage/mysql/connection.py`
  - MySQL 连接工厂，读取环境变量。
- `storage/mysql/proxy_repository.py`
  - MySQL 仓储实现。
  - 负责：
    - 保存/更新代理
    - 分页筛选查询
    - 统计汇总
    - 高质量代理查询
    - 删除代理

### 2.10 前端层

- 目录：`daili/`
- `daili/src/App.tsx`
  - 主界面（统计卡片、过滤、列表、删除、刷新）。
- `daili/src/lib/api.ts`
  - 前端 API 调用封装，对接 Flask 后端。
- `daili/src/types.ts`
  - 前端数据类型定义（`ProxyNode`、`DashboardStats`）。

### 2.11 兼容与历史入口

- `check/main_check.py`
  - 兼容接口封装，内部已委托到新服务层（`ProxyCheckService`）。
- `proxy.py`、`sql.py`
  - 兼容别名导出（便于旧调用方式继续工作）。

---

## 3. 检测流程（端到端）

1. 读取代理源（默认 `collectors/data/lastData.txt`）  
2. 构建 `CheckPipeline`  
3. 多线程执行普通检测器链  
4. 对“可用代理”执行安全插件  
5. 执行评分器写回模型  
6. `save_to_db=True` 时写入 MySQL  
7. API 层查询并返回前端结构化数据

---

## 4. 环境准备与启动

## 4.1 依赖要求

- Python 3.9+
- Node.js 18+
- MySQL 5.7+

## 4.2 安装依赖

后端：

```bash
pip install flask flask-cors pymysql requests
```

前端：

```bash
cd daili
npm install
```

## 4.3 初始化数据库

```sql
CREATE DATABASE proxy_pool CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE proxy_pool;

CREATE TABLE proxies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    port INT NOT NULL,
    source VARCHAR(128) DEFAULT 'unknown',
    country VARCHAR(64),
    city VARCHAR(64),
    proxy_type VARCHAR(32),
    anonymity VARCHAR(32),
    response_time FLOAT,
    business_score INT DEFAULT 0,
    success_count INT DEFAULT 0,
    fail_count INT DEFAULT 0,
    last_check_time DATETIME,
    is_alive TINYINT(1) DEFAULT 0,
    quality_score INT DEFAULT 0,
    security_risk VARCHAR(32) DEFAULT 'unknown',
    UNIQUE KEY idx_ip_port (ip, port),
    INDEX idx_country (country),
    INDEX idx_proxy_type (proxy_type),
    INDEX idx_is_alive (is_alive),
    INDEX idx_quality_score (quality_score)
);
```

## 4.4 数据库环境变量

Windows PowerShell:

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="3307"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_NAME="proxy_pool"
```

## 4.5 准备代理源文件（采集层）

编辑 `collectors/data/lastData.txt`，每行格式建议：

```text
IP:PORT source_name
```

例如：

```text
192.168.1.1:8080 from_file
10.0.0.1:3128 api_source
```

如需生成 JSON 数据集，可执行：

```bash
python -c "from collectors import DEFAULT_LAST_DATA_PATH, DEFAULT_LAST_DATA_JSON_PATH, LastDataJsonTransformer; LastDataJsonTransformer().transform(str(DEFAULT_LAST_DATA_PATH), str(DEFAULT_LAST_DATA_JSON_PATH))"
```

输出文件：`collectors/data/lastData.json`

## 4.6 启动方式

方式 1（手动）：

```bash
# 后端 API
python api.py

# 新终端启动前端
cd daili
npm run dev
```

方式 2（脚本）：

```powershell
.\start_all.ps1
```

```cmd
start_servers.bat
```

---

## 5. API 概览

- `GET /api/proxies`
  - 分页列表 + 过滤 + 排序。
- `GET /api/filters`
  - 返回可筛选国家、协议类型等。
- `GET /api/stats`
  - 返回统计摘要。
- `GET /api/proxies/high-quality`
  - 返回高质量代理。
- `DELETE /api/proxies/{ip}:{port}`
  - 删除指定代理。
- `POST /api/refresh`
  - 重新加载文件并触发全量检测。

---

## 6. 如何新增组件（重点）

这里把“新增组件”拆成 6 类：普通检测器、安全插件、评分器、采集器、仓储实现、前端组件。  
每一类都给出最小步骤、接入点和示例。

### 6.1 新增普通检测器（`BaseChecker`）

适用于：新增一个检测阶段，例如“端口指纹识别”“TLS 特征检测”等。

步骤：

1. 在 `checkers/` 下选择合适子目录（或新建子目录）创建文件，例如 `checkers/protocol/tls_checker.py`。
2. 继承 `BaseChecker`，实现 `supports()` 和 `check()`。
3. 设定 `name`、`stage`、`order`、`blocking`。
4. 在 `checkers/registry.py` 的 `build_default_checkers()` 中注册实例，并放入合适顺序。
5. 如需把结果写入模型，在 `scheduler/check_pipeline.py` 的 `_apply_check_result()` 中增加对 `checker_name` 的处理。
6. 运行 `python main.py` 或 `POST /api/refresh` 验证。

示例：

```python
from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult


class TlsChecker(BaseChecker):
    name = "tls_checker"
    stage = "protocol"
    order = 35
    blocking = False

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_alive

    def check(self, context: CheckContext) -> CheckResult:
        # TODO: 你的检测逻辑
        ok = False
        return CheckResult(
            checker_name=self.name,
            stage=self.stage,
            success=ok,
            metadata={"tls_supported": ok},
        )
```

### 6.2 新增安全插件（`BaseSecurityChecker`）

适用于：新增风险检测，如证书异常、内容篡改、流量行为评分等。

步骤：

1. 在 `security/plugins/` 新建插件文件，例如 `security/plugins/tls_fingerprint_checker.py`。
2. 继承 `BaseSecurityChecker`，实现 `supports()`、`check()`。
3. 返回 `SecurityResult`，至少包含 `risk_level` 与可选 `risk_tags/evidence`。
4. 无需手动注册，`security/registry.py` 会自动加载该目录插件。
5. 运行检查后确认 `security_scorer` 能汇总你的结果。

示例：

```python
from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.results import SecurityResult


class TlsFingerprintChecker(BaseSecurityChecker):
    name = "tls_fingerprint_checker"
    order = 25

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.https or context.proxy.socks5

    def check(self, context: CheckContext) -> SecurityResult:
        # TODO: 你的检测逻辑
        suspicious = False
        return SecurityResult(
            checker_name=self.name,
            success=not suspicious,
            risk_level="medium" if suspicious else "low",
            risk_tags=["tls-mismatch"] if suspicious else [],
            evidence={"sample": "fingerprint-data"},
        )
```

### 6.3 新增评分器（`BaseScorer`）

适用于：增加新的评分维度（稳定性、地域可信度、成本分等）。

步骤：

1. 在 `scoring/` 新建评分器文件，例如 `scoring/stability_scorer.py`。
2. 继承 `BaseScorer` 并实现 `score(context)`。
3. 在 `scoring/composite_scorer.py` 的 `build_default_scorers()` 中注册。
4. 如需持久化新分值，扩展 `ProxyModel` 字段和数据库字段。

### 6.4 新增采集器（代理来源组件）

适用于：新增“文件之外”的数据源，比如 HTTP API、Redis、消息队列。

步骤：

1. 在 `collectors/` 新建采集器，如 `api_collector.py`。
2. 实现 `collect(...) -> set[ProxyModel]`。
3. 在调用侧（如 `ProxyCheckService` 或路由）增加入口并并入代理集合。
4. 对输入去重（依赖 `ProxyModel.__hash__/__eq__` 已支持 ip+port 去重）。

### 6.5 新增仓储实现（持久化组件）

适用于：替换 MySQL，为 PostgreSQL/ClickHouse/ES 等。

步骤：

1. 新建仓储类并实现 `BaseProxyRepository` 全部方法。
2. 在 `ProxyCheckService` 与 `ProxyQueryService` 注入你的仓储实例。
3. 保持返回对象仍是 `ProxyModel`（或在 service 层统一转换）。

### 6.6 新增前端组件（React）

适用于：新增页面卡片、风险详情面板、批量操作工具栏等。

步骤：

1. 在 `daili/src` 下新增组件文件（建议新增 `components/` 目录）。
2. 在组件中使用 `daili/src/lib/api.ts` 拉取数据，或先扩展 API 封装。
3. 如果后端字段变更，先同步更新 `daili/src/types.ts`。
4. 在 `App.tsx` 中挂载组件并接入状态流（过滤、分页、刷新）。
5. 本地运行 `npm run dev` 验证渲染和交互。

---

## 7. 新增组件时的工程规范建议

- `name` 唯一：检测器/插件/评分器的 `name` 不要重复。
- `order` 明确：越靠前越先执行，避免顺序冲突。
- `supports()` 尽量严格：减少无效请求和耗时。
- `metadata/evidence` 结构化：方便后续 API 和前端展示。
- 失败返回要可诊断：`error` 字段给出明确错误原因。
- 尽量避免在 checker 内直接写库：统一交给 pipeline + repository。

---

## 8. 常见问题

### Q1: 如何提高检测速度？

- 提高 `max_workers`，但注意目标站点限流和本机网络上限。
- 优化 `supports()`，让不适用检查尽早跳过。
- 缩短单次 `timeout`，并控制 `retry_times`。

### Q2: 为什么代理很多但存活率低？

- 原始源质量问题常见。
- 出口探测目标可能被地区封锁或限流。
- 某些代理只支持特定协议，需看 `protocol_aggregator` 聚合结果。

### Q3: 安全插件看起来没变化？

- 当前默认插件多为占位实现。
- 你需要在 `security/plugins` 中实现真实检测逻辑，风险评分才会拉开差异。

---

## 9. 技术栈

- 后端：Python, Flask, requests, PyMySQL
- 调度：ThreadPoolExecutor
- 前端：React, TypeScript, Vite
- 数据库：MySQL
