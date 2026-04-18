import { apiRequest } from './client';
import { GeoCountrySummary, SecurityBatchDetail, SecurityBatchListResponse, SecurityOverview, SecurityEventListResponse } from '../types';

export function getSecurityOverview() {
  return apiRequest<SecurityOverview>('/security/overview');
}

export function getSecurityBatches(params: { page?: number; limit?: number } = {}) {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.limit) query.set('limit', String(params.limit));
  const suffix = query.toString() ? `?${query}` : '';
  return apiRequest<SecurityBatchListResponse>(`/security/batches${suffix}`);
}

export function getSecurityBatchDetail(batchId: string, params: { recordLimit?: number } = {}) {
  const query = new URLSearchParams();
  if (params.recordLimit) query.set('recordLimit', String(params.recordLimit));
  const suffix = query.toString() ? `?${query}` : '';
  return apiRequest<SecurityBatchDetail>(`/security/batches/${encodeURIComponent(batchId)}${suffix}`);
}

export function getSecurityEvents(params: { page?: number; limit?: number; eventType?: string; riskLevel?: string; country?: string } = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  });
  const suffix = query.toString() ? `?${query}` : '';
  return apiRequest<SecurityEventListResponse>(`/security/events${suffix}`);
}

export function getSecurityGeoSummary() {
  return apiRequest<{ data: GeoCountrySummary[] }>('/security/geo');
}
