import React, { useState, useEffect } from 'react';
import { ShieldCheck, RefreshCw, Trash2, Search, Bell, User, Globe, Activity, Shield, FileText, ChevronLeft, ChevronRight, Layers, Zap, MoreVertical, ChevronDown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from './lib/utils';
import { api } from './lib/api';
import { ProxyNode, DashboardStats } from './types';

// --- Components ---

const NavItem = ({ icon: Icon, label, active, onClick }: { icon: any, label: string, active?: boolean, onClick: () => void }) => (
  <button 
    onClick={onClick}
    className={cn(
      "flex flex-col items-center gap-1 px-4 py-2 transition-all relative",
      active ? "text-neon-cyan" : "text-slate-400 hover:text-white"
    )}
  >
    <Icon size={20} />
    <span className="text-xs font-medium">{label}</span>
    {active && (
      <motion.div 
        layoutId="nav-underline"
        className="absolute -bottom-[1px] left-0 right-0 h-0.5 bg-neon-cyan"
      />
    )}
  </button>
);

const StatCard = ({ title, value, icon: Icon, trend, trendColor, chart }: { title: string, value: string | number, icon: any, trend?: string, trendColor?: string, chart?: React.ReactNode }) => (
  <div className="bg-slate-card p-5 rounded-xl border border-slate-800 shadow-xl">
    <div className="flex justify-between items-start mb-4">
      <div className={cn("p-2 rounded-lg", title === '活跃代理数' ? "bg-cyan-500/10" : title === '平均响应时间' ? "bg-rose-500/10" : "bg-slate-700/50")}>
        <Icon className={cn("w-5 h-5", title === '活跃代理数' ? "text-neon-cyan" : title === '平均响应时间' ? "text-amber-400" : "text-slate-300")} />
      </div>
      {trend && (
        <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", trendColor || "text-emerald-400 bg-emerald-400/10")}>
          {trend}
        </span>
      )}
    </div>
    <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
    <p className="text-2xl font-bold text-white">{value}</p>
    <div className="mt-4">
      {chart || <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-slate-400 w-full" /></div>}
    </div>
  </div>
);

const ProxyRow = ({ node, onDelete }: { node: ProxyNode, onDelete?: () => void, key?: string | number }) => (
  <tr className={cn("hover:bg-slate-700/30 transition-colors", node.status === '失效' && "bg-rose-500/[0.02]")}>
    <td className="px-6 py-4">
      <div className={cn("font-mono", node.status === '失效' ? "text-slate-500" : "text-neon-cyan")}>{node.ip}</div>
      <div className="text-[10px] text-slate-500">Port: {node.port}</div>
    </td>
    <td className="px-4 py-4 text-slate-300">{node.source}</td>
    <td className="px-4 py-4">
      <div className={cn("flex items-center gap-2", node.status === '失效' && "opacity-50")}>
        <span className="w-5 h-3.5 bg-slate-700 rounded-sm overflow-hidden flex items-center justify-center text-[8px]">{node.location.flag}</span>
        <span>{node.location.country}, {node.location.city}</span>
      </div>
    </td>
    <td className="px-4 py-4 text-slate-400">
      <div className="flex flex-wrap gap-1">
        {node.types.map(t => (
          <span key={t} className={cn(
            "px-1.5 py-0.5 rounded text-[10px] border",
            t === 'SOCKS5' ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
            t === 'HTTP' ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" :
            "bg-purple-500/20 text-purple-400 border-purple-500/30"
          )}>
            {t}
          </span>
        ))}
      </div>
    </td>
    <td className="px-4 py-4">
      <span className={cn(
        "px-2 py-0.5 rounded text-[11px] font-bold border uppercase",
        node.anonymity === '高匿' ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" :
        node.anonymity === '匿名' ? "bg-slate-700/30 text-slate-500 border-slate-700" :
        "bg-slate-700/50 text-slate-400 border-slate-600/20"
      )}>
        {node.anonymity}
      </span>
    </td>
    <td className={cn("px-4 py-4 font-mono", node.status === '失效' ? "text-slate-500" : node.speed < 200 ? "text-emerald-400" : "text-amber-400")}>
      {node.speed > 0 ? `${node.speed}ms` : '超时'}
    </td>
    <td className="px-4 py-4">
      <div className="w-24">
        <div className={cn("flex justify-between text-[10px] mb-1", node.status === '失效' && "text-rose-400")}>
          <span>{node.successRate}%</span>
        </div>
        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={cn("h-full", node.successRate > 90 ? "bg-emerald-500" : node.successRate > 70 ? "bg-amber-500" : "bg-neon-rose")} 
            style={{ width: `${node.successRate}%` }} 
          />
        </div>
      </div>
    </td>
    <td className="px-4 py-4">
      <div className="w-24">
        <div className={cn("flex justify-between text-[10px] mb-1", node.status === '失效' && "text-rose-400")}>
          <span>业务: {node.businessScore}/3</span>
        </div>
        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={cn("h-full", node.businessScore >= 2 ? "bg-emerald-500" : node.businessScore >= 1 ? "bg-amber-500" : "bg-neon-rose")} 
            style={{ width: `${(node.businessScore / 3) * 100}%` }} 
          />
        </div>
      </div>
    </td>
    <td className="px-4 py-4">
      <div className="w-24">
        <div className={cn("flex justify-between text-[10px] mb-1", node.status === '失效' && "text-rose-400")}>
          <span>质量: {node.qualityScore}</span>
        </div>
        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={cn("h-full", node.qualityScore >= 80 ? "bg-emerald-500" : node.qualityScore >= 60 ? "bg-amber-500" : "bg-neon-rose")} 
            style={{ width: `${node.qualityScore}%` }} 
          />
        </div>
      </div>
    </td>
    <td className="px-4 py-4 text-slate-500">{node.lastCheck}</td>
    <td className="px-4 py-4">
      <span className={cn(
        "flex items-center gap-1.5",
        node.status === '存活' ? "text-emerald-400" : node.status === '缓慢' ? "text-amber-400" : "text-neon-rose"
      )}>
        <span className={cn(
          "w-2 h-2 rounded-full",
          node.status === '存活' ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" : 
          node.status === '缓慢' ? "bg-amber-400" : 
          "bg-neon-rose shadow-[0_0_8px_rgba(251,113,133,0.6)]"
        )} />
        {node.status}
      </span>
    </td>
    <td className="px-6 py-4 text-right">
      <button 
        onClick={onDelete}
        className="p-1.5 text-slate-500 hover:text-neon-rose transition-colors"
      >
        <Trash2 size={16} />
      </button>
    </td>
  </tr>
);

// --- Main Views ---

const CustomSelect = ({ label, options, value, onChange }: { label: string, options: string[], value: string, onChange: (val: string) => void }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">{label}</label>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 hover:border-slate-600 transition-colors focus:ring-2 focus:ring-neon-cyan/50"
      >
        <span className="truncate">{value}</span>
        <ChevronDown size={14} className={cn("text-slate-500 transition-transform", isOpen && "rotate-180")} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute z-20 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-2xl py-2 overflow-hidden"
            >
              {options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => {
                    onChange(opt);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-center justify-between px-4 py-2 text-sm transition-colors hover:bg-slate-700",
                    value === opt ? "text-neon-cyan bg-neon-cyan/5" : "text-slate-300"
                  )}
                >
                  {opt}
                  {value === opt && <Check size={14} />}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

const DashboardView = () => {
  const [filters, setFilters] = useState({
    country: '所有国家',
    type: '所有类型',
    status: '所有状态',
    sort: '质量评分 (高-低)'
  });
  const [proxies, setProxies] = useState<ProxyNode[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    totalProxies: 0,
    activeProxies: 0,
    countriesCount: 0,
    avgResponseTime: 0,
    responseTimeChange: 0,
    activeChange: 0
  });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterOptions, setFilterOptions] = useState({
    countries: ['所有国家', '美国', '德国', '日本', '英国', '中国'],
    proxyTypes: ['所有类型', 'HTTP', 'HTTPS', 'SOCKS5'],
    mainCountry: '美国'
  });

  // 获取筛选选项
  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const data = await api.getFilters();
        setFilterOptions({
          countries: ['所有国家', ...data.countries],
          proxyTypes: ['所有类型', ...data.proxyTypes],
          mainCountry: data.mainCountry
        });
      } catch (error) {
        console.error('Failed to fetch filters:', error);
      }
    };
    fetchFilters();
  }, []);

  // 获取统计信息
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };
    fetchStats();
  }, []);

  // 获取代理列表
  useEffect(() => {
    const fetchProxies = async () => {
      setLoading(true);
      try {
        const result = await api.getProxies({
          country: filters.country === '所有国家' ? undefined : filters.country,
          type: filters.type === '所有类型' ? undefined : filters.type,
          status: filters.status === '所有状态' ? undefined : filters.status,
          sort: filters.sort === '响应时间 (低-高)' ? 'response_time' : 
                filters.sort === '成功率' ? 'success_rate' : 
                filters.sort === '业务评分 (高-低)' ? 'business_score' : 
                filters.sort === '质量评分 (高-低)' ? 'quality_score' : 'last_check',
          page: page,
          limit: 10
        });
        setProxies(result.data || []);
        setTotal(result.total || 0);
      } catch (error) {
        console.error('Failed to fetch proxies:', error);
        setProxies([]);
      } finally {
        setLoading(false);
      }
    };
    fetchProxies();
  }, [filters, page]);

  // 删除代理
  const handleDelete = async (ip: string, port: number) => {
    try {
      await api.deleteProxy(ip, port);
      // 重新获取代理列表
      const result = await api.getProxies({
        page: page,
        limit: 10
      });
      setProxies(result.data || []);
    } catch (error) {
      console.error('Failed to delete proxy:', error);
    }
  };

  // 刷新代理
  const handleRefresh = async () => {
    try {
      await api.refreshProxies();
      // 重新获取数据
      const [statsData, proxiesData, filtersData] = await Promise.all([
        api.getStats(),
        api.getProxies({ page: page, limit: 10 }),
        api.getFilters()
      ]);
      setStats(statsData);
      setProxies(proxiesData.data || []);
      setFilterOptions({
        countries: ['所有国家', ...filtersData.countries],
        proxyTypes: ['所有类型', ...filtersData.proxyTypes],
        mainCountry: filtersData.mainCountry
      });
    } catch (error) {
      console.error('Failed to refresh:', error);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="总代理数" 
          value={stats.totalProxies.toLocaleString()} 
          icon={Layers} 
          trend={`+${stats.activeChange}%`} 
        />
        <StatCard 
          title="活跃代理数" 
          value={stats.activeProxies.toLocaleString()} 
          icon={Activity} 
          trend="正常运行" 
          trendColor="text-neon-cyan bg-cyan-500/10"
          chart={
            <div className="flex items-end gap-1 h-6">
              {[0.4, 0.6, 0.8, 1, 0.9, 0.7].map((h, i) => (
                <div key={i} className="w-1 bg-neon-cyan rounded-t-sm" style={{ height: `${h * 100}%`, opacity: h }} />
              ))}
            </div>
          }
        />
        <StatCard 
          title="地区分布" 
          value={`${stats.countriesCount} 个国家/地区`} 
          icon={Globe} 
          trend={`主要地区: ${filterOptions.mainCountry}`} 
          trendColor="text-slate-400"
          chart={
            <div className="flex gap-1 h-1.5 w-full">
              <div className="bg-blue-500 rounded-full" style={{ width: '40%' }} />
              <div className="bg-indigo-500 rounded-full" style={{ width: '25%' }} />
              <div className="bg-purple-500 rounded-full" style={{ width: '20%' }} />
              <div className="bg-slate-600 rounded-full" style={{ width: '15%' }} />
            </div>
          }
        />
        <StatCard 
          title="平均响应时间" 
          value={`${stats.avgResponseTime}ms`} 
          icon={Zap} 
          trend={`${stats.responseTimeChange}ms`} 
          chart={
            <div className="flex items-end gap-1 h-6">
              {[1, 0.6, 0.8, 0.5, 0.3, 0.2].map((h, i) => (
                <div key={i} className="w-1 bg-amber-400 rounded-t-sm" style={{ height: `${h * 100}%`, opacity: h }} />
              ))}
            </div>
          }
        />
      </div>

      <section className="bg-slate-card border border-slate-800 rounded-xl p-4 shadow-lg">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <CustomSelect 
            label="按国家" 
            options={filterOptions.countries} 
            value={filters.country} 
            onChange={(val) => setFilters(f => ({ ...f, country: val }))} 
          />
          <CustomSelect 
            label="代理类型" 
            options={filterOptions.proxyTypes} 
            value={filters.type} 
            onChange={(val) => setFilters(f => ({ ...f, type: val }))} 
          />
          <CustomSelect 
            label="状态" 
            options={['所有状态', '存活', '失效', '缓慢']} 
            value={filters.status} 
            onChange={(val) => setFilters(f => ({ ...f, status: val }))} 
          />
          <CustomSelect 
            label="排序方式" 
            options={['质量评分 (高-低)', '业务评分 (高-低)', '响应时间 (低-高)', '成功率', '最后检查时间']} 
            value={filters.sort} 
            onChange={(val) => setFilters(f => ({ ...f, sort: val }))} 
          />
          <div className="flex items-end">
            <button className="w-full bg-neon-cyan/10 hover:bg-neon-cyan text-neon-cyan hover:text-deep-slate font-bold py-2 rounded-lg border border-neon-cyan/30 transition-all duration-300">
              应用筛选
            </button>
          </div>
        </div>
      </section>

    <div className="bg-slate-card border border-slate-800 rounded-xl shadow-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-slate-800/50 border-b border-slate-700">
            <tr>
              <th className="px-6 py-4 font-semibold text-slate-400">IP地址</th>
              <th className="px-4 py-4 font-semibold text-slate-400">来源</th>
              <th className="px-4 py-4 font-semibold text-slate-400">位置</th>
              <th className="px-4 py-4 font-semibold text-slate-400">类型</th>
              <th className="px-4 py-4 font-semibold text-slate-400">匿名度</th>
              <th className="px-4 py-4 font-semibold text-slate-400">速度</th>
              <th className="px-4 py-4 font-semibold text-slate-400">成功率</th>
              <th className="px-4 py-4 font-semibold text-slate-400">业务评分</th>
              <th className="px-4 py-4 font-semibold text-slate-400">质量评分</th>
              <th className="px-4 py-4 font-semibold text-slate-400">最后检查</th>
              <th className="px-4 py-4 font-semibold text-slate-400">状态</th>
              <th className="px-6 py-4 font-semibold text-slate-400 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {loading ? (
              <tr>
                <td colSpan={12} className="px-6 py-8 text-center text-slate-500">
                  加载中...
                </td>
              </tr>
            ) : proxies.length === 0 ? (
              <tr>
                <td colSpan={12} className="px-6 py-8 text-center text-slate-500">
                  暂无数据
                </td>
              </tr>
            ) : (
              proxies.map(node => (
                <ProxyRow 
                  key={node.id} 
                  node={node} 
                  onDelete={() => handleDelete(node.ip, node.port)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="bg-slate-800/30 border-t border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="text-xs text-slate-500">显示 <span className="text-slate-300 font-medium">{((page - 1) * 10) + 1}-{Math.min(page * 10, total)}</span> 条，共 <span className="text-slate-300 font-medium">{total.toLocaleString()}</span> 条记录</div>
        <div className="flex items-center gap-2">
          <button 
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg border border-slate-700 transition-colors" 
            disabled={page === 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            <ChevronLeft size={16} />
          </button>
          <button className="w-8 h-8 bg-neon-cyan text-deep-slate font-bold rounded-lg text-xs">{page}</button>
          <button className="w-8 h-8 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition-colors" onClick={() => setPage(p => p + 1)}>
            {page + 1}
          </button>
          <span className="text-slate-600 px-1">...</span>
          <button className="w-8 h-8 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition-colors">
            {Math.ceil(total / 10)}
          </button>
          <button 
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg border border-slate-700 transition-colors"
            onClick={() => setPage(p => p + 1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  </motion.div>
  );
};

const NodeMapView = () => (
  <motion.div 
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="relative h-[calc(100vh-200px)] min-h-[600px] bg-[#0a0f1e] rounded-2xl border border-slate-800 overflow-hidden"
  >
    {/* Stylized Map Background with Grid Overlay */}
    <div className="absolute inset-0">
      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#22d3ee_1px,transparent_1px)] [background-size:40px_40px]" />
      <div className="absolute inset-0 opacity-30">
        <img 
          className="w-full h-full object-cover mix-blend-screen" 
          src="https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=dark%20world%20map%20with%20political%20boundaries%2C%20blue%20oceans%2C%20detailed%20continents%2C%20minimal%20styling%2C%20high%20resolution&image_size=landscape_16_9" 
          alt="World Map"
          referrerPolicy="no-referrer"
        />
      </div>
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#0a0f1e]" />
    </div>

    {/* Connection Lines (Visual Decor) */}
    <svg className="absolute inset-0 w-full h-full opacity-20 pointer-events-none">
      <motion.path
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 3, repeat: Infinity }}
        d="M 25% 35% Q 40% 20% 48% 45%"
        stroke="#22d3ee"
        strokeWidth="1"
        fill="none"
      />
      <motion.path
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 4, repeat: Infinity, delay: 1 }}
        d="M 48% 45% Q 60% 30% 75% 38%"
        stroke="#22d3ee"
        strokeWidth="1"
        fill="none"
      />
      <motion.path
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 5, repeat: Infinity, delay: 2 }}
        d="M 25% 35% Q 50% 60% 75% 38%"
        stroke="#22d3ee"
        strokeWidth="1"
        fill="none"
      />
    </svg>

    {/* Stats Overlay */}
    <div className="absolute top-6 left-6 z-10 flex flex-col gap-4">
      <div className="bg-slate-card/80 backdrop-blur-xl p-5 rounded-xl border border-slate-700 shadow-2xl min-w-[240px]">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
          <Activity size={14} /> 实时节点概况
        </h3>
        <div className="space-y-4">
          <div>
            <p className="text-xs text-slate-500">全球在线节点</p>
            <p className="text-2xl font-bold text-white tracking-tight">1,248,392</p>
            <span className="text-[10px] text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full flex items-center gap-1 w-fit mt-1">
              <Activity size={12} /> +5.2% (过去1h)
            </span>
          </div>
          <div className="h-[1px] bg-slate-700" />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] text-slate-500 uppercase font-bold">平均延迟</p>
              <p className="text-lg font-bold text-neon-cyan">82ms</p>
            </div>
            <div>
              <p className="text-[10px] text-slate-500 uppercase font-bold">今日请求</p>
              <p className="text-lg font-bold text-white">2.4M</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    {/* Interactive Node Points */}
    {[
      { top: '35%', left: '25%', country: '美国 (USA)', status: '状态极佳', proxies: '42,105', latency: '45ms', uptime: '98.2%' },
      { top: '45%', left: '48%', country: '德国 (DEU)', status: '正常', proxies: '12,402', latency: '22ms', uptime: '99.5%' },
      { top: '38%', left: '75%', country: '日本 (JPN)', status: '状态极佳', proxies: '28,912', latency: '12ms', uptime: '99.9%' },
      { top: '65%', left: '32%', country: '巴西 (BRA)', status: '缓慢', proxies: '5,102', latency: '182ms', uptime: '85.4%' },
      { top: '72%', left: '82%', country: '澳大利亚 (AUS)', status: '负载高', proxies: '3,201', latency: '245ms', uptime: '92.1%' },
      { top: '40%', left: '35%', country: '英国 (GBR)', status: '状态极佳', proxies: '8,745', latency: '18ms', uptime: '99.3%' },
      { top: '25%', left: '60%', country: '俄罗斯 (RUS)', status: '正常', proxies: '15,234', latency: '35ms', uptime: '97.8%' },
      { top: '55%', left: '65%', country: '印度 (IND)', status: '缓慢', proxies: '7,890', latency: '120ms', uptime: '90.5%' },
    ].map((point, idx) => (
      <div key={idx} className="absolute group cursor-pointer" style={{ top: point.top, left: point.left }}>
        <div className={cn(
          "w-6 h-6 rounded-full animate-ping absolute -top-1 -left-1",
          point.status === '状态极佳' ? "bg-neon-cyan/20" : point.status === '缓慢' ? "bg-amber-400/20" : "bg-neon-rose/20"
        )} />
        <div className={cn(
          "w-4 h-4 rounded-full shadow-lg border-2 border-white/20",
          point.status === '状态极佳' ? "bg-neon-cyan shadow-neon-cyan/50" : point.status === '缓慢' ? "bg-amber-400" : "bg-neon-rose shadow-neon-rose/50"
        )} />
        
        {/* Tooltip */}
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-56 bg-slate-card rounded-xl shadow-2xl border border-slate-700 p-4 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-bold text-white">{point.country}</h4>
            <span className={cn(
              "px-2 py-0.5 text-[10px] rounded-full font-bold",
              point.status === '状态极佳' ? "bg-emerald-400/10 text-emerald-400" : "bg-amber-400/10 text-amber-400"
            )}>{point.status}</span>
          </div>
          <div className="space-y-2.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">总代理数:</span>
              <span className="text-white font-mono">{point.proxies}</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">平均延迟:</span>
              <span className={cn("font-bold", point.latency.includes('ms') && parseInt(point.latency) < 50 ? "text-neon-cyan" : "text-amber-400")}>{point.latency}</span>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-[9px] font-bold uppercase">
                <span className="text-slate-500">在线率</span>
                <span className="text-emerald-400">{point.uptime}</span>
              </div>
              <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" 
                  style={{ width: point.uptime }} 
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    ))}

    {/* Performance Bottom Bar */}
    <div className="absolute bottom-6 left-6 right-6 z-10">
      <div className="bg-slate-card/90 backdrop-blur-xl p-5 rounded-2xl border border-slate-700 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-widest flex items-center gap-2">
            <Zap size={16} className="text-neon-cyan" /> 性能最佳地区 TOP 5
          </h3>
          <button className="text-[10px] text-neon-cyan hover:underline font-bold uppercase tracking-wider">完整数据报告</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {
            [
              { name: '日本 (JPN)', lat: '12ms', id: '01' },
              { name: '韩国 (KOR)', lat: '15ms', id: '02' },
              { name: '新加坡 (SGP)', lat: '18ms', id: '03' },
              { name: '德国 (DEU)', lat: '22ms', id: '04' },
              { name: '荷兰 (NLD)', lat: '25ms', id: '05' },
            ].map(item => (
              <div key={item.id} className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-neon-cyan/50 transition-all cursor-pointer group">
                <div className="text-lg font-black text-slate-700 group-hover:text-neon-cyan/30">{item.id}</div>
                <div>
                  <p className="text-xs font-bold text-white">{item.name}</p>
                  <p className="text-[10px] text-slate-500">延迟: <span className="text-emerald-400 font-mono">{item.lat}</span></p>
                </div>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  </motion.div>
);

export default function App() {
  // 刷新代理
  const handleRefresh = async () => {
    try {
      await api.refreshProxies();
      // 这里可以添加刷新成功的提示
      console.log('代理刷新成功');
    } catch (error) {
      console.error('Failed to refresh:', error);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-deep-slate border-b border-slate-800 p-6 lg:px-10 flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 z-50">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldCheck className="text-neon-cyan w-8 h-8" />
            ProxyPool <span className="text-neon-cyan">Pro</span> 代理池管理系统
          </h1>
          <p className="text-slate-400 mt-1 text-sm">高性能代理管理与监控面板</p>
        </div>
        
        <nav className="flex items-center gap-2">
          <NavItem icon={FileText} label="代理列表" active={true} onClick={() => {}} />
        </nav>

        <div className="flex items-center gap-3">
          <button className="bg-slate-card hover:bg-slate-700 text-white p-2 rounded-lg border border-slate-700 transition-all relative">
            <Bell size={20} />
            <span className="absolute top-2 right-2 w-2 h-2 bg-neon-rose rounded-full" />
          </button>
          <button 
            onClick={handleRefresh}
            className="bg-slate-card hover:bg-slate-700 text-white px-4 py-2 rounded-lg border border-slate-700 flex items-center gap-2 transition-all"
          >
            <RefreshCw id="refresh-btn" size={16} /> 手动刷新
          </button>
          <button className="bg-rose-500/10 hover:bg-rose-500/20 text-neon-rose px-4 py-2 rounded-lg border border-neon-rose/30 flex items-center gap-2 transition-all">
            <Trash2 size={16} /> 批量删除
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 lg:p-10 max-w-[1600px] mx-auto w-full">
        <DashboardView />
      </main>

      {/* Footer */}
      <footer className="p-6 lg:px-10 flex items-center justify-between text-[11px] text-slate-500 uppercase tracking-widest border-t border-slate-800">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> 系统在线
          </span>
          <span>版本 2.4.0-BUILD.82</span>
        </div>
        <div className="flex items-center gap-4">
          <a href="#" className="hover:text-neon-cyan transition-colors">API 文档</a>
          <a href="#" className="hover:text-neon-cyan transition-colors">服务条款</a>
        </div>
      </footer>
    </div>
  );
}
