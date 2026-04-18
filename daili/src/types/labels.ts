import { AnonymityLevel, Applicability, BehaviorClass, ExecutionStatus, ProxyStatus, RiskLevel, ScanOutcome } from './index';

export const PROXY_STATUS_LABELS: Record<ProxyStatus, string> = {
  alive: '存活',
  slow: '缓慢',
  dead: '失效',
};

export const ANONYMITY_LABELS: Record<AnonymityLevel, string> = {
  high_anonymous: '高匿',
  anonymous: '匿名',
  transparent: '透明',
  unknown: '未知',
};

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  unknown: '未检测',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '严重风险',
};

export const EXECUTION_STATUS_LABELS: Record<ExecutionStatus, string> = {
  planned: '已计划',
  running: '执行中',
  completed: '已完成',
  skipped: '已跳过',
  error: '执行错误',
  timeout: '超时',
};

export const APPLICABILITY_LABELS: Record<Applicability, string> = {
  applicable: '适用',
  not_applicable: '不适用',
  unknown: '未知',
};

export const SCAN_OUTCOME_LABELS: Record<ScanOutcome, string> = {
  normal: '正常',
  anomalous: '异常',
  not_applicable: '不适用',
  skipped: '已跳过',
  error: '错误',
  timeout: '超时',
};

export const BEHAVIOR_CLASS_LABELS: Record<BehaviorClass, string> = {
  normal: '正常',
  content_tampering: '内容篡改',
  ad_injection: '广告注入',
  script_injection: '脚本注入',
  redirect_manipulation: '跳转操控',
  resource_replacement: '资源替换',
  mitm_suspected: '疑似中间人',
  stealthy_malicious: '隐蔽恶意',
  unstable_but_non_malicious: '不稳定但非恶意',
};
