import { ReactNode } from 'react';
import { Activity, Database, LayoutDashboard, ListChecks, Map, RadioTower, ShieldAlert, ShieldCheck } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '../../lib/utils';

const NAV_ITEMS = [
  { to: '/overview', label: '安全总览', icon: LayoutDashboard },
  { to: '/proxies', label: '代理资产', icon: Database },
  { to: '/batches', label: '检测批次', icon: ListChecks },
  { to: '/events', label: '安全事件', icon: ShieldAlert },
  { to: '/honeypot', label: '蜜罐目标', icon: RadioTower },
  { to: '/map', label: '全球地图', icon: Map },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-5">
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-2 text-blue-700">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="text-base font-semibold tracking-tight">ProxyTester</div>
            <div className="text-xs text-slate-500">代理安全研究平台</div>
          </div>
        </div>
        <nav className="p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'mb-1 flex items-center gap-3 rounded-md border px-3 py-2 text-sm font-medium transition duration-200',
                  isActive
                    ? 'border-blue-100 bg-blue-50 text-blue-700 shadow-[0_10px_24px_rgba(37,99,235,0.08)]'
                    : 'border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-950',
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">代理安全研究工作台</h1>
              <p className="text-sm text-slate-500">统一查看代理资产、检测批次、安全事件、蜜罐基准与全球分布特征。</p>
            </div>
            <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600">
              <Activity className="h-4 w-4 text-blue-600" />
              Security Console
            </div>
          </div>
        </header>
        <main className="px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
