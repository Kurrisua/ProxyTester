import { apiRequest } from './client';
import { DashboardStats, ProxyDetailResponse, ProxyListResponse, ProxyQuery } from '../types';

function buildQuery(params: ProxyQuery): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.append(key, String(value));
    }
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : '';
}

export function getProxies(params: ProxyQuery) {
  return apiRequest<ProxyListResponse>(`/proxies${buildQuery(params)}`);
}

export function getProxyDetail(ip: string, port: number) {
  return apiRequest<ProxyDetailResponse>(`/proxies/${encodeURIComponent(ip)}:${port}`);
}

export function getStats() {
  return apiRequest<DashboardStats>('/stats');
}

export function getFilters() {
  return apiRequest<{ countries: string[]; proxyTypes: string[]; mainCountry: string }>('/filters');
}

export function deleteProxy(ip: string, port: number) {
  return apiRequest<{ success: boolean }>(`/proxies/${ip}:${port}`, { method: 'DELETE' });
}

export function refreshProxies() {
  return apiRequest<{ success: boolean; message: string }>('/refresh', { method: 'POST' });
}
