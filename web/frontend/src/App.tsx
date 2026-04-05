import React from 'react';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import { AdminHeader } from './components/admin/AdminHeader';
import { DecorativeFooter } from './components/admin/DecorativeFooter';
import MainMenuPage from './pages/MainMenuPage';
import UsersPage from './pages/UsersPage';
import SchedulePage from './pages/SchedulePage';
import ExportPage from './pages/ExportPage';
import OperationsListPage from './pages/OperationsListPage';

import './styles/fuel-admin.css';

const AppShell: React.FC = () => (
  <div className="ft-app">
    <AdminHeader />
    <div className="ft-app__main">
      <Routes>
        <Route path="/" element={<MainMenuPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route path="/export" element={<ExportPage />} />
        <Route path="/operations" element={<Navigate to="/operations/recent" replace />} />
        <Route path="/operations/:segment" element={<OperationsListPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
    <DecorativeFooter />
  </div>
);

const App: React.FC = () => (
  <ConfigProvider
    locale={ruRU}
    theme={{
      token: {
        colorPrimary: '#d80027',
        borderRadius: 12,
        fontFamily: "'Montserrat', system-ui, sans-serif",
      },
    }}
  >
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
