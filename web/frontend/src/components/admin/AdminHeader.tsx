import React from 'react';
import { LogoBadge } from './LogoBadge';

export const AdminHeader: React.FC = () => (
  <header className="ft-header">
    <LogoBadge />
    <div className="ft-header__titles">
      <h1 className="ft-header__title">FUEL TRACKER</h1>
      <p className="ft-header__subtitle">ПАНЕЛЬ АДМИНИСТРАТОРА</p>
    </div>
  </header>
);
