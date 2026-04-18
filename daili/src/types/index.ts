export type ProxyStatus = 'alive' | 'slow' | 'dead';
export type AnonymityLevel = 'high_anonymous' | 'anonymous' | 'transparent' | 'unknown';
export type RiskLevel = 'unknown' | 'low' | 'medium' | 'high' | 'critical';
export type ExecutionStatus = 'planned' | 'running' | 'completed' | 'skipped' | 'error' | 'timeout';
export type Applicability = 'applicable' | 'not_applicable' | 'unknown';
export type ScanOutcome = 'normal' | 'anomalous' | 'not_applicable' | 'skipped' | 'error' | 'timeout';
export type BehaviorClass =
  | 'normal'
  | 'content_tampering'
  | 'ad_injection'
  | 'script_injection'
  | 'redirect_manipulation'
  | 'resource_replacement'
  | 'mitm_suspected'
  | 'stealthy_malicious'
  | 'unstable_but_non_malicious';

export interface ProxyNode {
  id: string;
  ip: string;
  port: number;
  source: string;
  location: {
    country: string;
    city: string;
    flag: string;
    lat: number;
    lng: number;
  };
  types: Array<'HTTP' | 'HTTPS' | 'SOCKS5'>;
  anonymity: AnonymityLevel;
  speed: number;
  successRate: number;
  businessScore: number;
  qualityScore: number;
  securityRisk: RiskLevel;
  securityScore?: number | null;
  behaviorClass: BehaviorClass;
  securityFlags: string[];
  securitySummary: {
    hasContentTampering: boolean;
    hasResourceReplacement: boolean;
    hasMitmRisk: boolean;
    anomalyTriggerCount: number;
    securityCheckCount: number;
    anomalyTriggerRate?: number | null;
    triggerPattern?: string;
    confidenceLevel?: string;
    evidenceSummary?: Record<string, unknown> | null;
    lastSecurityCheck?: string | null;
  };
  lastCheck: string;
  status: ProxyStatus;
  statusColor?: string;
}

export interface ProxyListResponse {
  data: ProxyNode[];
  total: number;
  page: number;
  limit: number;
}

export interface ProxyQuery {
  country?: string;
  type?: string;
  status?: ProxyStatus | '';
  sort?: string;
  page?: number;
  limit?: number;
}

export interface DashboardStats {
  totalProxies: number;
  activeProxies: number;
  countriesCount: number;
  avgResponseTime: number;
  responseTimeChange: number;
  activeChange: number;
  highQualityProxies?: number;
  avgBusinessScore?: number;
}

export interface SecurityScanRecordCount {
  executionStatus: ExecutionStatus;
  outcome: ScanOutcome;
  count: number;
}

export interface SecurityTopEvent {
  eventType: string;
  riskLevel: RiskLevel;
  count: number;
}

export interface SecurityBatchSummary {
  batchId: string;
  status: string;
  scanMode?: string;
  scanPolicy?: string;
  maxScanDepth?: string;
  targetProxyCount: number;
  checkedProxyCount: number;
  skippedProxyCount?: number;
  errorProxyCount?: number;
  normalProxyCount?: number;
  suspiciousProxyCount?: number;
  maliciousProxyCount?: number;
  anomalyEventCount: number;
  startedAt?: string | null;
  finishedAt?: string | null;
  elapsedSeconds?: number | null;
  errorMessage?: string | null;
}

export interface SecurityStageStat {
  funnelStage: number;
  stage: string;
  executionStatus: ExecutionStatus;
  outcome: ScanOutcome;
  count: number;
}

export interface SecurityScanRecord {
  id: number;
  proxy: string;
  proxyIp: string;
  proxyPort: number;
  roundIndex: number;
  funnelStage: number;
  stage: string;
  checkerName: string;
  scanDepth: string;
  applicability: Applicability;
  executionStatus: ExecutionStatus;
  outcome: ScanOutcome;
  skipReason?: string | null;
  preconditionSummary?: Record<string, unknown>;
  elapsedMs?: number | null;
  isAnomalous: boolean;
  riskLevel: RiskLevel;
  riskTags: string[];
  errorMessage?: string | null;
  createdAt?: string | null;
}

export interface SecurityBatchDetail {
  batch: SecurityBatchSummary;
  stageStats: SecurityStageStat[];
  records: SecurityScanRecord[];
}

export interface ProxySecurityDetail {
  stageStats: SecurityStageStat[];
  records: SecurityScanRecord[];
  events: SecurityEvent[];
  batches: SecurityBatchSummary[];
  resources: SecurityResourceObservation[];
  certificates: SecurityCertificateObservation[];
}

export interface ProxyDetailResponse {
  proxy: ProxyNode;
  security: ProxySecurityDetail;
}

export interface SecurityOverview {
  totalProxies: number;
  activeProxies: number;
  uncheckedProxies: number;
  normalProxies: number;
  suspiciousProxies: number;
  maliciousProxies: number;
  riskCounts: Partial<Record<RiskLevel, number>>;
  behaviorCounts: Record<string, number>;
  scanRecordCounts: SecurityScanRecordCount[];
  funnelStats: SecurityFunnelOverviewStat[];
  riskTrend: SecurityRiskTrendPoint[];
  protocolCounts: ProtocolCounts;
  geoRiskRanking: GeoCountrySummary[];
  topEvents: SecurityTopEvent[];
  recentBatches: SecurityBatchSummary[];
}

export interface SecurityBatchListResponse {
  data: SecurityBatchSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface SecurityEvent {
  id: number;
  eventType: string;
  behaviorClass?: string | null;
  riskLevel: RiskLevel;
  confidence?: number | null;
  targetUrl?: string | null;
  selector?: string | null;
  summary?: string | null;
  createdAt?: string | null;
}

export interface SecurityEventListResponse {
  data: SecurityEvent[];
  total: number;
  page: number;
  limit: number;
}

export interface SecurityResourceObservation {
  id: number;
  recordId?: number | null;
  proxyId?: number | null;
  resourceUrl: string;
  resourceType?: string | null;
  directStatusCode?: number | null;
  proxyStatusCode?: number | null;
  directSha256?: string | null;
  proxySha256?: string | null;
  directSize?: number | null;
  proxySize?: number | null;
  directMimeType?: string | null;
  proxyMimeType?: string | null;
  isModified: boolean;
  failureType?: string | null;
  riskLevel: RiskLevel;
  summary?: Record<string, unknown> | null;
  observedAt?: string | null;
}

export interface SecurityCertificateObservation {
  id: number;
  recordId?: number | null;
  proxyId?: number | null;
  observationMode: 'direct' | 'proxy' | string;
  host: string;
  port: number;
  fingerprintSha256?: string | null;
  issuer?: string | null;
  subject?: string | null;
  notBefore?: string | null;
  notAfter?: string | null;
  isSelfSigned: boolean;
  isMismatch: boolean;
  riskLevel: RiskLevel;
  certificateSummary?: Record<string, unknown> | null;
  errorMessage?: string | null;
  observedAt?: string | null;
}

export interface GeoCountrySummary {
  countryCode: string;
  countryName: string;
  totalProxies: number;
  activeProxies: number;
  uncheckedProxies: number;
  normalProxies: number;
  suspiciousProxies: number;
  maliciousProxies: number;
  avgResponseTimeMs?: number;
  protocols: {
    http: number;
    https: number;
    socks5: number;
  };
  topRiskLevel: RiskLevel;
  topEventTypes: SecurityTopEvent[];
}

export interface SecurityFunnelOverviewStat {
  funnelStage: number;
  stage: string;
  total: number;
  normal: number;
  anomalous: number;
  notApplicable: number;
  skipped: number;
  error: number;
  timeout: number;
}

export interface SecurityRiskTrendPoint {
  date: string;
  totalRecords: number;
  checkedProxies: number;
  anomalousRecords: number;
  highRiskRecords: number;
  anomalyRate: number;
}

export interface ProtocolCounts {
  http: number;
  https: number;
  socks5: number;
  unknown?: number;
}
