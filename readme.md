# ProxyTester 使用说明

ProxyTester 是一个代理采集、检测、评分、入库、查询和可视化平台。当前版本已经从单纯的“代理可用性检测工具”升级为代理安全研究平台的基础版：系统不仅判断代理是否可用，还会记录检测批次、漏斗阶段记录、安全事件、证据、资源观测、证书观测、蜜罐访问摘要和地理聚合结果，帮助把代理从“可用/不可用”的资源对象升级为“正常/可疑/恶意”的行为研究对象。

本文重点说明如何安装、配置、初始化数据库、运行后端、运行前端、触发检测和排错。

---

## 1. 当前能力

当前仓库包含：

- 免费代理源采集、合并和去重。
- Deadpool 代理源刷新和本地文件源读取。
- 基础连通性检测。
- HTTP、HTTPS、SOCKS5 协议识别。
- 匿名性、出口地理位置和业务可用性检测。
- 基础评分和安全评分。
- MySQL 持久化。
- 检测批次、检测记录、安全行为事件、证据、资源观测、证书观测、蜜罐日志等安全研究表结构。
- Flask API 查询代理、统计、安全总览、批次、事件、国家/地区聚合和蜜罐 manifest。
- 本地蜜罐页面、资源、下载样本和表单提交入口。
- React + Vite + TypeScript + Tailwind 前端。
- 前端页面：安全总览、代理列表、代理详情、检测批次、安全事件、事件详情、蜜罐目标、世界地图。
- Python 单元测试和前端 TypeScript 检查。

当前仍然是安全研究平台的基础版，不是完整浏览器沙箱或企业级威胁情报系统。高成本浏览器模拟、更复杂的多轮攻击诱导和更细粒度地图交互仍可继续增强。

---

## 2. 目录结构

```text
ProxyTester/
  api.py                         Flask API 启动入口
  main.py                        命令行检测流水线入口
  api/                           Flask 应用工厂和路由
  checkers/                      基础代理检测器
  collectors/                    代理源读取、Deadpool 刷新、源合并
  core/models/                   核心模型、稳定英文枚举、检测结果模型
  daili/                         前端项目，Vite + React + TypeScript
  docs/                          项目规划和实施文档
  honeypot/                      本地蜜罐页面、资源和提交接口
  migrations/                    MySQL schema migration SQL
  scheduler/                     检测 pipeline
  scoring/                       基础评分和安全评分
  scripts/                       运行、诊断、兼容和 migration 检查脚本
  security/                      蜜罐、DOM、资源、MITM、动态观测等安全检测
  services/                      工作流服务、查询服务、检测服务
  storage/mysql/                 MySQL 连接和 repository
  tests/                         Python 单元测试
  third_party/                   内嵌第三方工具和离线技能包
```

---

## 3. 运行要求

建议环境：

- Windows 10/11 或兼容 PowerShell 环境。
- Python 3.10+。
- Node.js 18+。
- npm 9+。
- MySQL 8.0+。

项目当前默认数据库连接为：

```text
host: localhost
port: 3307
user: root
database: proxy_pool
charset: utf8mb4
```

默认值来自 `storage/mysql/connection.py`，可以通过环境变量覆盖：

```powershell
$env:PROXYTESTER_DB_HOST="localhost"
$env:PROXYTESTER_DB_PORT="3307"
$env:PROXYTESTER_DB_USER="root"
$env:PROXYTESTER_DB_PASSWORD="你的密码"
$env:PROXYTESTER_DB_NAME="proxy_pool"
```

兼容说明：代码仍会回退读取旧变量名 `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`，但新部署建议统一使用 `PROXYTESTER_DB_*`。

---

## 4. 快速启动

下面命令均以 PowerShell 为例。

### 4.1 进入项目目录

```powershell
cd C:\MyProjects\ProxyTester
```

### 4.2 创建并启用 Python 虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4.3 安装 Python 依赖

仓库根目录提供 `requirements.txt`：

```powershell
python -m pip install -r requirements.txt
```

其中包含 Flask API、MySQL、HTTP/SOCKS 请求支持、测试和诊断脚本依赖。SOCKS 代理访问依赖 `requests[socks]`。

### 4.4 安装前端依赖

```powershell
cd C:\MyProjects\ProxyTester\daili
npm install
cd C:\MyProjects\ProxyTester
```

---

## 5. 初始化数据库

项目使用 MySQL，schema 由 `migrations/` 下 SQL 文件维护。不要再依赖业务代码隐式 `ALTER TABLE` 来补表结构。

先检查本地 migration 文件是否齐全：

```powershell
python scripts\check_migrations.py
```

如果需要检查当前 MySQL schema 是否已经具备规划表和关键字段，可以运行只读检查：

```powershell
python scripts\check_migrations.py --check-db
```

该命令只查询 `information_schema` 和数据库版本，不会建表、改表或迁移数据。真正执行任何 SQL migration 前，必须先备份并取得明确授权。

建议按顺序执行：

```text
migrations/001_extend_proxies_security_fields.sql
migrations/002_create_security_scan_batches.sql
migrations/003_create_security_scan_records.sql
migrations/004_create_security_behavior_events.sql
migrations/005_create_security_evidence_files.sql
migrations/006_create_security_certificate_observations.sql
migrations/007_create_security_resource_observations.sql
migrations/008_create_proxy_sources.sql
migrations/009_create_proxy_check_records.sql
migrations/010_create_honeypot_targets.sql
migrations/011_create_honeypot_request_logs.sql
```

如果是已有数据库，建议先备份：

```powershell
mysqldump -h localhost -P 3307 -u root -p proxy_pool > proxy_pool_backup.sql
```

执行 migration 示例：

```powershell
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\001_extend_proxies_security_fields.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\002_create_security_scan_batches.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\003_create_security_scan_records.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\004_create_security_behavior_events.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\005_create_security_evidence_files.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\006_create_security_certificate_observations.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\007_create_security_resource_observations.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\008_create_proxy_sources.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\009_create_proxy_check_records.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\010_create_honeypot_targets.sql
mysql -h localhost -P 3307 -u root -p proxy_pool < migrations\011_create_honeypot_request_logs.sql
```

注意：

- `proxies` 主表只保存最新汇总状态。
- 完整检测过程保存到批次表、记录表、事件表、证据表、证书观测表、资源观测表和蜜罐日志表。
- 删除代理时不要轻易级联删除研究历史。

---

## 6. 启动后端 API

在项目根目录运行：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python api.py
```

默认 API 地址：

```text
http://localhost:5000
```

常用健康检查：

```powershell
curl http://localhost:5000/api/stats
curl http://localhost:5000/api/security/overview
curl http://localhost:5000/api/security/geo
curl http://localhost:5000/api/security/honeypot/manifest
```

蜜罐目标示例：

```text
http://localhost:5000/honeypot/static/basic
http://localhost:5000/honeypot/static/complex
http://localhost:5000/honeypot/assets/site.css
http://localhost:5000/honeypot/assets/site.js
http://localhost:5000/honeypot/assets/marker.svg
http://localhost:5000/honeypot/download/sample.txt
http://localhost:5000/honeypot/download/sample.zip
```

### 6.1 安全检测目标配置

安全 checker 依赖以下目标 URL。没有配置时，相关检测会记录为 `skipped`，不会被解释为安全：

```powershell
$env:HONEYPOT_BASE_URL="http://localhost:5000/honeypot/static/basic"
$env:MITM_TARGET_URL="https://你明确授权检测的 HTTPS 目标"
$env:HONEYPOT_HTTPS_URL="https://你的 HTTPS 蜜罐目标"
```

配置语义：

- `HONEYPOT_BASE_URL`：用于轻量蜜罐、DOM/HTML 差分和资源完整性检测。建议优先指向本项目自建蜜罐。
- `MITM_TARGET_URL`：用于 TLS 证书直连 vs 代理路径对比，必须是 HTTPS URL，且应为自建或明确授权目标。
- `HONEYPOT_HTTPS_URL`：HTTPS 蜜罐目标备用配置；当 `MITM_TARGET_URL` 未设置时，MITM checker 会尝试使用它。
- `HONEYPOT_TIMEOUT_SECONDS`、`MITM_TIMEOUT_SECONDS`：可选超时配置，默认均为 10 秒。

不建议默认对第三方真实站点做安全研究检测。未配置 HTTPS 目标时，MITM 检测会以 `skipped` / `not_applicable` 进入记录。

---

## 7. 启动前端

另开一个 PowerShell：

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run dev
```

默认前端地址通常是：

```text
http://localhost:3000
```

前端会请求：

```text
http://localhost:5000/api
```

如果后端端口不同，请修改 `daili/src/api/client.ts` 中的 `API_BASE_URL`。

---

## 8. 运行检测

### 8.1 命令行完整检测

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python main.py
```

该入口会执行代理采集、基础检测、安全检测、评分和入库。当前 pipeline 会生成安全检测批次，并为基础 checker 与安全 checker 记录阶段结果。失败、跳过、不适用和错误也会记录，不再只保存存活代理。

### 8.2 通过 API 刷新代理

```powershell
curl -X POST http://localhost:5000/api/refresh
```

### 8.3 触发指定代理安全扫描

```powershell
curl -X POST http://localhost:5000/api/security/proxies/127.0.0.1:8080/scan `
  -H "Content-Type: application/json" `
  -d "{\"maxWorkers\":1}"
```

### 8.4 批量触发安全扫描

```powershell
curl -X POST http://localhost:5000/api/security/scans `
  -H "Content-Type: application/json" `
  -d "{\"proxies\":[\"127.0.0.1:8080\",\"127.0.0.2:8080\"],\"maxWorkers\":4}"
```

---

## 9. 主要 API

代理基础接口：

```text
GET    /api/proxies
GET    /api/proxies/<ip>:<port>
DELETE /api/proxies/<ip>:<port>
GET    /api/stats
GET    /api/filters
POST   /api/refresh
```

安全平台接口：

```text
GET  /api/security/overview
GET  /api/security/proxies
GET  /api/security/proxies/<ip>:<port>
GET  /api/security/proxies/<ip>:<port>/history
GET  /api/security/proxies/<ip>:<port>/events
POST /api/security/proxies/<ip>:<port>/scan

GET  /api/security/batches
GET  /api/security/batches/<batch_id>
POST /api/security/batches

GET  /api/security/events
GET  /api/security/events/<event_id>

GET  /api/security/geo
GET  /api/security/geo/<country>

GET  /api/security/stats/behavior
GET  /api/security/stats/risk-trend
GET  /api/security/analytics/trend
GET  /api/security/analytics/event-types
GET  /api/security/analytics/risk-distribution

GET  /api/security/honeypot/manifest
```

常用筛选参数：

```text
/api/proxies?country=China&type=HTTP&status=alive&page=1&limit=20
/api/proxies?securityRisk=high&behaviorClass=script_injection
/api/security/events?riskLevel=high&eventType=script_injection
/api/security/geo/CN
```

内部状态统一使用英文枚举，前端负责中文展示。例如：

```text
alive / slow / dead
unknown / low / medium / high / critical
planned / running / completed / skipped / error / timeout
normal / anomalous / not_applicable / skipped / error / timeout
```

---

## 10. 前端页面

启动前端后可访问：

```text
/overview       安全总览，包含风险分布、趋势、漏斗、事件和国家排行
/proxies        代理资产列表
/proxies/:ip/:port
                代理详情、漏斗路径、安全事件、资源观测、证书观测、检测记录
/batches        检测批次和批次详情
/events         安全事件列表
/events/:id     安全事件详情和证据文件
/honeypot       蜜罐目标与基准资源
/map            国家级世界地图，支持 hover 摘要、点击详情和跳转列表
```

---

## 11. 安全检测语义

检测采用漏斗式逐层推进：

```text
基础连通性
  -> 协议识别
  -> 轻量蜜罐检测
  -> 内容 hash 对比
  -> DOM / HTML 风险规则
  -> 资源完整性检测
  -> HTTPS / SOCKS MITM
  -> 多轮条件触发检测
  -> 无头浏览器深度检测
  -> 行为分类与安全评分
```

关键规则：

- 纯 HTTP 代理不会被标记为“MITM 正常”，而是记录为 `not_applicable` 或 `skipped`。
- 资源请求失败不会直接判定为资源替换。
- 网络失败、超时、内容异常、证书异常会尽量区分。
- 高成本检测只应对高可用、可疑、高价值或抽样代理执行。
- 未检测永远不能被当成安全。

---

## 12. 测试和构建

后端单元测试：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests
```

前端类型检查：

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run lint
```

前端生产构建：

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run build
```

---

## 13. 常见问题

### 13.1 `pymysql.err.InterfaceError: (0, '')`

常见原因是数据库连接断开、MySQL 未启动、连接配置错误，或多个并发线程共享同一个未加保护的连接/游标。当前安全 repository 已加入锁来避免同一连接被多个 worker 同时操作，但仍建议：

- 确认 MySQL 正在运行。
- 确认端口、用户名、密码和数据库名正确。
- 确认 migrations 已执行。
- 降低检测并发，例如 API 里设置 `maxWorkers: 1` 或较小值。

### 13.2 前端没有数据

先确认后端可访问：

```powershell
curl http://localhost:5000/api/stats
curl http://localhost:5000/api/security/overview
```

再确认前端 API 地址 `daili/src/api/client.ts` 是否指向正确后端。

### 13.3 安全总览报表为空

可能原因：

- 还没有执行安全检测。
- migration 未执行，安全表不存在。
- 数据库里只有基础代理数据，没有检测批次和安全记录。

先运行：

```powershell
python main.py
```

或通过 API 触发某个代理的安全扫描。

### 13.4 世界地图国家不高亮

地图第一版使用国家级聚合，需要后端返回可识别的国家名称或国家代码。当前内置了常见国家/地区映射，未知国家会在表格和统计中保留，但不一定能映射到地图形状。

### 13.5 中文乱码

源码和数据库都应使用 UTF-8 / utf8mb4。建议：

- 编辑器使用 UTF-8。
- MySQL 数据库和连接使用 `utf8mb4`。
- PowerShell 如显示乱码，可尝试：

```powershell
chcp 65001
```

---

## 14. 开发约束

- 业务状态值使用稳定英文枚举。
- 前端只负责把英文枚举映射为中文文案。
- schema 变更先写 migration。
- `proxies` 只保存最新汇总状态。
- 完整检测过程保存到安全明细表。
- 不要把未检测解释为安全。
- 不要默认对所有代理执行最高成本检测。

