import { apiRequest } from './client';
import {
  GeoCountrySummary,
  GeoRegionDetail,
  HoneypotTarget,
  RiskLevel,
  SecurityBatchDetail,
  SecurityBatchListResponse,
  SecurityBehaviorStat,
  SecurityEventDetail,
  SecurityEventListResponse,
  SecurityOverview,
  SecurityRiskTrendPoint,
  SecurityScanCreateResponse,
} from '../types';

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  });
  const suffix = query.toString();
  return suffix ? `?${suffix}` : '';
}

export function getSecurityOverview() {
  return apiRequest<SecurityOverview>('/security/overview');
}

export function getSecurityBatches(params: { page?: number; limit?: number } = {}) {
  return apiRequest<SecurityBatchListResponse>(`/security/batches${buildQuery(params)}`);
}

export function getSecurityBatchDetail(batchId: string, params: { recordLimit?: number } = {}) {
  return apiRequest<SecurityBatchDetail>(`/security/batches/${encodeURIComponent(batchId)}${buildQuery(params)}`);
}

export function getSecurityEvents(params: { page?: number; limit?: number; eventType?: string; riskLevel?: string; country?: string } = {}) {
  return apiRequest<SecurityEventListResponse>(`/security/events${buildQuery(params)}`);
}

export function getSecurityEventDetail(eventId: number) {
  return apiRequest<SecurityEventDetail>(`/security/events/${eventId}`);
}

export function getSecurityGeoSummary() {
  return apiRequest<{ data: GeoCountrySummary[] }>('/security/geo');
}

export function getSecurityGeoRegion(country: string) {
  return apiRequest<GeoRegionDetail>(`/security/geo/${encodeURIComponent(country)}`);
}

export function getSecurityBehaviorStats() {
  return apiRequest<{ data: SecurityBehaviorStat[] }>('/security/stats/behavior');
}

export function getSecurityRiskTrend(days = 14) {
  return apiRequest<{ data: SecurityRiskTrendPoint[] }>(`/security/stats/risk-trend${buildQuery({ days })}`);
}

export function getSecurityEventTypeDistribution() {
  return apiRequest<{ data: Array<{ eventType: string; riskLevel: RiskLevel; count: number }> }>('/security/analytics/event-types');
}

export function getSecurityRiskDistribution() {
  return apiRequest<Partial<Record<RiskLevel, number>>>('/security/analytics/risk-distribution');
}

export function getHoneypotManifest() {
  return apiRequest<{ data: HoneypotTarget[] }>('/security/honeypot/manifest');
}

export function createSecurityScan(proxies: string[], maxWorkers = 20) {
  return apiRequest<SecurityScanCreateResponse>('/security/scans', {
    method: 'POST',
    body: JSON.stringify({ proxies, maxWorkers }),
  });
}

export function scanSecurityProxy(ip: string, port: number, maxWorkers = 1) {
  return apiRequest<SecurityScanCreateResponse>(`/security/proxies/${encodeURIComponent(ip)}:${port}/scan`, {
    method: 'POST',
    body: JSON.stringify({ maxWorkers }),
  });
}
