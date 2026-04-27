# ProxyTester 数据库设计建议

> 本文档用于规划 ProxyTester 从“单表代理池”升级为“代理安全检测、行为分析、多轮观测、证据追踪”的 MySQL 数据库结构。  
> 当前阶段只做设计建议，不修改业务代码。  
> 最后更新：2026-04-17

## 1. 设计结论

后续不建议继续只使用一张 `proxies` 表。

当前 `proxies` 表适合保存代理的最新汇总状态，例如 IP、端口、协议、国家、响应时间、可用性、基础评分等。但是后续要实现蜜罐检测、DOM 差分、资源替换检测、MITM 检测、多轮行为观测和前端可视化分析，这些数据天然具有不同粒度：

1. 一个代理会有多次检测批次。
2. 一个检测批次会包含多个代理。
3. 一个代理在一个批次中会有多轮访问。
4. 一轮访问会产生直连结果、代理结果、证书结果、资源结果和差分结果。
5. 一轮检测可能识别出多个异常行为事件。
6. 原始证据可能体积较大，不适合全部塞进主表。

因此推荐采用：

> 代理主表保存最新状态，检测批次表保存任务，检测记录表保存每轮摘要，行为事件表保存异常，证据表保存可追溯证据引用。

这会比单表复杂一些，但后续查询、分析、统计和前端展示会清晰很多。

### 1.1 已确认的用户决策

截至 2026-04-17，用户已确认以下数据库方向：

1. 允许使用 MySQL 外键约束。
2. 希望一次性创建完整规划表结构，而不是先建 MVP 表、后续再频繁改表。
3. 主要目标是降低后续迁移导致数据丢失或结构反复调整的风险。
4. 当前项目已有 MySQL 连接配置，可以基于项目配置尝试连接数据库。

当前已通过项目虚拟环境进行只读连接测试：

```text
MySQL version: 8.0.45
Database: proxy_pool
Connection source: storage/mysql/connection.py
```

这意味着：

1. MySQL 8.0 支持本文档建议的 `JSON` 字段。
2. 可以使用 `utf8mb4`。
3. 可以使用外键。
4. 可以一次性创建完整表结构。

注意：

1. 建表属于写操作，真正执行前仍应由用户明确授权。
2. 建表前应先备份当前数据库，尤其是已有 `proxies` 表中的数据。
3. 如果要重建 `proxies` 表，必须先导出现有数据，避免覆盖或丢失。

## 2. 当前数据库状态判断

根据当前代码，系统主要依赖一张 `proxies` 表。代码中已经使用或假设的字段包括：

1. `id`
2. `ip`
3. `port`
4. `source`
5. `country`
6. `city`
7. `proxy_type`
8. `anonymity`
9. `response_time`
10. `business_score`
11. `success_count`
12. `fail_count`
13. `last_check_time`
14. `is_alive`
15. `quality_score`
16. `security_risk`

其中 `business_score`、`quality_score`、`security_risk` 当前由 `storage/mysql/proxy_repository.py` 在运行时尝试补列。

批判性建议：

1. 运行时自动 `ALTER TABLE` 只适合早期开发，不适合后续复杂表结构。
2. 后续应逐步改成明确的 SQL 初始化脚本或迁移机制。
3. 不建议把 `security_evidence` 这类复杂 JSON 全部放进 `proxies` 主表。
4. `proxies` 应该只保存“最新汇总状态”，不要保存每次检测明细。

## 3. 总体表结构

建议后续数据库分为六类表：

1. 代理资产表：保存代理基础信息和最新汇总状态。
2. 代理来源表：保存代理从哪里来、来源是否有效。
3. 基础检测表：保存连通性、协议、匿名性、地理位置、性能等历史记录。
4. 安全检测表：保存蜜罐、差分、资源、证书、MITM、多轮检测结果。
5. 行为事件表：保存明确识别出的异常事件。
6. 证据索引表：保存原始证据文件或摘要引用。

原始建议是分阶段建表，但用户已明确表示希望一次性建好所有表，避免后续频繁改表带来的数据风险。因此当前推荐改为：

1. 一次性准备完整 schema。
2. 对已有 `proxies` 表采用安全迁移或备份重建。
3. 一次性创建所有安全研究相关表。
4. 后续尽量通过新增 nullable 字段或新增独立表扩展，避免破坏性改动。

一次性建表清单建议包括：

1. `proxies`
2. `proxy_sources`
3. `proxy_check_records`
4. `security_scan_batches`
5. `security_scan_records`
6. `security_behavior_events`
7. `security_certificate_observations`
8. `security_resource_observations`
9. `security_evidence_files`
10. `honeypot_targets`
11. `honeypot_request_logs`

### 3.1 漏斗式检测对数据库的影响

后续安全检测不是所有代理执行同一套完整流程，而是根据代理协议、稳定性、前置检测结果和风险信号进入不同路径。这会直接影响数据库设计。

数据库必须能表达：

1. 某个检测是否被计划执行。
2. 某个检测是否适用于该代理。
3. 某个检测是否被策略跳过。
4. 某个检测是否执行失败。
5. 某个检测是否发现异常。
6. 某个代理当前处于漏斗的哪一层。
7. 某个代理为什么没有进入更深层检测。

因此安全检测记录不能只有 `is_anomalous`。至少需要同时记录：

1. `funnel_stage`：漏斗层级。
2. `stage`：检测阶段。
3. `checker_name`：检测器名称。
4. `applicability`：适用性。
5. `execution_status`：执行状态。
6. `skip_reason`：跳过原因。
7. `precondition_summary`：前置条件摘要。
8. `scan_depth`：检测深度。

推荐状态语义：

| 字段 | 推荐取值 | 含义 |
| --- | --- | --- |
| `applicability` | `applicable` | 该检测适用于当前代理 |
| `applicability` | `not_applicable` | 因协议或能力不满足而不适用 |
| `applicability` | `unknown` | 当前无法判断是否适用 |
| `execution_status` | `planned` | 已进入检测计划但尚未运行 |
| `execution_status` | `running` | 正在运行 |
| `execution_status` | `completed` | 已完成 |
| `execution_status` | `skipped` | 被策略跳过 |
| `execution_status` | `error` | 检测执行出错 |
| `execution_status` | `timeout` | 检测超时 |

关键区别：

1. `not_applicable` 表示检测不适用，例如纯 HTTP 代理不做 HTTPS 证书检测。
2. `skipped` 表示检测适用但被策略跳过，例如浏览器深度检测只对可疑代理运行。
3. `error` 表示检测应该执行，但执行过程中失败。
4. `completed` 只代表检测完成，不代表结果正常，是否异常仍由 `is_anomalous` 和 `risk_level` 表达。

批判性建议：

1. 不能把“未执行 MITM 检测”统计为“无 MITM 风险”。
2. 前端必须能看到某一层检测未执行的原因。
3. 汇总安全评分时，`not_applicable`、`skipped`、`error` 应采用不同权重，不能混为一类。

## 4. 表一：代理主表 `proxies`

### 4.1 职责

`proxies` 是代理资产主表，只保存每个代理的基础身份和最新汇总状态。

它不负责保存每轮检测明细，也不负责保存完整 DOM diff、证书链、响应正文或资源文件。

### 4.2 建议字段

```sql
CREATE TABLE proxies (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ip VARCHAR(64) NOT NULL,
    port INT NOT NULL,
    source VARCHAR(512) DEFAULT 'unknown',

    is_alive TINYINT(1) NOT NULL DEFAULT 0,
    proxy_type VARCHAR(64) DEFAULT NULL,
    anonymity VARCHAR(64) DEFAULT NULL,
    exit_ip VARCHAR(64) DEFAULT NULL,
    country VARCHAR(128) DEFAULT NULL,
    city VARCHAR(128) DEFAULT NULL,
    isp VARCHAR(255) DEFAULT NULL,

    response_time DOUBLE DEFAULT NULL,
    business_score INT NOT NULL DEFAULT 0,
    quality_score INT NOT NULL DEFAULT 0,
    success_count INT NOT NULL DEFAULT 0,
    fail_count INT NOT NULL DEFAULT 0,
    last_check_time DATETIME DEFAULT NULL,

    security_risk VARCHAR(32) NOT NULL DEFAULT 'unknown',
    security_score INT DEFAULT NULL,
    behavior_class VARCHAR(64) DEFAULT NULL,
    risk_tags JSON DEFAULT NULL,
    has_content_tampering TINYINT(1) NOT NULL DEFAULT 0,
    has_resource_replacement TINYINT(1) NOT NULL DEFAULT 0,
    has_mitm_risk TINYINT(1) NOT NULL DEFAULT 0,
    anomaly_trigger_count INT NOT NULL DEFAULT 0,
    security_check_count INT NOT NULL DEFAULT 0,
    anomaly_trigger_rate DECIMAL(6,4) DEFAULT NULL,
    last_security_check_time DATETIME DEFAULT NULL,

    first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_proxy_ip_port (ip, port),
    KEY idx_alive_type (is_alive, proxy_type),
    KEY idx_country (country),
    KEY idx_quality_score (quality_score),
    KEY idx_security_risk (security_risk),
    KEY idx_behavior_class (behavior_class),
    KEY idx_last_security_check_time (last_security_check_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.3 字段说明

`security_risk` 表示最新安全风险等级，建议取值：

1. `unknown`
2. `low`
3. `medium`
4. `high`
5. `critical`

`behavior_class` 表示最新行为分类，建议取值：

1. `normal`
2. `content_tampering`
3. `ad_injection`
4. `script_injection`
5. `redirect_manipulation`
6. `resource_replacement`
7. `mitm_suspected`
8. `stealthy_malicious`
9. `unstable_but_non_malicious`

`risk_tags` 可以保存最新汇总标签，例如：

```json
["script_injection", "hidden_iframe", "cert_mismatch"]
```

批判性建议：

1. `risk_tags` 用 JSON 可以接受，因为它只是最新汇总标签，不承担复杂事件查询。
2. 如果后续要高频按单个标签检索，应该通过 `security_behavior_events.event_type` 查询，而不是依赖 JSON 查询。
3. `security_risk` 可以继续兼容现有代码，但建议逐步让它表示安全风险，而不是泛泛的 security 字段。

## 5. 表二：代理来源表 `proxy_sources`

### 5.1 职责

当前代理来源主要存在于代码配置和文件路径里。后续如果要分析“哪些来源更容易产生恶意代理”，就需要代理来源表。

### 5.2 建议字段

```sql
CREATE TABLE proxy_sources (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    location VARCHAR(1024) NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,

    last_refresh_time DATETIME DEFAULT NULL,
    last_success_time DATETIME DEFAULT NULL,
    last_error TEXT DEFAULT NULL,
    total_collected INT NOT NULL DEFAULT 0,
    unique_collected INT NOT NULL DEFAULT 0,
    alive_count INT NOT NULL DEFAULT 0,
    suspicious_count INT NOT NULL DEFAULT 0,
    malicious_count INT NOT NULL DEFAULT 0,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_source_name (name),
    KEY idx_enabled (enabled),
    KEY idx_source_type (source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 5.3 是否第一版必须做

不是必须。

如果第一版只做安全检测 MVP，可以暂缓 `proxy_sources`。但如果你希望后续在前端管理代理源、统计来源质量、禁用高风险来源，就应该尽早设计这张表。

## 6. 表三：基础检测历史表 `proxy_check_records`

### 6.1 职责

保存代理基础检测历史，例如连通性、协议、响应时间、匿名性、地理位置、业务可用性。

当前系统只把最新结果写进 `proxies`。如果你想看“这个代理是否越来越慢”“过去 10 次是否稳定”，就需要这张表。

### 6.2 建议字段

```sql
CREATE TABLE proxy_check_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    proxy_id BIGINT UNSIGNED NOT NULL,

    checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    check_type VARCHAR(64) NOT NULL DEFAULT 'full',
    is_alive TINYINT(1) NOT NULL DEFAULT 0,
    proxy_type VARCHAR(64) DEFAULT NULL,
    anonymity VARCHAR(64) DEFAULT NULL,
    response_time DOUBLE DEFAULT NULL,
    business_score INT DEFAULT NULL,
    quality_score INT DEFAULT NULL,
    exit_ip VARCHAR(64) DEFAULT NULL,
    country VARCHAR(128) DEFAULT NULL,
    city VARCHAR(128) DEFAULT NULL,
    isp VARCHAR(255) DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    metadata JSON DEFAULT NULL,

    PRIMARY KEY (id),
    KEY idx_proxy_checked_at (proxy_id, checked_at),
    KEY idx_checked_at (checked_at),
    CONSTRAINT fk_proxy_check_records_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 6.3 是否第一版必须做

不是安全检测 MVP 的绝对前置条件，但建议做。

它能把“基础可用性历史”和“安全行为历史”区分开，避免后续所有历史都混在安全表里。

## 7. 表四：安全检测批次表 `security_scan_batches`

### 7.1 职责

一次安全检测任务应该有一个批次记录。比如你点击“检测 100 个代理是否篡改蜜罐页面”，这就是一个 batch。

### 7.2 建议字段

```sql
CREATE TABLE security_scan_batches (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    batch_id CHAR(36) NOT NULL,
    scan_mode VARCHAR(64) NOT NULL DEFAULT 'honeypot',
    scan_policy VARCHAR(64) NOT NULL DEFAULT 'funnel_standard',
    max_scan_depth VARCHAR(32) NOT NULL DEFAULT 'standard',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',

    target_proxy_count INT NOT NULL DEFAULT 0,
    checked_proxy_count INT NOT NULL DEFAULT 0,
    skipped_proxy_count INT NOT NULL DEFAULT 0,
    error_proxy_count INT NOT NULL DEFAULT 0,
    normal_proxy_count INT NOT NULL DEFAULT 0,
    suspicious_proxy_count INT NOT NULL DEFAULT 0,
    malicious_proxy_count INT NOT NULL DEFAULT 0,
    anomaly_event_count INT NOT NULL DEFAULT 0,
    light_scan_count INT NOT NULL DEFAULT 0,
    standard_scan_count INT NOT NULL DEFAULT 0,
    deep_scan_count INT NOT NULL DEFAULT 0,
    browser_scan_count INT NOT NULL DEFAULT 0,

    started_at DATETIME DEFAULT NULL,
    finished_at DATETIME DEFAULT NULL,
    elapsed_seconds DOUBLE DEFAULT NULL,
    parameters JSON DEFAULT NULL,
    error_message TEXT DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_security_batch_id (batch_id),
    KEY idx_status (status),
    KEY idx_scan_mode (scan_mode),
    KEY idx_scan_policy (scan_policy),
    KEY idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 7.3 状态建议

`status` 建议取值：

1. `pending`
2. `running`
3. `completed`
4. `failed`
5. `cancelled`
6. `partial_completed`

批判性建议：

1. 安全检测通常耗时较长，不建议只靠同步接口等待结果。
2. 即使第一版暂时同步执行，也建议先有 batch 表，为后续异步任务留接口。
3. `scan_policy` 应记录本批次采用哪种漏斗策略，例如 `funnel_light`、`funnel_standard`、`funnel_deep`、`suspicious_followup`。
4. `max_scan_depth` 应限制本批次最高检测深度，避免误把浏览器深度检测跑成全量任务。

## 8. 表五：安全检测记录表 `security_scan_records`

### 8.1 职责

保存某个代理在某个批次中的某一轮安全检测摘要。

这是后续多轮观测、条件触发识别、异常触发率统计的核心表。

### 8.2 建议字段

```sql
CREATE TABLE security_scan_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    batch_id BIGINT UNSIGNED NOT NULL,
    proxy_id BIGINT UNSIGNED NOT NULL,

    round_index INT NOT NULL DEFAULT 1,
    funnel_stage INT NOT NULL DEFAULT 0,
    stage VARCHAR(64) NOT NULL,
    checker_name VARCHAR(128) NOT NULL,
    scan_depth VARCHAR(32) NOT NULL DEFAULT 'light',
    applicability VARCHAR(32) NOT NULL DEFAULT 'applicable',
    execution_status VARCHAR(32) NOT NULL DEFAULT 'completed',
    skip_reason VARCHAR(255) DEFAULT NULL,
    precondition_summary JSON DEFAULT NULL,

    target_url VARCHAR(2048) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    access_client VARCHAR(64) NOT NULL DEFAULT 'http',
    user_agent VARCHAR(512) DEFAULT NULL,
    request_profile VARCHAR(128) DEFAULT NULL,

    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME DEFAULT NULL,
    elapsed_ms DOUBLE DEFAULT NULL,

    direct_success TINYINT(1) NOT NULL DEFAULT 0,
    proxy_success TINYINT(1) NOT NULL DEFAULT 0,
    direct_status_code INT DEFAULT NULL,
    proxy_status_code INT DEFAULT NULL,
    direct_final_url VARCHAR(2048) DEFAULT NULL,
    proxy_final_url VARCHAR(2048) DEFAULT NULL,
    direct_body_hash CHAR(64) DEFAULT NULL,
    proxy_body_hash CHAR(64) DEFAULT NULL,
    direct_body_size INT DEFAULT NULL,
    proxy_body_size INT DEFAULT NULL,
    direct_mime_type VARCHAR(128) DEFAULT NULL,
    proxy_mime_type VARCHAR(128) DEFAULT NULL,

    is_anomalous TINYINT(1) NOT NULL DEFAULT 0,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'low',
    behavior_class VARCHAR(64) DEFAULT NULL,
    risk_tags JSON DEFAULT NULL,
    diff_summary JSON DEFAULT NULL,
    cert_summary JSON DEFAULT NULL,
    resource_summary JSON DEFAULT NULL,
    redirect_summary JSON DEFAULT NULL,
    error_message TEXT DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_batch_proxy_round (batch_id, proxy_id, round_index),
    KEY idx_proxy_started_at (proxy_id, started_at),
    KEY idx_stage_checker (stage, checker_name),
    KEY idx_funnel_stage (funnel_stage),
    KEY idx_scan_depth (scan_depth),
    KEY idx_applicability (applicability),
    KEY idx_execution_status (execution_status),
    KEY idx_is_anomalous (is_anomalous),
    KEY idx_risk_level (risk_level),
    KEY idx_behavior_class (behavior_class),
    KEY idx_target_type (target_type),
    CONSTRAINT fk_security_scan_records_batch
        FOREIGN KEY (batch_id) REFERENCES security_scan_batches(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_security_scan_records_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 8.3 字段说明

`target_type` 建议取值：

1. `html_static`
2. `html_dom`
3. `form`
4. `multi_resource`
5. `image`
6. `script`
7. `css`
8. `download`
9. `https_cert`

`access_client` 建议取值：

1. `http`
2. `browser`

`request_profile` 可以表示当前检测条件，例如：

1. `desktop_chrome`
2. `mobile_safari`
3. `crawler_like`
4. `delayed_second_visit`

`stage` 建议取值：

1. `basic_connectivity`
2. `protocol_identification`
3. `honeypot_light`
4. `content_hash_diff`
5. `dom_diff`
6. `resource_integrity`
7. `tls_mitm`
8. `multi_round_behavior`
9. `browser_behavior`
10. `behavior_modeling`

`scan_depth` 建议取值：

1. `light`
2. `standard`
3. `deep`
4. `browser`

`applicability` 建议取值：

1. `applicable`
2. `not_applicable`
3. `unknown`

`execution_status` 建议取值：

1. `planned`
2. `running`
3. `completed`
4. `skipped`
5. `error`
6. `timeout`

常见 `skip_reason` 示例：

1. `proxy_does_not_support_https_or_socks5`
2. `proxy_failed_basic_connectivity`
3. `response_not_html`
4. `resource_fetch_failed`
5. `not_selected_by_sampling_policy`
6. `not_suspicious_enough_for_deep_scan`
7. `browser_budget_exceeded`
8. `scan_depth_limited_by_batch_policy`

批判性建议：

1. `security_scan_records` 保存摘要即可，不要保存完整 HTML 或二进制。
2. `diff_summary`、`cert_summary`、`resource_summary` 可以用 JSON 保存结构化摘要。
3. 高频查询字段必须单独列出来，例如 `risk_level`、`behavior_class`、`is_anomalous`，不要只藏在 JSON 里。
4. `not_applicable`、`skipped`、`error` 必须和 `completed` 区分，否则安全统计会误导。
5. `funnel_stage` 和 `scan_depth` 是前端展示检测路径的重要字段，不建议只放在 JSON 中。

## 9. 表六：行为事件表 `security_behavior_events`

### 9.1 职责

保存明确识别出的异常行为事件。

一条 `security_scan_record` 可能产生多个事件，例如同一轮访问里同时出现 `script_injection` 和 `hidden_iframe`。

### 9.2 建议字段

```sql
CREATE TABLE security_behavior_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NOT NULL,
    batch_id BIGINT UNSIGNED NOT NULL,
    proxy_id BIGINT UNSIGNED NOT NULL,

    event_type VARCHAR(64) NOT NULL,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'medium',
    confidence DECIMAL(5,4) DEFAULT NULL,
    target_url VARCHAR(2048) DEFAULT NULL,
    target_type VARCHAR(64) DEFAULT NULL,

    dom_selector VARCHAR(1024) DEFAULT NULL,
    affected_attribute VARCHAR(128) DEFAULT NULL,
    before_value TEXT DEFAULT NULL,
    after_value TEXT DEFAULT NULL,
    external_domain VARCHAR(255) DEFAULT NULL,
    evidence_summary TEXT DEFAULT NULL,
    evidence JSON DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_proxy_event_created (proxy_id, event_type, created_at),
    KEY idx_event_type (event_type),
    KEY idx_risk_level (risk_level),
    KEY idx_batch_id (batch_id),
    KEY idx_record_id (record_id),
    KEY idx_external_domain (external_domain),
    CONSTRAINT fk_security_behavior_events_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_security_behavior_events_batch
        FOREIGN KEY (batch_id) REFERENCES security_scan_batches(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_security_behavior_events_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 9.3 事件类型建议

`event_type` 建议取值：

1. `content_tampering`
2. `script_injection`
3. `ad_injection`
4. `hidden_iframe`
5. `form_hijack`
6. `event_handler_injection`
7. `redirect_manipulation`
8. `resource_replacement`
9. `file_replaced`
10. `script_modified`
11. `image_rewritten`
12. `mime_type_mismatch`
13. `cert_mismatch`
14. `self_signed_cert`
15. `unknown_issuer`
16. `cert_chain_invalid`
17. `mitm_suspected`
18. `browser_only_anomaly`

### 9.4 为什么事件表很重要

如果只在 `security_scan_records.risk_tags` 里保存标签，前端可以展示摘要，但很难回答这些问题：

1. 哪种攻击类型最多。
2. 哪些代理注入了同一个外部域名。
3. 哪些国家的代理更容易发生 MITM。
4. 某个代理什么时候第一次出现表单劫持。
5. 某一批次里一共出现多少次脚本注入。

行为事件表就是为这些研究问题准备的。

## 10. 表七：证书观测表 `security_certificate_observations`

### 10.1 职责

证书信息既可以放在 `security_scan_records.cert_summary` 中，也可以单独建表。考虑到 MITM 是重点能力，建议单独建表。

### 10.2 建议字段

```sql
CREATE TABLE security_certificate_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NOT NULL,
    proxy_id BIGINT UNSIGNED NOT NULL,

    target_host VARCHAR(255) NOT NULL,
    access_mode VARCHAR(32) NOT NULL,
    subject TEXT DEFAULT NULL,
    issuer TEXT DEFAULT NULL,
    serial_number VARCHAR(255) DEFAULT NULL,
    not_before DATETIME DEFAULT NULL,
    not_after DATETIME DEFAULT NULL,
    fingerprint_sha256 CHAR(64) DEFAULT NULL,
    public_key_algorithm VARCHAR(64) DEFAULT NULL,
    public_key_sha256 CHAR(64) DEFAULT NULL,
    is_self_signed TINYINT(1) DEFAULT NULL,
    verify_ok TINYINT(1) DEFAULT NULL,
    verify_error TEXT DEFAULT NULL,
    chain_summary JSON DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_record_id (record_id),
    KEY idx_proxy_target (proxy_id, target_host),
    KEY idx_fingerprint (fingerprint_sha256),
    KEY idx_access_mode (access_mode),
    CONSTRAINT fk_security_certificate_observations_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_security_certificate_observations_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 10.3 `access_mode` 建议取值

1. `direct`
2. `proxy`

批判性建议：

1. 如果第一版只做证书摘要，可以暂时不建这张表，把摘要放在 `cert_summary`。
2. 如果 MITM 是研究重点，建议建表，因为证书指纹、issuer、self-signed 这些字段后续会被频繁查询。

## 11. 表八：资源观测表 `security_resource_observations`

### 11.1 职责

保存图片、JS、CSS、下载文件等资源在直连与代理路径下的差异摘要。

### 11.2 建议字段

```sql
CREATE TABLE security_resource_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED NOT NULL,
    proxy_id BIGINT UNSIGNED NOT NULL,

    resource_url VARCHAR(2048) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    expected_hash CHAR(64) DEFAULT NULL,
    direct_hash CHAR(64) DEFAULT NULL,
    proxy_hash CHAR(64) DEFAULT NULL,
    direct_size INT DEFAULT NULL,
    proxy_size INT DEFAULT NULL,
    expected_mime_type VARCHAR(128) DEFAULT NULL,
    direct_mime_type VARCHAR(128) DEFAULT NULL,
    proxy_mime_type VARCHAR(128) DEFAULT NULL,

    is_modified TINYINT(1) NOT NULL DEFAULT 0,
    modification_type VARCHAR(64) DEFAULT NULL,
    risk_level VARCHAR(32) DEFAULT NULL,
    evidence JSON DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_record_id (record_id),
    KEY idx_proxy_resource_type (proxy_id, resource_type),
    KEY idx_is_modified (is_modified),
    KEY idx_modification_type (modification_type),
    CONSTRAINT fk_security_resource_observations_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_security_resource_observations_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 11.3 是否第一版必须做

建议第一版就做，但可以简化字段。

资源替换是你后续目标中的核心能力之一，只把它压缩成 `resource_summary` 会影响后续分析。至少应该记录每个异常资源的 URL、类型、直连 hash、代理 hash 和异常类型。

## 12. 表九：证据文件表 `security_evidence_files`

### 12.1 职责

保存原始证据文件的索引，而不是把所有原始内容直接塞进数据库。

例如：

1. 直连 HTML 快照。
2. 代理 HTML 快照。
3. DOM diff JSON。
4. 网络请求日志。
5. 证书链 JSON。
6. 被替换资源样本。
7. 浏览器截图。

### 12.2 建议字段

```sql
CREATE TABLE security_evidence_files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    record_id BIGINT UNSIGNED DEFAULT NULL,
    event_id BIGINT UNSIGNED DEFAULT NULL,
    proxy_id BIGINT UNSIGNED NOT NULL,

    evidence_type VARCHAR(64) NOT NULL,
    storage_type VARCHAR(32) NOT NULL DEFAULT 'local_file',
    file_path VARCHAR(2048) NOT NULL,
    sha256 CHAR(64) DEFAULT NULL,
    size_bytes BIGINT DEFAULT NULL,
    mime_type VARCHAR(128) DEFAULT NULL,
    summary TEXT DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_record_id (record_id),
    KEY idx_event_id (event_id),
    KEY idx_proxy_id (proxy_id),
    KEY idx_evidence_type (evidence_type),
    CONSTRAINT fk_security_evidence_files_record
        FOREIGN KEY (record_id) REFERENCES security_scan_records(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_security_evidence_files_event
        FOREIGN KEY (event_id) REFERENCES security_behavior_events(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_security_evidence_files_proxy
        FOREIGN KEY (proxy_id) REFERENCES proxies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 12.3 证据类型建议

`evidence_type` 建议取值：

1. `direct_html`
2. `proxy_html`
3. `dom_diff`
4. `text_diff`
5. `resource_sample`
6. `cert_chain`
7. `network_log`
8. `browser_screenshot`
9. `browser_dom`

批判性建议：

1. 不要默认保存所有完整响应，否则磁盘和数据库都会很快膨胀。
2. 默认保存摘要，只有异常时保存完整证据。
3. 大文件放本地 evidence 目录，数据库只保存索引。

## 13. 蜜罐目标表设计

如果蜜罐页面和资源是固定代码，也可以不入库，只用 manifest 文件管理。

如果你希望前端能管理蜜罐目标，建议新增以下两张表。

### 13.1 蜜罐目标表 `honeypot_targets`

```sql
CREATE TABLE honeypot_targets (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    path VARCHAR(512) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    expected_status_code INT NOT NULL DEFAULT 200,
    expected_mime_type VARCHAR(128) DEFAULT NULL,
    expected_sha256 CHAR(64) DEFAULT NULL,
    manifest JSON DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_honeypot_path (path),
    KEY idx_enabled_type (enabled, target_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 13.2 蜜罐请求日志表 `honeypot_request_logs`

```sql
CREATE TABLE honeypot_request_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    request_id CHAR(36) DEFAULT NULL,
    target_id BIGINT UNSIGNED DEFAULT NULL,

    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    method VARCHAR(16) NOT NULL,
    path VARCHAR(1024) NOT NULL,
    source_ip VARCHAR(64) DEFAULT NULL,
    user_agent VARCHAR(512) DEFAULT NULL,
    request_headers JSON DEFAULT NULL,
    response_status_code INT DEFAULT NULL,
    response_body_hash CHAR(64) DEFAULT NULL,
    response_size INT DEFAULT NULL,

    PRIMARY KEY (id),
    KEY idx_requested_at (requested_at),
    KEY idx_source_ip (source_ip),
    KEY idx_path (path),
    CONSTRAINT fk_honeypot_request_logs_target
        FOREIGN KEY (target_id) REFERENCES honeypot_targets(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 13.3 第一版建议

第一版可以先不建这两张表。

蜜罐目标先用代码和 manifest 文件固定下来，会更简单、更稳定。等前端需要管理蜜罐目标时再入库。

## 14. 表关系概览

核心关系如下：

```text
proxies
  ├── proxy_check_records
  ├── security_scan_records
  │     ├── security_behavior_events
  │     ├── security_certificate_observations
  │     ├── security_resource_observations
  │     └── security_evidence_files
  └── security_behavior_events

security_scan_batches
  ├── security_scan_records
  └── security_behavior_events
```

关键原则：

1. `proxies` 是当前状态。
2. `security_scan_batches` 是任务维度。
3. `security_scan_records` 是轮次维度。
4. `security_behavior_events` 是异常事件维度。
5. `security_evidence_files` 是证据文件索引。

## 15. JSON 字段使用建议

MySQL 支持 JSON 字段，但不要滥用。

适合放 JSON 的内容：

1. 请求参数。
2. 风险标签数组。
3. 差分摘要。
4. 证书链摘要。
5. 资源异常摘要。
6. 不常用于筛选的扩展 metadata。

不适合只放 JSON 的内容：

1. `risk_level`
2. `behavior_class`
3. `event_type`
4. `proxy_id`
5. `batch_id`
6. `is_anomalous`
7. `created_at`
8. `country`
9. `proxy_type`

原因是这些字段后续会频繁用于筛选、排序、统计和前端图表。如果只放 JSON，查询会慢，索引也麻烦。

## 16. 索引设计建议

第一版重点索引：

1. `proxies(ip, port)` 唯一索引。
2. `proxies(is_alive, proxy_type)` 用于基础代理筛选。
3. `proxies(security_risk)` 用于安全等级筛选。
4. `proxies(behavior_class)` 用于行为分类筛选。
5. `security_scan_batches(batch_id)` 用于任务查询。
6. `security_scan_records(batch_id, proxy_id, round_index)` 用于查看某批次某代理多轮记录。
7. `security_scan_records(proxy_id, started_at)` 用于查看单代理历史。
8. `security_scan_records(stage, checker_name)` 用于按检测阶段统计。
9. `security_scan_records(applicability)` 用于统计不适用检测。
10. `security_scan_records(execution_status)` 用于任务状态和失败排查。
11. `security_scan_records(funnel_stage)` 用于展示漏斗层级。
12. `security_behavior_events(proxy_id, event_type, created_at)` 用于查看某代理异常事件。
13. `security_behavior_events(event_type)` 用于异常类型统计。
14. `security_resource_observations(is_modified)` 用于资源异常筛选。
15. `security_certificate_observations(fingerprint_sha256)` 用于证书指纹聚合。

批判性建议：

1. 不要一开始加太多索引，写入会变慢。
2. 先围绕前端查询和统计接口加索引。
3. 后续根据慢查询日志补索引。

## 17. 数据保留策略

安全检测数据会增长很快，需要提前规划保留策略。

建议：

1. `proxies` 永久保存。
2. `proxy_check_records` 保留最近 30 到 90 天。
3. `security_scan_batches` 保留长期摘要。
4. `security_scan_records` 保留最近 90 天，或按批次归档。
5. `security_behavior_events` 建议长期保存，因为它是研究价值最高的数据。
6. `security_evidence_files` 只长期保存异常样本，正常样本定期清理。
7. 浏览器截图、HTML 快照、资源样本设置文件大小和保留周期上限。

证据保存策略：

1. 正常结果只保存 hash 和摘要。
2. 异常结果保存关键证据。
3. 高风险结果保存完整证据。
4. critical 事件可以长期保留。

## 18. 一次性建表与分阶段启用建议

用户当前偏好是一次性建好完整表结构，避免后续频繁改表导致数据丢失风险。因此本节中的阶段划分不再表示“分阶段建表”，而表示“表一次性创建后，功能分阶段启用”。

建议：

1. 表结构一次性创建完整版本。
2. 功能可以按 MVP、证书资源增强、来源分析、蜜罐管理逐步启用。
3. 未启用的表可以先空置。
4. 后续尽量通过新增 nullable 字段或新增独立表扩展，避免破坏性变更。

### 第一阶段：启用最小安全检测能力

先启用：

1. 扩展 `proxies` 安全汇总字段。
2. 使用 `security_scan_batches`。
3. 使用 `security_scan_records`。
4. 使用 `security_behavior_events`。
5. 使用 `security_evidence_files`。
6. 在 `security_scan_records` 中写入检测阶段、适用性、执行状态和跳过原因。

表已创建但功能可暂缓启用：

1. `proxy_sources`
2. `proxy_check_records`
3. `security_certificate_observations`
4. `security_resource_observations`
5. `honeypot_targets`
6. `honeypot_request_logs`

适合目标：

1. 完成蜜罐直连 vs 代理检测。
2. 保存每轮检测摘要。
3. 保存异常事件。
4. 前端能展示安全风险和事件列表。
5. 前端能区分“正常”“异常”“不适用”“被跳过”“执行出错”。
6. 能说明某个代理为什么没有执行 MITM、多轮或浏览器检测。

### 第二阶段：资源与证书分析增强

增加：

1. `security_certificate_observations`
2. `security_resource_observations`

适合目标：

1. 做 MITM 证书分析。
2. 做资源替换统计。
3. 支持按证书指纹、资源类型、异常类型聚合。

### 第三阶段：来源与基础历史分析

增加：

1. `proxy_sources`
2. `proxy_check_records`

适合目标：

1. 分析代理来源质量。
2. 分析代理长期稳定性。
3. 前端展示来源管理和代理性能历史。

### 第四阶段：蜜罐管理与高级研究

增加：

1. `honeypot_targets`
2. `honeypot_request_logs`

适合目标：

1. 前端管理蜜罐目标。
2. 分析蜜罐访问日志。
3. 做更复杂的实验设计。

## 19. 迁移方式建议

你现在只有一张表，因此建议从简单但明确的迁移方式开始：

1. 新建 `migrations/` 目录。
2. 每次数据库结构变化写一个 SQL 文件。
3. 文件名包含序号和说明，例如 `001_extend_proxies_security_fields.sql`。
4. 不再依赖运行时代码自动 `ALTER TABLE`。
5. 后续如果项目变复杂，再引入 Alembic 或类似迁移工具。

建议迁移目录：

```text
migrations/
  001_extend_proxies_security_fields.sql
  002_create_security_scan_batches.sql
  003_create_security_scan_records.sql
  004_create_security_behavior_events.sql
  005_create_security_evidence_files.sql
```

批判性建议：

1. 不要在业务 Repository 初始化时偷偷改表。
2. 建表和业务逻辑分离，后续部署会更可控。
3. 每个迁移文件都应该可以独立审查。

## 20. 一次性完整建表清单

用户已确认希望一次性建好所有表。因此当前推荐建表清单改为完整版本。

必须存在：

1. `proxies`

一次性创建：

1. `security_scan_batches`
2. `security_scan_records`
3. `security_behavior_events`
4. `security_evidence_files`
5. `security_certificate_observations`
6. `security_resource_observations`
7. `proxy_sources`
8. `proxy_check_records`
9. `honeypot_targets`
10. `honeypot_request_logs`

第一批建表必须支持的关键字段：

1. `security_scan_batches.scan_policy`
2. `security_scan_batches.max_scan_depth`
3. `security_scan_records.funnel_stage`
4. `security_scan_records.stage`
5. `security_scan_records.checker_name`
6. `security_scan_records.scan_depth`
7. `security_scan_records.applicability`
8. `security_scan_records.execution_status`
9. `security_scan_records.skip_reason`
10. `security_scan_records.precondition_summary`

这样设计的好处是：

1. 避免后续频繁改表。
2. 降低迁移导致数据丢失的风险。
3. 一开始就能支撑安全检测、证书观测、资源观测、来源管理、蜜罐目标和前端可视化。
4. 功能可以逐步启用，但表结构先稳定下来。
5. `proxies` 仍然保持为快速列表查询的主表。
6. 安全研究数据不会污染基础代理资产数据。

## 21. 待确认问题

后续真正落 SQL 前，建议先确认这些问题：

1. 当前 `proxies` 表真实字段和类型是什么。
2. 是否需要备份并重建 `proxies` 表，还是基于现有表安全 `ALTER`。
3. 外键删除策略是否全部使用 `CASCADE`，还是部分历史表使用保留策略。
4. 是否希望删除代理时连带删除历史记录。
5. 证据文件是保存在本地磁盘、数据库，还是对象存储。
6. 第一版安全检测是否需要异步批次任务。
7. 前端第一版需要展示哪些安全字段。
8. 是否要长期保存所有异常事件。
9. 是否需要对研究数据做导出。
10. 是否要引入正式迁移工具。
11. 漏斗每一层的进入条件是什么。
12. `skipped` 和 `not_applicable` 在前端如何展示。
13. 低稳定代理是否保留抽样进入轻量安全检测。
14. 浏览器深度检测是否设置每日或每批次预算。

已确认事项：

1. MySQL 版本支持 JSON 字段，已测试版本为 `8.0.45`。
2. 允许使用外键约束。
3. 用户希望一次性创建完整表结构。
4. 当前项目配置可以连接到 `proxy_pool` 数据库。

## 22. 总结

后续数据库设计的核心不是“再给 `proxies` 加很多列”，而是建立清晰的数据层次：

1. `proxies` 回答“这个代理当前是什么状态”。
2. `security_scan_batches` 回答“这次安全检测任务是什么”。
3. `security_scan_records` 回答“某个代理某一轮、某一层检测发生了什么，以及为什么某些检测没有运行”。
4. `security_behavior_events` 回答“系统识别出了哪些明确异常行为”。
5. `security_evidence_files` 回答“证据在哪里，如何追溯”。

这个结构会让后续蜜罐检测、DOM 差分、资源替换、MITM、多轮观测、浏览器深度检测和前端分析都更稳。尤其是漏斗式检测下，数据库必须明确表达“适用但跳过”“不适用”“执行出错”“完成但正常”“完成且异常”这些状态。数据库稍微多几张表和几个状态字段，换来的是后面不会被一张巨大的混乱表拖住，也不会把“未检测”误判成“安全”。

## 23. 决策记录

| 日期 | 决策 | 原因 | 影响 |
| --- | --- | --- | --- |
| 2026-04-17 | 允许使用 MySQL 外键约束 | 用户明确允许使用外键 | 后续建表 SQL 可以包含外键，并需要谨慎设计删除策略 |
| 2026-04-17 | 一次性创建完整规划表结构 | 用户希望避免后续频繁改表导致数据丢失风险 | 数据库迁移应一次性包含安全检测、证书观测、资源观测、来源、基础历史、蜜罐目标和蜜罐日志表 |
| 2026-04-17 | 当前项目配置可连接 MySQL | 已通过 `.venv` 只读连接测试，数据库为 `proxy_pool`，MySQL 版本 `8.0.45` | 可以基于现有连接配置编写和执行迁移，但真正建表前仍需用户授权 |

## 24. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-04-17 | 根据用户新决策，将数据库规划从分阶段建表调整为一次性完整建表、分阶段启用功能 |

## 与当前架构审计的配合要求

本数据库设计需要和 `docs/project-architecture-audit.md` 配合执行。审计文档已经确认，当前代码中 `storage/mysql/proxy_repository.py` 仍然存在运行时自动补列的做法，这只适合早期开发，不适合后续一次性完整建表和安全研究数据沉淀。

因此，后续数据库实现必须遵守以下要求：

1. 不再依赖 repository 初始化时自动 `ALTER TABLE`。
2. 使用明确的 SQL migration 文件管理 schema。
3. 建表、重建表、迁移已有数据前必须备份当前数据库。
4. 所有写入数据库结构的操作都需要用户明确授权。
5. `proxies` 主表只保存最新汇总状态。
6. `security_scan_batches`、`security_scan_records`、`security_behavior_events`、`security_evidence_files` 等表保存过程数据。
7. 失败、超时、跳过、不可适用的检测记录同样需要入库。
8. 适用性和执行状态必须使用稳定枚举值，不要依赖中文展示文案。

这意味着数据库可以一次性创建完整结构，但业务功能仍然应分阶段启用。一次性建全 schema 的目的，是降低后续频繁改表带来的数据风险，而不是要求一次性实现全部检测能力。
