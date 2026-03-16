import { ProxyNode, DashboardStats } from '../types';

const API_BASE_URL = 'http://localhost:5000/api';

export const api = {
  async getProxies(params: {
    country?: string;
    type?: string;
    status?: string;
    sort?: string;
    page?: number;
    limit?: number;
  }) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) {
        queryParams.append(key, value.toString());
      }
    });
    
    console.log('发送 API 请求:', `${API_BASE_URL}/proxies?${queryParams}`);
    const response = await fetch(`${API_BASE_URL}/proxies?${queryParams}`);
    if (!response.ok) {
      throw new Error('Failed to fetch proxies');
    }
    const data = await response.json();
    console.log('API 响应:', data);
    return data;
  },

  async getStats() {
    const response = await fetch(`${API_BASE_URL}/stats`);
    if (!response.ok) {
      throw new Error('Failed to fetch stats');
    }
    return response.json() as Promise<DashboardStats>;
  },

  async getFilters() {
    const response = await fetch(`${API_BASE_URL}/filters`);
    if (!response.ok) {
      throw new Error('Failed to fetch filters');
    }
    return response.json();
  },

  async deleteProxy(ip: string, port: number) {
    const response = await fetch(`${API_BASE_URL}/proxies/${ip}:${port}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete proxy');
    }
    return response.json();
  },

  async refreshProxies() {
    const response = await fetch(`${API_BASE_URL}/refresh`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to refresh proxies');
    }
    return response.json();
  },
};
