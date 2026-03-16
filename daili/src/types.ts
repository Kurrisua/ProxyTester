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
  types: ('HTTP' | 'HTTPS' | 'SOCKS5')[];
  anonymity: '高匿' | '匿名' | '透明';
  speed: number; // ms
  successRate: number; // percentage
  businessScore: number; // 业务可用性评分 (0-3)
  qualityScore: number; // 综合质量评分 (0-100)
  lastCheck: string;
  status: '存活' | '失效' | '缓慢';
}

export interface DashboardStats {
  totalProxies: number;
  activeProxies: number;
  countriesCount: number;
  avgResponseTime: number;
  responseTimeChange: number;
  activeChange: number;
}
