# ProxyTester 使用说明

ProxyTester 是一个代理采集、检测、评分、入库、查询和可视化平台。当前项目已经从单纯的“代理可用性检测工具”升级为“代理安全研究平台”的基础版本：系统不仅判断代理是否可用，还会记录检测批次、逐阶段检测记录、安全事件、证据、资源观测、证书观测和地理聚合结果，帮助把代理从“可用/不可用”的资源对象升级为“正常/可疑/恶意”的行为研究对象。

本文档重点说明怎么安装、配置、运行、验证和排错。

---

## 1. 当前能力

当前仓库包含以下能力：

- 免费代理源采集与合并去重。
- Deadpool 代理源刷新和本地文件源读取。
- 基础连通性检测。
- HTTP、HTTPS、SOCKS5 协议识别。
- 匿名性、出口地理位置、业务可用性检测。
- 基础评分和安全评分。
- MySQL 持久化。
- 检测批次、检测记录、安全行为事件、证据、资源和证书观测表。
- Flask API 查询代理、统计、安全总览、批次、事件和国家/地区聚合。
- 本地蜜罐页面和资源。
- React + Vite + TypeScript + Tailwind 前端。
- 前端页面：安全总览、代理列表、代理详情、检测批次、安全事件、世界地图。
- Python 单元测试和前端 TypeScript 检查。

当前仍然是安全研究平台的基础版，不是完整的浏览器沙箱或企业级威胁情报系统。高成本检测、复杂多轮浏览器模拟、深度 MITM 研究和更精细的地图交互仍可继续扩展。

---

## 2. 目录结构

常用目录如下：

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
  security/                      蜜罐、DOM、资源、MITM、流量等安全检测
  services/                      工作流服务、查询服务、检测服务
  storage/mysql/                 MySQL 连接和 repository
  tests/                         Python 单元测试
```

---

## 3. 运行要求

建议环境：

- Windows 10/11 或兼容的 PowerShell 环境。
- Python 3.10+。
- Node.js 18+。
- npm 9+。
- MySQL 8.0+。

本项目当前默认数据库连接为：

```text
host: localhost
port: 3307
user: root
database: proxy_pool
charset: utf8mb4
```

这些默认值来自 `storage/mysql/connection.py`，可通过环境变量覆盖。

---

## 4. 快速启动

下面以 PowerShell 为例。

### 4.1 进入项目目录

```powershell
cd C:\MyProjects\ProxyTester
```

### 4.2 创建并启用 Python 虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

如果 PowerShell 禁止执行脚本，可以临时允许当前进程执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4.3 安装 Python 依赖

项目当前没有统一的 `requirements.txt`，按当前代码使用情况至少需要：

```powershell
python -m pip install flask flask-cors pymysql requests "requests[socks]"
```

说明：

- `flask`：启动 API 服务。
- `flask-cors`：允许前端跨域访问后端。
- `pymysql`：连接 MySQL。
- `requests`：执行 HTTP/HTTPS 检测。
- `requests[socks]`：支持 SOCKS 代理检测。

### 4.4 安装前端依赖

```powershell
cd C:\MyProjects\ProxyTester\daili
npm install
cd C:\MyProjects\ProxyTester
```

---

## 5. 配置数据库

### 5.1 环境变量

后端读取以下环境变量：

```powershell
$env:DB_HOST = "localhost"
$env:DB_PORT = "3307"
$env:DB_USER = "root"
$env:DB_PASSWORD = "your_password"
$env:DB_NAME = "proxy_pool"
```

如果你的 MySQL 没有密码，可以把 `DB_PASSWORD` 设为空字符串：

```powershell
$env:DB_PASSWORD = ""
```

### 5.2 创建数据库

如果数据库还不存在，先创建：

```powershell
$env:MYSQL_PWD = "your_password"
mysql -h localhost -P 3307 -u root -e "CREATE DATABASE IF NOT EXISTS proxy_pool CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
Remove-Item Env:\MYSQL_PWD
```

如果 root 没有密码，可以省略 `MYSQL_PWD`：

```powershell
mysql -h localhost -P 3307 -u root -e "CREATE DATABASE IF NOT EXISTS proxy_pool CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 5.3 执行 migration

数据库结构通过 `migrations/` 目录中的 SQL 文件管理。请按文件名顺序执行：

```text
migrations/
  001_extend_proxies_security_fields.sql
  002_create_security_scan_batches.sql
  003_create_security_scan_records.sql
  004_create_security_behavior_events.sql
  005_create_security_evidence_files.sql
  006_create_security_certificate_observations.sql
  007_create_security_resource_observations.sql
  008_create_proxy_sources.sql
  009_create_proxy_check_records.sql
  010_create_honeypot_targets.sql
  011_create_honeypot_request_logs.sql
```

执行示例：

```powershell
cd C:\MyProjects\ProxyTester
$env:MYSQL_PWD = "your_password"
Get-ChildItem .\migrations\*.sql | Sort-Object Name | ForEach-Object {
  Get-Content $_.FullName | mysql -h localhost -P 3307 -u root proxy_pool
}
Remove-Item Env:\MYSQL_PWD
```

如果你的 MySQL root 没有密码：

```powershell
cd C:\MyProjects\ProxyTester
Get-ChildItem .\migrations\*.sql | Sort-Object Name | ForEach-Object {
  Get-Content $_.FullName | mysql -h localhost -P 3307 -u root proxy_pool
}
```

重要提醒：

- 如果已有历史数据，执行前建议先备份 `proxies` 表。
- `proxies` 主表只保存最新汇总状态。
- 完整检测过程保存在 scan batch、scan record、behavior event、evidence、certificate observation、resource observation 等明细表中。
- 不要再依赖业务代码启动时隐式改表。

### 5.4 备份 proxies 表

已有数据时建议先做 SQL 备份：

```powershell
$env:MYSQL_PWD = "your_password"
mysqldump -h localhost -P 3307 -u root proxy_pool proxies > backups\proxies_backup.sql
Remove-Item Env:\MYSQL_PWD
```

也可以根据实际部署策略导出全库：

```powershell
$env:MYSQL_PWD = "your_password"
mysqldump -h localhost -P 3307 -u root proxy_pool > backups\proxy_pool_backup.sql
Remove-Item Env:\MYSQL_PWD
```

---

## 6. 启动后端 API

后端入口是 `api.py`：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python api.py
```

默认监听：

```text
http://localhost:5000
```

Flask 会注册三组路由：

- 代理查询 API：`/api/...`
- 安全研究 API：`/api/security/...`
- 蜜罐资源：`/honeypot/...`

### 6.1 检查 API 是否启动

浏览器或 PowerShell 访问：

```powershell
Invoke-RestMethod http://localhost:5000/api/stats
```

如果数据库尚未初始化或连接失败，先检查：

- MySQL 服务是否启动。
- `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` 是否正确。
- `migrations/` 是否已经按顺序执行。

---

## 7. 启动前端

前端目录是 `daili/`：

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run dev
```

默认访问：

```text
http://localhost:3000
```

当前前端 API client 直接访问：

```text
http://localhost:5000/api
```

因此本地使用时需要同时启动：

1. Flask API：`python api.py`
2. Vite 前端：`npm run dev`

---

## 8. 运行代理采集和检测流水线

命令行入口是 `main.py`：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python main.py
```

完整流程会执行：

1. 可选刷新 Deadpool 外部代理源。
2. 读取多个代理源文件。
3. 合并去重。
4. 生成规范化代理数据。
5. 执行基础检测。
6. 执行安全检测插件。
7. 计算基础评分和安全评分。
8. 保存 `proxies` 最新汇总状态。
9. 保存检测批次、检测记录、安全事件、证据和观测数据。

### 8.1 常用参数

跳过外部抓取，只检测本地已有数据：

```powershell
python main.py --skip-crawl
```

跳过 Deadpool 源：

```powershell
python main.py --skip-deadpool-sources
```

不写入数据库，只做本地验证：

```powershell
python main.py --skip-db
```

限制并发，适合第一次小规模验证：

```powershell
python main.py --skip-crawl --max-workers 20
```

最小验证命令：

```powershell
python main.py --skip-crawl --skip-db --max-workers 20
```

---

## 9. 启用蜜罐和安全检测

安全检测采用漏斗式逐层检测，不会默认对所有代理执行最重检测。当前安全插件会根据代理状态、协议能力和环境变量决定是否执行。

### 9.1 本地蜜罐页面

启动 `python api.py` 后，可访问：

```text
http://localhost:5000/honeypot/static/basic
```

蜜罐 manifest：

```text
http://localhost:5000/honeypot/manifest
```

蜜罐资源：

```text
http://localhost:5000/honeypot/assets/site.css
http://localhost:5000/honeypot/assets/site.js
http://localhost:5000/honeypot/assets/pixel.txt
```

### 9.2 开启 HTML/DOM 和资源完整性检测

设置 `HONEYPOT_BASE_URL`：

```powershell
$env:HONEYPOT_BASE_URL = "http://127.0.0.1:5000/honeypot/static/basic"
$env:HONEYPOT_TIMEOUT_SECONDS = "10"
```

然后运行检测：

```powershell
python main.py --skip-crawl --max-workers 20
```

如果没有设置 `HONEYPOT_BASE_URL`，相关检测会生成 `skipped` 或 `not_applicable` 语义，而不是把“未检测”当成安全。

### 9.3 开启 HTTPS / SOCKS MITM 证书观测

设置 HTTPS 目标：

```powershell
$env:MITM_TARGET_URL = "https://example.com/"
$env:MITM_TIMEOUT_SECONDS = "10"
```

也可以使用：

```powershell
$env:HONEYPOT_HTTPS_URL = "https://example.com/"
```

注意：

- 纯 HTTP 代理不应被解释为“MITM 正常”，应记录为 `not_applicable`。
- 证书检测失败、网络失败、超时和证书异常会区分记录。
- 高成本检测应优先用于高可用、可疑、高价值或抽样代理。

---

## 10. 前端页面怎么用

启动后端和前端后，打开：

```text
http://localhost:3000
```

主要页面：

```text
/overview              安全总览
/proxies               代理列表
/proxies/:ip/:port     代理详情
/batches               检测批次
/events                安全事件
/map                   世界地图
```

### 10.1 安全总览

安全总览用于查看整体风险态势：

- 代理数量。
- 活跃代理数量。
- 未检测数量。
- 正常、可疑、恶意或高风险代理分布。
- 检测批次趋势。
- 行为事件分布。

### 10.2 代理列表

代理列表用于筛选和查看代理最新状态。内部状态使用稳定英文枚举，前端负责展示中文。

常见状态：

```text
alive   存活
slow    较慢
dead    失效
```

常见匿名级别：

```text
high_anonymous  高匿
anonymous       匿名
transparent     透明
unknown         未知
```

### 10.3 代理详情

代理详情页用于查看单个代理：

- 基础状态。
- 协议能力。
- 响应时间。
- 评分。
- 安全风险。
- 漏斗式检测路径。
- 关联检测记录。
- 关联安全事件。

### 10.4 检测批次

检测批次页用于查看每次 pipeline 运行：

- 批次 ID。
- 开始时间和结束时间。
- 代理总量。
- 完成、跳过、错误、超时数量。
- 检测记录摘要。

### 10.5 安全事件

安全事件页用于查看异常行为：

- 内容篡改。
- 广告注入。
- 脚本注入。
- 跳转操纵。
- 资源替换。
- MITM 可疑。
- 隐蔽恶意行为。
- 非恶意但不稳定行为。

### 10.6 世界地图

世界地图页按国家/地区聚合代理安全态势。第一版聚合维度包括：

- 代理总数。
- 活跃数量。
- 未检测数量。
- 正常、可疑、恶意数量。
- 平均响应时间。
- 协议分布。
- 最高风险等级。
- 主要异常类型。

点击国家/地区后，可进入筛选后的代理列表或事件列表。

---

## 11. API 使用

后端默认地址：

```text
http://localhost:5000
```

### 11.1 代理列表

```http
GET /api/proxies?page=1&limit=20
```

可选查询参数：

```text
country              国家/地区
type                 协议类型
status               alive | slow | dead
min_business_score   最低业务评分
sort                 response_time 等排序字段
page                 页码
limit                每页数量
```

PowerShell 示例：

```powershell
Invoke-RestMethod "http://localhost:5000/api/proxies?page=1&limit=20"
```

### 11.2 代理详情

```http
GET /api/proxies/<ip>:<port>
```

示例：

```powershell
Invoke-RestMethod "http://localhost:5000/api/proxies/1.2.3.4:8080"
```

### 11.3 删除代理

```http
DELETE /api/proxies/<ip>:<port>
```

示例：

```powershell
Invoke-RestMethod -Method Delete "http://localhost:5000/api/proxies/1.2.3.4:8080"
```

### 11.4 统计信息

```http
GET /api/stats
```

示例：

```powershell
Invoke-RestMethod "http://localhost:5000/api/stats"
```

### 11.5 筛选项

```http
GET /api/filters
```

### 11.6 高质量代理

```http
GET /api/proxies/high-quality?min_score=2&limit=10
```

### 11.7 触发刷新

```http
POST /api/refresh
```

请求体示例：

```json
{
  "refreshCrawler": true,
  "includeDeadpoolSources": true,
  "maxWorkers": 150,
  "saveToDb": true
}
```

PowerShell 示例：

```powershell
$body = @{
  refreshCrawler = $true
  includeDeadpoolSources = $true
  maxWorkers = 50
  saveToDb = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://localhost:5000/api/refresh" `
  -ContentType "application/json" `
  -Body $body
```

### 11.8 安全总览

```http
GET /api/security/overview
```

### 11.9 检测批次

```http
GET /api/security/batches?page=1&limit=20
GET /api/security/scans?page=1&limit=20
```

两者当前都返回批次列表。

### 11.10 批次详情

```http
GET /api/security/batches/<batch_id>?recordLimit=100
GET /api/security/scans/<batch_id>?recordLimit=100
```

### 11.11 安全事件

```http
GET /api/security/events?page=1&limit=20
```

可选查询参数：

```text
eventType    行为事件类型
riskLevel    unknown | low | medium | high | critical
country      国家/地区
```

### 11.12 国家/地区聚合

```http
GET /api/security/geo
```

---

## 12. 稳定状态枚举

项目内部状态使用英文枚举，前端负责中文展示。

### 12.1 Applicability

```text
applicable
not_applicable
unknown
```

### 12.2 ExecutionStatus

```text
planned
running
completed
skipped
error
timeout
```

### 12.3 ScanOutcome

```text
normal
anomalous
not_applicable
skipped
error
timeout
```

### 12.4 RiskLevel

```text
unknown
low
medium
high
critical
```

### 12.5 BehaviorClass

```text
normal
content_tampering
ad_injection
script_injection
redirect_manipulation
resource_replacement
mitm_suspected
stealthy_malicious
unstable_but_non_malicious
```

关键语义：

- `normal` 表示已执行且没有发现异常。
- `not_applicable` 表示检测条件不适用，例如 HTTP 代理不适合被标记为 MITM 正常。
- `skipped` 表示本轮有意跳过，例如未配置目标 URL 或漏斗前置条件不满足。
- `error` 表示执行失败。
- `timeout` 表示明确超时。
- 未检测永远不能被当成安全。

---

## 13. 测试和构建

### 13.1 后端单元测试

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests
```

### 13.2 前端类型检查

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run lint
```

当前 `lint` 实际执行的是：

```text
tsc --noEmit
```

### 13.3 前端生产构建

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run build
```

构建产物会输出到 Vite 默认目录：

```text
daili/dist/
```

### 13.4 前端本地预览

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run preview
```

---

## 14. 常见使用场景

### 14.1 只想打开前端看已有数据库数据

终端 1：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python api.py
```

终端 2：

```powershell
cd C:\MyProjects\ProxyTester\daili
npm run dev
```

浏览器打开：

```text
http://localhost:3000
```

### 14.2 第一次小规模检测

先启动 API，让本地蜜罐可访问：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
python api.py
```

另开一个终端：

```powershell
cd C:\MyProjects\ProxyTester
.\.venv\Scripts\Activate.ps1
$env:HONEYPOT_BASE_URL = "http://127.0.0.1:5000/honeypot/static/basic"
python main.py --skip-crawl --max-workers 20
```

### 14.3 只验证代码不写数据库

```powershell
python main.py --skip-crawl --skip-db --max-workers 20
```

### 14.4 触发一次完整刷新

```powershell
python main.py --max-workers 150
```

这会尝试刷新外部源、合并数据、检测并写入数据库。

### 14.5 通过 API 刷新

```powershell
$body = @{
  refreshCrawler = $true
  includeDeadpoolSources = $true
  maxWorkers = 50
  saveToDb = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://localhost:5000/api/refresh" `
  -ContentType "application/json" `
  -Body $body
```

---

## 15. 排错

### 15.1 前端页面没有数据

检查顺序：

1. `python api.py` 是否正在运行。
2. 浏览器能否访问 `http://localhost:5000/api/stats`。
3. MySQL 是否启动。
4. 数据库是否执行过 migration。
5. `proxies` 表里是否已有数据。
6. 浏览器开发者工具里是否有跨域或网络错误。

### 15.2 API 连接数据库失败

检查：

```powershell
$env:DB_HOST
$env:DB_PORT
$env:DB_USER
$env:DB_PASSWORD
$env:DB_NAME
```

也可以直接测试 MySQL：

```powershell
mysql -h localhost -P 3307 -u root -p proxy_pool
```

### 15.3 SOCKS5 检测报错

确认安装了 SOCKS 支持：

```powershell
python -m pip install "requests[socks]"
```

### 15.4 安全检测一直 skipped

常见原因：

- 没有设置 `HONEYPOT_BASE_URL`。
- 没有设置 `MITM_TARGET_URL` 或 `HONEYPOT_HTTPS_URL`。
- 代理不支持相关协议。
- 漏斗前置条件不满足，例如基础连通性失败。

检查环境变量：

```powershell
$env:HONEYPOT_BASE_URL
$env:MITM_TARGET_URL
$env:HONEYPOT_HTTPS_URL
```

### 15.5 Deadpool 刷新很慢

外部代理源质量和响应速度波动较大。可以先跳过抓取：

```powershell
python main.py --skip-crawl
```

也可以降低并发做排查：

```powershell
python main.py --skip-crawl --max-workers 20
```

### 15.6 端口被占用

Flask 默认使用 5000，Vite 默认使用 3000。

检查端口占用：

```powershell
netstat -ano | findstr :5000
netstat -ano | findstr :3000
```

---

## 16. 开发扩展

### 16.1 新增基础 checker

建议步骤：

1. 在 `checkers/` 下选择合适子目录新增 checker。
2. 返回稳定的 `CheckResult`。
3. 明确 `applicability`、`execution_status`、`outcome`、`skip_reason` 和 `funnel_stage`。
4. 在 `checkers/registry.py` 注册。
5. 为 checker 增加最小测试。

### 16.2 新增安全 checker

建议步骤：

1. 在 `security/plugins/` 下新增插件。
2. 遵守漏斗式检测原则，不要默认执行高成本检测。
3. 不适用时返回 `not_applicable`。
4. 条件不足时返回 `skipped`。
5. 超时、网络错误、内容异常、证书异常要分开表达。
6. 在 `security/registry.py` 注册。
7. 如果会生成行为事件，使用稳定 `BehaviorClass`。

### 16.3 新增 repository

当前 MySQL repository 位于：

```text
storage/mysql/
```

如需支持其他数据库，应保持服务层契约不变，新增 repository 实现，而不是把 SQL 写入 pipeline。

### 16.4 新增前端页面

前端结构位于：

```text
daili/src/
  app/
  api/
  components/
  features/
  lib/
  types/
```

建议：

1. API 调用放入 `api/`。
2. 类型放入 `types/`。
3. 页面和业务组件放入 `features/`。
4. 枚举中文展示放入 label map，不要把中文状态传回后端。
5. `App.tsx` 只保留应用组合入口。

---

## 17. 当前限制

- 迁移文件已经完整提供，但当前没有独立 migration runner，需要手动按顺序执行 SQL。
- 前端 API base URL 当前固定为 `http://localhost:5000/api`。
- 高成本检测应谨慎启用，避免对所有代理无差别执行。
- 代理源质量受外部公开源波动影响，检测结果数量会随时间变化。
- 世界地图第一版以国家/地区聚合为主，不做城市级定位。
- 未配置蜜罐或 HTTPS 目标时，相关安全检测会跳过，这是正确语义，不代表代理安全。

---

## 18. 推荐日常工作流

开发和验证时建议按这个顺序：

1. 启动 MySQL。
2. 设置 `DB_*` 环境变量。
3. 确认 migration 已执行。
4. 启动 Flask API：`python api.py`。
5. 设置 `HONEYPOT_BASE_URL`。
6. 小规模运行：`python main.py --skip-crawl --max-workers 20`。
7. 启动前端：`npm run dev`。
8. 查看 `/overview`、`/proxies`、`/batches`、`/events`、`/map`。
9. 运行后端测试：`python -m unittest discover -s tests`。
10. 运行前端检查：`npm run lint`。
11. 需要生产构建时运行：`npm run build`。

---

## 19. 一句话定位

ProxyTester 的下一阶段目标，是把代理从“可用/不可用”的资源对象，升级为“正常/可疑/恶意”的行为研究对象。
