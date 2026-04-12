# ProxyTester

`ProxyTester` 是一个代理采集、检测、评分、入库和查询一体化项目。

当前项目由两部分组成：

- 主项目：Python + Flask + MySQL + React
- 并入的采集项目：`new/proxyxy/Deadpool-proxypool1.5/Deadpool-proxypool1.5`

整合后的目标是把“代理抓取”和“代理检测管理”打通成一条统一自动化流程。

## 功能概览

- 从本地文件加载代理
- 集成 Deadpool 采集项目，自动刷新代理种子
- 合并多个代理源并按 `ip:port` 去重
- 执行多阶段检测
- 生成标准化 JSON 数据集
- 将检测结果保存到 MySQL
- 通过 Flask API 提供查询、筛选、删除和刷新能力
- 提供 React 前端界面查看代理状态

## 当前自动化流程

统一流程如下：

1. 可选执行 Deadpool 的 `fir.py`，刷新抓取到的代理种子文件
2. 读取以下代理源并合并：
   - `collectors/data/lastData.txt`
   - `new/proxyxy/Deadpool-proxypool1.5/Deadpool-proxypool1.5/lastData.txt`
   - `new/proxyxy/Deadpool-proxypool1.5/Deadpool-proxypool1.5/http.txt`
   - `new/proxyxy/Deadpool-proxypool1.5/Deadpool-proxypool1.5/git.txt`
3. 合并、去重后写回统一数据集：
   - `collectors/data/lastData.txt`
4. 生成标准化 JSON：
   - `collectors/data/lastData.json`
5. 执行检测流水线：
   - 连通性检测
   - 协议检测
   - 匿名性检测
   - 地理位置检测
   - 业务可用性检测
   - 安全插件检测
   - 质量与安全评分
6. 可选写入 MySQL

## 项目结构

```text
ProxyTester/
├─ api/                    # Flask API
├─ checkers/               # 代理检测器
├─ collectors/             # 代理源、数据转换、Deadpool 接入
├─ core/                   # 核心模型与接口
├─ scheduler/              # 检测流水线调度
├─ scoring/                # 评分逻辑
├─ security/               # 安全检查插件
├─ services/               # 业务服务与自动化编排
├─ storage/                # MySQL 持久化
├─ daili/                  # React 前端
└─ new/                    # 并入的代理抓取项目
```

## 关键入口

### 1. 命令行统一入口

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

- `--skip-crawl`：跳过 Deadpool 种子刷新
- `--skip-deadpool-sources`：忽略 Deadpool 生成的代理文件
- `--skip-db`：执行检测但不写入 MySQL
- `--max-workers`：设置并发检测线程数

### 2. API 入口

启动后端：

```bash
python api.py
```

主要接口：

- `GET /api/proxies`
- `GET /api/filters`
- `GET /api/stats`
- `GET /api/proxies/high-quality`
- `DELETE /api/proxies/{ip}:{port}`
- `POST /api/refresh`

其中 `POST /api/refresh` 现在会触发统一自动化流程。

请求体示例：

```json
{
  "refreshCrawler": true,
  "includeDeadpoolSources": true,
  "maxWorkers": 150,
  "saveToDb": true
}
```

### 3. 前端入口

```bash
cd daili
npm install
npm run dev
```

## 环境要求

- Python 3.9+
- Node.js 18+
- MySQL 5.7+

后端依赖安装：

```bash
pip install flask flask-cors pymysql requests
```

## 数据库初始化

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

PowerShell 环境变量示例：

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="3307"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_NAME="proxy_pool"
```

## 这次整合新增的核心模块

- `collectors/deadpool_runner.py`
  - 负责调用并入的 Deadpool 抓取脚本
- `services/proxy_workflow_service.py`
  - 负责统一编排“抓取 -> 合并 -> JSON -> 检测 -> 入库”
- `collectors/source_provider.py`
  - 增加 Deadpool 生成文件作为正式采集源
- `main.py`
  - 改为统一自动化入口
- `api/routes/proxy_routes.py`
  - `/api/refresh` 改为执行完整自动化流程

## 说明

- 当前自动化接入的是 Deadpool 的批处理抓取逻辑，即 `fir.py`
- `main_modify.go` 仍然更适合做长期驻留的 SOCKS 监听服务，不直接纳入批量检测主流程
- 如果后续需要，可以继续把 Go 侧拆成“批处理模式”和“监听模式”

## 后续建议

- 为 `new/` 下的采集项目补充独立配置说明
- 将敏感 key 从 `config.toml` 移到环境变量
- 为自动化流程增加日志落盘和失败告警
- 为 `ProxyWorkflowService` 增加单元测试
