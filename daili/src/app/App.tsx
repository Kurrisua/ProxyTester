import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './layout/AppShell';
import { ProxyListPage } from '../features/proxies/pages/ProxyListPage';
import { ProxyDetailPage } from '../features/proxies/pages/ProxyDetailPage';
import { SecurityOverviewPage } from '../features/overview/pages/SecurityOverviewPage';
import { SecurityBatchesPage } from '../features/security/pages/SecurityBatchesPage';
import { SecurityEventsPage } from '../features/security/pages/SecurityEventsPage';
import { SecurityEventDetailPage } from '../features/security/pages/SecurityEventDetailPage';
import { HoneypotTargetsPage } from '../features/security/pages/HoneypotTargetsPage';
import { WorldMapPage } from '../features/map/pages/WorldMapPage';

export function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<SecurityOverviewPage />} />
          <Route path="/proxies" element={<ProxyListPage />} />
          <Route path="/proxies/:ip/:port" element={<ProxyDetailPage />} />
          <Route path="/batches" element={<SecurityBatchesPage />} />
          <Route path="/events" element={<SecurityEventsPage />} />
          <Route path="/events/:eventId" element={<SecurityEventDetailPage />} />
          <Route path="/honeypot" element={<HoneypotTargetsPage />} />
          <Route path="/map" element={<WorldMapPage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
