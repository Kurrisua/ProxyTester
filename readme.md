# ProxyTester 代理检测系统

## 项目简介

ProxyTester 是一个功能完整的自动化代理检测系统，采用前后端分离架构：
- **后端**: Python (Flask) + MySQL
- **前端**: React + TypeScript + Vite
- **检测模块**: 多线程并发检测，支持安全检测

## 功能特性

| 类别 | 功能 |
|------|------|
| **协议检测** | HTTP、HTTPS、SOCKS5 协议支持检测 |
| **匿名度检测** | 高匿、匿名、透明 |
| **地理位置** | 国家、城市、ISP（支持多 GEO API 源） |
| **业务可用性** | 测试代理能否访问 Google/Baidu/GitHub |
| **安全检测** | 蜜罐检测、MITM 检测、流量分析、DOM 差异检测 |
| **质量评分** | 综合评分系统（0-100分） |

---

## 项目结构

```
ProxyTester/
├── api/                      # Flask API 模块
│   ├── app_factory.py        # 应用工厂
│   └── routes/
│       └── proxy_routes.py   # 代理相关 API 路由
├── checkers/                 # 检测器模块
│   ├── anonymity/            # 匿名度检测
│   ├── business/             # 业务可用性检测
│   ├── connectivity/         # TCP 连通性检测
│   ├── geo/                 # 地理位置检测
│   └── protocol/            # 协议检测 (HTTP/HTTPS/SOCKS5)
├── core/                     # 核心模块
│   ├── context/              # 检测上下文
│   ├── interfaces/           # 接口定义
│   └── models/               # 数据模型
├── collectors/               # 代理采集器
├── scoring/                  # 评分模块
├── security/                 # 安全检测插件
├── services/                 # 业务服务层
├── storage/                  # 存储层 (MySQL)
│   └── mysql/
│       ├── connection.py     # 数据库连接
│       └── proxy_repository.py # 代理数据仓库
├── utils/                    # 工具模块
├── daili/                    # 前端项目 (React)
│   └── src/
│       ├── App.tsx           # 主应用组件
│       ├── types.ts          # 类型定义
│       └── lib/
│           └── api.ts        # API 调用
├── main.py                   # 主程序入口
└── api.py                    # API 服务入口
```

---

## 快速开始

### 1. 环境要求

- Python 3.9+
- Node.js 18+
- MySQL 5.7+

### 2. 安装依赖

**后端依赖：**
```bash
pip install flask flask-cors pymysql requests
```

**前端依赖：**
```bash
cd daili
npm install
```

### 3. 配置数据库

确保 MySQL 服务运行，并创建数据库：
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

**数据库环境变量（可选）：**
```bash
export DB_HOST=localhost
export DB_PORT=3307
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=proxy_pool
```

### 4. 准备代理数据

在 `lastData.txt` 文件中添加代理列表，格式：
```
IP:PORT [source]
```

示例：
```
192.168.1.1:8080 from_file
10.0.0.1:3128 api_source
```

### 5. 启动服务

**方式一：分别启动**
```bash
# 启动后端 API
python api.py

# 启动前端 (新终端)
cd daili
npm run dev
```

**方式二：使用启动脚本**
```powershell
# PowerShell
.\start_all.ps1
```

```cmd
# Windows
start_servers.bat
```

---

## 使用方法

### 后端使用

#### 方式一：命令行运行检测

```python
from check.main_check import (
    load_proxys,
    full_proxy_check,
    print_full_proxy_info
)

# 1. 加载代理列表
proxies = load_proxys("lastData.txt")
print(f"Loaded {len(proxies)} proxies")

# 2. 执行完整检测流程
# 参数说明：
#   max_workers: 并发线程数（默认 150）
#   save_to_db: 是否保存到数据库（默认 True）
alive_proxies = full_proxy_check(proxies, max_workers=150, save_to_db=True)

# 3. 打印检测结果
for proxy in alive_proxies:
    print_full_proxy_info(proxy)
```

#### 方式二：使用 ProxyCheckService

```python
from services.proxy_check_service import ProxyCheckService

service = ProxyCheckService()

# 从文件加载代理
proxies = service.load_from_file("lastData.txt")

# 执行检测
alive = service.run_full_check(proxies, max_workers=150, save_to_db=True)

print(f"Alive proxies: {len(alive)}")
```

### 前端使用

启动前端服务后，访问 `http://localhost:5173`

功能说明：
- **统计卡片**：显示活跃代理数、平均响应时间、国家分布
- **代理列表**：展示所有代理详情（IP、端口、国家、协议、匿名度、响应时间等）
- **搜索过滤**：按国家、协议类型、状态筛选
- **状态显示**：
  - 🟢 绿色 - 存活（响应时间 < 500ms）
  - 🟡 黄色 - 缓慢（响应时间 >= 500ms）
  - 🔴 红色 - 失效
- **刷新按钮**：触发后端重新检测

---

## API 接口文档

### 获取代理列表

```
GET /api/proxies
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `country` | string | 按国家筛选 |
| `type` | string | 按协议类型筛选 |
| `status` | string | 状态：存活/失效/缓慢 |
| `min_business_score` | int | 最低业务评分 |
| `page` | int | 页码（默认 1） |
| `limit` | int | 每页数量（默认 10） |
| `sort` | string | 排序：response_time/success_rate/business_score/quality_score |

**响应示例：**
```json
{
  "data": [
    {
      "id": "192.168.1.1:8080",
      "ip": "192.168.1.1",
      "port": 8080,
      "source": "from_file",
      "country": "美国",
      "city": "洛杉矶",
      "flag": "🇺🇸",
      "types": ["HTTP", "HTTPS"],
      "anonymity": "高匿",
      "speed": 120,
      "successRate": 95.5,
      "businessScore": 3,
      "qualityScore": 88,
      "status": "存活"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 10
}
```

### 获取筛选选项

```
GET /api/filters
```

返回可选的国家、协议类型等筛选条件。

### 获取统计信息

```
GET /api/stats
```

返回代理池的统计数据。

### 获取高质量代理

```
GET /api/proxies/high-quality
```

**参数：**
- `min_score`: 最低业务评分（默认 2）
- `limit`: 返回数量（默认 10）

### 删除代理

```
DELETE /api/proxies/{ip}:{port}
```

### 刷新代理检测

```
POST /api/refresh
```

触发后端重新检测所有代理。

**请求体（可选）：**
```json
{
  "filePath": "lastData.txt"
}
```

---

## 检测模块说明

### 检测器 (checkers/)

| 模块 | 文件 | 功能 |
|------|------|------|
| 连通性 | `tcp_checker.py` | TCP 端口连通性测试 |
| 协议 | `http_checker.py` | HTTP 代理检测 |
| 协议 | `https_checker.py` | HTTPS 代理检测 |
| 协议 | `socks5_checker.py` | SOCKS5 代理检测 |
| 协议 | `protocol_aggregator.py` | 协议聚合，更新代理类型 |
| 匿名度 | `anonymity_checker.py` | 检测匿名度（高匿/匿名/透明） |
| 地理位置 | `exit_geo_checker.py` | 通过代理出口查询地理位置 |
| 地理位置 | `ip_geo_fallback_checker.py` | 直接 IP 查询地理位置 |
| 业务 | `business_availability_checker.py` | 测试 Google/Baidu/GitHub 可访问性 |

### 安全检测 (security/)

| 插件 | 功能 |
|------|------|
| `honeypot_checker.py` | 蜜罐检测 |
| `mitm_checker.py` | 中间人攻击检测 |
| `dom_diff_checker.py` | DOM 差异检测 |
| `traffic_analysis_checker.py` | 流量分析检测 |

### 评分系统 (scoring/)

| 模块 | 功能 |
|------|------|
| `quality_scorer.py` | 质量评分（成功率、响应时间、业务评分） |
| `security_scorer.py` | 安全风险评分 |
| `composite_scorer.py` | 综合评分 |

---

## 数据模型

### ProxyModel 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `ip` | string | IP 地址 |
| `port` | int | 端口号 |
| `source` | string | 代理来源 |
| `is_alive` | bool | 是否存活 |
| `http` | bool | 是否支持 HTTP |
| `https` | bool | 是否支持 HTTPS |
| `socks5` | bool | 是否支持 SOCKS5 |
| `proxy_type` | string | 代理类型（HTTP/HTTPS/SOCKS5/ALL） |
| `anonymity` | string | 匿名度（high_anonymous/anonymous/transparent） |
| `country` | string | 国家 |
| `city` | string | 城市 |
| `isp` | string | 运营商 |
| `response_time` | float | 响应时间（毫秒） |
| `business_score` | int | 业务评分（0-3） |
| `quality_score` | int | 质量评分（0-100） |
| `security_risk` | string | 安全风险（low/medium/high/unknown） |
| `success_count` | int | 成功次数 |
| `fail_count` | int | 失败次数 |
| `last_check_time` | datetime | 最后检查时间 |

---

## 扩展开发

### 添加新的检测器

1. 继承 `BaseChecker` 类
2. 实现 `name`、`stage`、`order` 属性
3. 实现 `supports()` 和 `check()` 方法

```python
from core.interfaces.checker_base import BaseChecker
from core.models.results import CheckResult

class MyChecker(BaseChecker):
    name = "my_checker"
    stage = "custom"
    order = 100

    def supports(self, context):
        return True

    def check(self, context):
        # 检测逻辑
        return CheckResult(self.name, self.stage, True, metadata={})
```

2. 注册到检测器列表（修改 `checkers/registry.py`）

### 添加新的安全检测插件

1. 继承 `BaseSecurityChecker` 类
2. 实现 `check()` 方法
3. 放置到 `security/plugins/` 目录

---

## 常见问题

### Q: 如何提高检测速度？
A: 调整 `max_workers` 参数，但过高可能导致连接超时或被封 IP。

### Q: 代理检测失败怎么办？
A: 系统会自动重试，支持多目标检测（httpbin、ip-api 等）提高成功率。

### Q: 如何查看检测日志？
A: 控制台会输出详细检测过程，包括每个代理的检测状态、响应时间等。

---

## 技术栈

- **后端**: Python 3.9+, Flask, pymysql, requests
- **前端**: React 18, TypeScript, Vite, framer-motion, lucide-react
- **数据库**: MySQL 5.7+
- **并发**: ThreadPoolExecutor

---

## 许可证

MIT License
