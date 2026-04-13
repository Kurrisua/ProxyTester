# ProxyTester

`ProxyTester` 是一个面向代理资源采集、检测、评分、入库和查询展示的一体化项目。  
项目原本已经具备“代理检测与管理”主流程，这次又把 `new/` 目录下的 Deadpool 抓取项目并入到了统一架构里，使整个系统从“仅检测已有代理”升级为“抓取 + 合并 + 检测 + 入库 + 查询”的自动化流水线。

---

## 1. 项目目的与当前已实现内容

### 1.1 项目目的

这个项目要解决的核心问题是：

- 如何从多个来源持续获得可用代理
- 如何批量判断这些代理是否真的可用
- 如何识别代理支持的协议、匿名性、地理位置和业务可用性
- 如何对代理进行统一评分并保存，供后续筛选和使用
- 如何通过 API 和前端界面方便地查看、筛选和刷新代理池

换句话说，`ProxyTester` 不只是一个“代理检查脚本”，而是一个完整的代理资产处理系统。

### 1.2 当前已经实现的能力

目前仓库里已经实现了以下能力：

- 从文本文件中读取代理列表
- 对代理进行多阶段检测
- 识别 `HTTP`、`HTTPS`、`SOCKS5` 等协议能力
- 检测匿名性、出口地理位置、业务目标可达性
- 执行安全插件检查与评分
- 将结果写入 MySQL
- 通过 Flask API 查询代理列表、统计信息和高质量代理
- 通过 React 前端页面查看代理池状态
- 集成 Deadpool 抓取项目，自动刷新额外的代理种子文件
- 将多个来源的代理合并、去重、标准化，并统一送入检测流程
- 增加了运行日志，便于排查每一步的执行状态

### 1.3 这次整合后的统一工作流

当前自动化流程如下：

1. 可选执行 Deadpool 的抓取脚本 `fir.py`
2. 读取多个代理源文件
3. 将所有代理按 `ip:port` 去重合并
4. 生成统一的标准数据集文件
5. 生成结构化 JSON 数据集
6. 执行并发检测
7. 对检测通过的代理串行写入 MySQL
8. 通过 API 和前端提供查询与刷新能力

---

## 2. 整体结构与各层次具体职能

项目整体上可以理解为七层：

1. 入口层
2. 采集层
3. 核心抽象层
4. 检测调度层
5. 评分与安全层
6. 持久化层
7. 展示与接口层

下面按目录详细说明。

### 2.1 入口层

入口层负责启动整个系统或某条具体流程。

#### `main.py`

统一命令行入口。  
现在它不再只是读取一个 `lastData.txt` 进行检测，而是负责触发完整自动化流程：

- 可选刷新 Deadpool 抓取结果
- 合并多个代理源
- 生成标准数据集和 JSON
- 执行检测
- 可选写入数据库

#### `api.py`

后端服务启动入口。  
运行后会启动 Flask API，供前端或其他脚本调用。

#### `start_all.ps1`

用于同时启动后端和前端开发环境的脚本。

#### `start_servers.bat`

Windows 下的辅助启动脚本。

---

### 2.2 采集层 `collectors/`

采集层负责定义“代理从哪里来”，以及“采集后的原始文本如何变成统一格式”。

#### `collectors/defaults.py`

定义采集相关的默认路径，包括：

- 主项目标准数据集路径
- JSON 输出路径
- Deadpool 项目目录
- Deadpool 生成的多个源文件路径

这是整个采集层的路径配置中心。

#### `collectors/source_provider.py`

定义默认代理源列表。  
当前已经纳入的源包括：

- `collectors/data/lastData.txt`
- `new/.../lastData.txt`
- `new/.../http.txt`
- `new/.../git.txt`

也就是说，这里负责告诉系统：“这次要从哪些文件里收代理”。

#### `collectors/file_collector.py`

负责真正读取代理文件，并把文本行解析成 `ProxyModel` 对象。  
目前支持的基本格式是：

```text
IP:PORT source_name
```

解析失败的行会被跳过，并记录日志。

#### `collectors/transformers/last_data_to_json.py`

把标准化后的 `lastData.txt` 转成结构化 JSON 数据集，便于后续调试、对接或展示。

#### `collectors/deadpool_runner.py`

这是这次新增的重要模块。  
它专门负责调用并入的 Deadpool 项目中的 `fir.py`，刷新 Deadpool 生成的代理种子文件。

它的职责是：

- 定位 Deadpool 项目目录
- 执行 `fir.py`
- 记录 stdout/stderr 摘要
- 记录运行耗时
- 在超时或失败时返回结构化结果

这个模块本身不做代理检测，它只负责“刷新代理源”。

---

### 2.3 核心抽象层 `core/`

核心层提供统一的数据结构和接口定义，让系统各模块能按一致方式协作。

#### `core/interfaces/`

定义系统中的抽象接口，包括：

- 代理源提供器接口
- 代理采集器接口
- 数据转换器接口
- 检测器接口
- 安全检测器接口
- 评分器接口
- 仓储接口

这一层的意义是：后续新增任何模块时，都可以沿着统一协议接入，而不是直接硬编码到业务流程里。

#### `core/models/proxy_model.py`

定义代理的核心数据对象 `ProxyModel`。  
它承载了整个系统中围绕代理的主要字段，例如：

- IP、端口、来源
- 是否存活
- 支持的协议
- 匿名性
- 国家、城市、ISP
- 响应时间
- 业务评分
- 质量评分
- 安全风险

#### `core/models/results.py`

定义每一类检查结果对象，例如：

- 普通检查结果
- 安全检查结果
- 评分结果

#### `core/context/check_context.py`

定义检测上下文。  
每个代理在整条流水线中会携带自己的上下文，逐步累积检查结果、评分结果和最终状态。

---

### 2.4 检测调度层 `scheduler/` 与 `checkers/`

这一层负责“代理怎么检测、按什么顺序检测、什么情况下终止后续检测”。

#### `scheduler/check_pipeline.py`

这是核心调度器。  
它负责：

- 按 `order` 顺序执行检测器
- 遇到阻断型失败时提前停止
- 并发执行多个代理的检测
- 在检测完成后统一执行入库

注意：目前已经修复为“检测并发、入库串行”，避免多线程共享同一个数据库连接导致异常。

#### `checkers/registry.py`

负责注册默认检测器集合。

#### `checkers/connectivity/`

负责基础连通性检测：

- TCP 是否可连

#### `checkers/protocol/`

负责协议能力检测：

- `SOCKS5`
- `HTTPS`
- `HTTP`
- 协议聚合

#### `checkers/anonymity/`

负责匿名性判断。

#### `checkers/geo/`

负责出口地理位置检测和 IP 回退地理位置检测。

#### `checkers/business/`

负责业务目标可达性检测，例如某些站点是否能通过代理访问成功。

---

### 2.5 安全与评分层 `security/`、`scoring/`

这一层负责将代理从“可用/不可用”进一步扩展为“质量好不好、风险高不高”。

#### `security/registry.py`

负责自动加载安全插件。

#### `security/plugins/`

目前包含若干安全检测插件，如：

- `honeypot_checker.py`
- `dom_diff_checker.py`
- `mitm_checker.py`
- `traffic_analysis_checker.py`

其中有些还偏占位实现，但接口和加载机制已经完整。

#### `scoring/quality_scorer.py`

根据响应时间、成功率、业务分等信息给出质量评分。

#### `scoring/security_scorer.py`

根据安全插件结果汇总风险等级和风险标记。

#### `scoring/composite_scorer.py`

负责构建默认评分器组合。

---

### 2.6 服务层 `services/`

服务层负责把底层模块编排成用户真正会调用的业务流程。

#### `services/proxy_check_service.py`

负责“给一批代理做完整检测”。  
它的职责包括：

- 构建默认检测器、评分器、安全插件
- 调用 `CheckPipeline`
- 返回存活代理
- 可选写入 MySQL

#### `services/proxy_query_service.py`

负责面向 API 的查询能力，例如：

- 分页列表
- 筛选条件
- 统计信息
- 高质量代理查询
- 删除代理

#### `services/proxy_workflow_service.py`

这是这次新增的自动化编排核心。  
它负责把原先分散的步骤串起来：

- 触发 Deadpool 刷新
- 收集多个代理源
- 合并和去重
- 回写标准数据集
- 生成 JSON
- 触发完整检测
- 可选入库

可以把它理解成当前项目的“总导演”。

---

### 2.7 持久化层 `storage/`

#### `storage/mysql/connection.py`

负责创建 MySQL 连接。

#### `storage/mysql/proxy_repository.py`

负责代理结果的数据库读写，包括：

- 保存和更新代理
- 分页查询
- 统计
- 删除

注意：现在数据库保存已经由调度器统一串行调用，避免线程安全问题。

---

### 2.8 展示与接口层 `api/`、`daili/`

#### `api/`

Flask API 层，提供标准 HTTP 接口。

重点接口：

- `GET /api/proxies`
- `GET /api/filters`
- `GET /api/stats`
- `GET /api/proxies/high-quality`
- `DELETE /api/proxies/{ip}:{port}`
- `POST /api/refresh`

其中 `/api/refresh` 已经改为触发整条自动化流程。

#### `daili/`

React + TypeScript 前端目录，用于展示代理统计信息、筛选条件和列表数据。

---

### 2.9 并入模块 `new/`

#### `new/proxyxy/Deadpool-proxypool1.5/Deadpool-proxypool1.5`

这是并入的代理抓取项目。  
它主要负责：

- 通过 `fir.py` 从公开源抓取代理列表
- 生成 `http.txt`、`git.txt`、`lastData.txt`
- 通过 `main_modify.go` 提供一个长期驻留的本地 SOCKS 转发监听能力

当前主项目自动化流程集成的是它的批量抓取部分，即 `fir.py`。  
`main_modify.go` 目前仍作为独立能力保留，不直接纳入主检测流水线。

---

## 3. 使用方法

这一部分按“最常见场景”来说明。

### 3.1 环境要求

- Python 3.9+
- Node.js 18+
- MySQL 5.7+

### 3.2 安装依赖

后端依赖：

```bash
pip install flask flask-cors pymysql requests
```

前端依赖：

```bash
cd daili
npm install
```

### 3.3 初始化数据库

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

### 3.4 配置数据库环境变量

PowerShell 示例：

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="3307"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_NAME="proxy_pool"
```

### 3.5 准备代理源文件

标准文件格式：

```text
IP:PORT source_name
```

例如：

```text
192.168.1.1:8080 from_file
10.0.0.1:3128 api_source
```

主项目标准数据文件位置：

- `collectors/data/lastData.txt`

### 3.6 运行命令行自动化流程

最完整方式：

```bash
python main.py
```

常用参数：

```bash
python main.py --skip-crawl
python main.py --skip-deadpool-sources
python main.py --skip-db
python main.py --max-workers 200
```

参数说明：

- `--skip-crawl`
  - 跳过 Deadpool 抓取刷新
- `--skip-deadpool-sources`
  - 不读取 Deadpool 生成的代理文件
- `--skip-db`
  - 做完整检测，但不把结果写入 MySQL
- `--max-workers`
  - 设置检测并发数

建议的运行顺序：

1. 先跳过抓取和入库，确认检测流程正常

```bash
python main.py --skip-crawl --skip-db --max-workers 50
```

2. 再开启入库

```bash
python main.py --skip-crawl --max-workers 50
```

3. 最后再跑完整自动化

```bash
python main.py --max-workers 50
```

### 3.7 启动 API

```bash
python api.py
```

### 3.8 启动前端

```bash
cd daili
npm run dev
```

### 3.9 一键启动前后端

```powershell
.\start_all.ps1
```

---

## 4. 新增模块的操作方法

这一部分重点说明本次新增和变化较大的模块应该怎么使用。

### 4.1 `services/proxy_workflow_service.py`

这是新的主流程编排器。  
如果你在代码里想手动调用完整自动化流程，可以这样用：

```python
from services.proxy_workflow_service import ProxyWorkflowService

summary = ProxyWorkflowService().run_automated_workflow(
    refresh_external_sources=True,
    include_deadpool_sources=True,
    max_workers=150,
    save_to_db=True,
)

print(summary)
```

返回结果中会包含：

- `refreshSummary`
- `sources`
- `sourceCount`
- `collectedCount`
- `aliveCount`
- `canonicalFile`
- `jsonFile`
- `jsonRecordCount`
- `elapsedSeconds`

适合场景：

- 你想从 Python 代码里直接触发整套自动化
- 你想后续接定时任务
- 你想在别的服务里嵌入这条流程

### 4.2 `collectors/deadpool_runner.py`

这个模块用于刷新 Deadpool 的代理种子文件。

基本用法：

```python
from collectors.deadpool_runner import DeadpoolSeedRunner

result = DeadpoolSeedRunner().run(timeout_seconds=180)
print(result)
```

它会执行：

- `new/proxyxy/Deadpool-proxypool1.5/Deadpool-proxypool1.5/fir.py`

执行完成后主要影响的文件是：

- `new/.../http.txt`
- `new/.../git.txt`
- `new/.../lastData.txt`

适合场景：

- 只想刷新抓取结果，不做检测
- 调试 Deadpool 抓取阶段是否正常

### 4.3 `collectors/source_provider.py`

如果你想新增新的代理源，最直接的方式就是在这里追加新的 `ProxySourceDefinition`。

例如你想再增加一个文件源：

```python
ProxySourceDefinition(
    name="extra_file",
    kind="file",
    location="C:/path/to/proxies.txt",
    description="Extra local proxy file",
    metadata={"format": "ip:port source_name"},
)
```

新增后，统一自动化流程会自动把它纳入合并与检测。

### 4.4 `collectors/file_collector.py`

如果新增的是“文本文件代理源”，通常不需要额外改采集逻辑，只要文件格式符合：

```text
IP:PORT source_name
```

就能直接被这个 collector 处理。

### 4.5 `collectors/transformers/last_data_to_json.py`

如果你只想把标准数据文件转成 JSON，而不跑完整检测，可以单独调用：

```bash
python -c "from collectors import DEFAULT_LAST_DATA_PATH, DEFAULT_LAST_DATA_JSON_PATH, LastDataJsonTransformer; LastDataJsonTransformer().transform(str(DEFAULT_LAST_DATA_PATH), str(DEFAULT_LAST_DATA_JSON_PATH))"
```

### 4.6 `/api/refresh` 接口

这个接口现在不是简单重新读取文件，而是执行完整自动化流程。

示例请求体：

```json
{
  "refreshCrawler": true,
  "includeDeadpoolSources": true,
  "maxWorkers": 150,
  "saveToDb": true
}
```

适合场景：

- 前端点击刷新
- 外部脚本远程触发
- 后续接入定时任务系统

### 4.7 日志模块 `utils/logging_config.py`

项目现在已经内置日志配置，默认会同时输出到：

- 控制台
- `logs/proxytester.log`

日志覆盖阶段包括：

- Deadpool 刷新
- 代理文件读取
- JSON 生成
- 批量检测
- 数据库保存
- 主流程耗时

如果你要排查流程卡住在哪一步，优先看这个日志文件。

---

## 5. 输出文件与数据流转说明

### 5.1 输入侧

当前代理输入可能来自这些文件：

- `collectors/data/lastData.txt`
- `new/.../lastData.txt`
- `new/.../http.txt`
- `new/.../git.txt`

### 5.2 中间产物

合并去重后的标准数据集：

- `collectors/data/lastData.txt`

结构化 JSON：

- `collectors/data/lastData.json`

### 5.3 日志文件

- `logs/proxytester.log`

### 5.4 数据库存储

最终检测结果会进入 MySQL 的 `proxies` 表。

---

## 6. 如何新增模块

### 6.1 新增检测器

步骤：

1. 在 `checkers/` 下新增检测器文件
2. 继承 `BaseChecker`
3. 实现 `supports()` 和 `check()`
4. 在 `checkers/registry.py` 中注册
5. 如有必要，在调度器中处理结果字段映射

### 6.2 新增安全插件

步骤：

1. 在 `security/plugins/` 下新增插件
2. 继承 `BaseSecurityChecker`
3. 实现 `supports()` 和 `check()`
4. 插件会被自动发现和加载

### 6.3 新增评分器

步骤：

1. 在 `scoring/` 下新增评分器
2. 继承 `BaseScorer`
3. 在 `scoring/composite_scorer.py` 中注册

### 6.4 新增代理源

步骤：

1. 在 `collectors/source_provider.py` 中增加源定义
2. 如果是文本文件源，通常不需要改采集器
3. 如果是新类型源，可扩展新的 collector

### 6.5 新增持久化实现

如果后续需要支持 PostgreSQL、ClickHouse 等，可以新增仓储实现并替换 `MySQLProxyRepository`。

---

## 7. 日志与故障排查

### 7.1 常见日志位置

- 控制台输出
- `logs/proxytester.log`

### 7.2 常见问题

#### Deadpool 刷新很慢

可能原因：

- 公开源响应慢
- 网络超时
- 抓取量较大

临时绕过：

```bash
python main.py --skip-crawl
```

#### 检测可以跑，但不想入库

```bash
python main.py --skip-db
```

#### 想最小化验证主流程

```bash
python main.py --skip-crawl --skip-db --max-workers 20
```

#### 数据库出错

优先检查：

- 环境变量是否正确
- MySQL 服务是否正常
- `proxy_pool.proxies` 表是否已创建

---

## 8. 当前已知限制

- Deadpool 集成的主要是批量抓取部分，长期驻留的 Go SOCKS 监听模式还未纳入统一自动化
- 某些安全插件仍偏占位实现
- 当前主要持久化目标仍是 MySQL
- 代理来源质量波动较大，最终可用率依赖外部源质量

---

## 9. 后续建议

- 把 Deadpool 的敏感配置从 `config.toml` 迁移到环境变量
- 为 `ProxyWorkflowService` 增加单元测试
- 增加定时任务或调度器，周期性运行自动化流程
- 为前端增加刷新任务状态展示
- 后续可将 Go 侧监听模式拆成独立可选服务
