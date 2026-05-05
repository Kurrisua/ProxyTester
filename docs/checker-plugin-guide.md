# 安全 Checker 插件接入指南

本文档面向后续小组协作开发。目标是让每个成员只关注自己的安全检测逻辑，并通过统一契约接入 ProxyTester 的调度、记录、证据和评分流程。

## 1. 放置位置

安全检测插件放在：

```text
security/plugins/
```

每个插件文件中定义一个继承 `BaseSecurityChecker` 的类。`security/registry.py` 会自动加载该目录下的插件类，并按 `order` 排序。

## 2. 必填元数据

每个安全 checker 必须声明以下属性：

```python
class ExampleChecker(BaseSecurityChecker):
    name = "example_checker"
    stage = "example_stage"
    order = 50
    enabled = True
    funnel_stage = 5
    scan_depth = "standard"
    cost_level = "medium"
    required_capabilities = ("usable", "web")
    required_config = ("HONEYPOT_BASE_URL",)
    required_results = ("honeypot_checker",)
    produces_events = ("content_tampering",)
    description = "Short explanation of what this checker verifies."
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `name` | 全局唯一的稳定英文标识，不要使用中文或空格。 |
| `stage` | 当前检测阶段，例如 `dom_diff`、`resource_integrity`、`mitm_detection`。 |
| `order` | 同一批检测中的执行顺序，数字越小越早。 |
| `funnel_stage` | 九层漏斗中的层级编号，用于记录和前端解释。 |
| `scan_depth` | `light`、`standard`、`deep`、`multi_round`、`browser`。 |
| `cost_level` | `low`、`medium`、`high`。高成本检测默认不会全量执行。 |
| `required_capabilities` | 代理必须具备的能力，例如 `usable`、`web`、`http`、`https`、`socks5`、`tls_proxy`。 |
| `required_config` | 运行前必须存在的环境变量或运行时配置。 |
| `required_results` | 必须已经完成的前置 checker，例如 DOM diff 依赖 `honeypot_checker`。 |
| `produces_events` | 可能产生的行为事件类型，用于审计和前端说明。 |
| `description` | 面向协作者的简短说明。 |

## 3. 职责边界

Checker 只负责检测和返回结果，不直接写数据库。

允许：

- 读取 `context.proxy` 和 `context.runtime`
- 调用 `security/access/`、`security/diff/`、`security/rules/` 等底层工具
- 返回 `SecurityResult`
- 在 `evidence` 中附加结构化证据
- 在 `evidence["behaviorEvents"]` 中返回行为事件

不允许：

- 在 checker 中直接写 MySQL
- 静默吞掉未执行状态
- 把未检测当成安全
- 对未授权外部目标做高成本检测
- 在默认全量流程中运行浏览器级或多轮高成本检测

## 4. 状态语义

所有 checker 必须明确区分：

| 结果 | 使用场景 |
| --- | --- |
| `normal` | 已执行，未发现异常。 |
| `anomalous` | 已执行，发现可疑或恶意行为。 |
| `not_applicable` | 当前代理能力不适用，例如 HTTP-only 代理不做 TLS 证书检测。 |
| `skipped` | 适用但被策略跳过，例如深度不足、缺少配置、缺少前置结果。 |
| `error` | 检测执行失败。 |
| `timeout` | 检测超时。 |

调度层会把策略跳过和不适用状态写入 scan record，插件内也应在主动返回时使用同一语义。

## 5. 最小插件模板

```python
from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseSecurityChecker
from core.models.enums import ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import SecurityResult


class ExampleChecker(BaseSecurityChecker):
    name = "example_checker"
    stage = "example_stage"
    order = 50
    funnel_stage = 5
    scan_depth = "standard"
    cost_level = "medium"
    required_capabilities = ("usable", "web")
    required_config = ()
    required_results = ()
    produces_events = ()
    description = "Example checker template."

    def supports(self, context: CheckContext) -> bool:
        return context.proxy.is_usable and (context.proxy.http or context.proxy.https)

    def check(self, context: CheckContext) -> SecurityResult:
        return SecurityResult(
            checker_name=self.name,
            success=True,
            stage=self.stage,
            risk_level=RiskLevel.LOW.value,
            execution_status=ExecutionStatus.COMPLETED.value,
            outcome=ScanOutcome.NORMAL.value,
            funnel_stage=self.funnel_stage,
            scan_depth=self.scan_depth,
            evidence={"summary": "No anomaly found."},
        )
```

## 6. 策略接入

API 或服务调用可以通过 `maxScanDepth` / `max_scan_depth` 控制深度：

```json
{
  "proxies": ["127.0.0.1:8080"],
  "maxWorkers": 20,
  "maxScanDepth": "standard"
}
```

也可以传入 `scanPolicy`：

```json
{
  "maxScanDepth": "deep",
  "scanPolicy": {
    "name": "team-dom-review",
    "maxScanDepth": "deep",
    "allowedCostLevels": ["low", "medium"],
    "enabledCheckers": ["honeypot_checker", "dom_diff_checker"]
  }
}
```

默认策略允许 `low` 和 `medium` 成本，最高深度为 `standard`。`multi_round` 和 `browser` 类型检测需要显式策略允许。

## 7. 测试要求

新增 checker 至少补充以下测试：

- 能被插件加载器发现。
- 缺少配置时返回或被策略记录为 `skipped`。
- 代理能力不满足时记录为 `not_applicable`。
- 正常结果使用 `normal`，异常结果使用 `anomalous`。
- 异常和超时不会中断整批检测。
- 产生事件时，`evidence["behaviorEvents"]` 结构完整。
