import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeading } from '../components/admin/PageHeading';
import {
  IconUsers,
  IconCalendar,
  IconClock,
  IconWarning,
  IconInfo,
  IconChart,
} from '../components/admin/MenuIcons';

type NavCardProps = {
  label: string;
  icon: React.ReactNode;
  to: string;
};

const MenuNavCard: React.FC<NavCardProps> = ({ label, icon, to }) => {
  const navigate = useNavigate();
  return (
    <div className="ft-menu-card-cell">
      <div className="ft-menu-card">
        <button type="button" className="ft-menu-card__body" onClick={() => navigate(to)}>
          <span className="ft-menu-card__label">{label}</span>
          <div className="ft-menu-card__icon">{icon}</div>
        </button>
        <button
          type="button"
          className="ft-menu-card__details-hit"
          onClick={() => navigate(to)}
          aria-label={`Подробнее: ${label}`}
        >
          <span className="ft-menu-card__more">ПОДРОБНЕЕ →</span>
        </button>
      </div>
    </div>
  );
};

const MainMenuPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <>
      <PageHeading title="Главное меню" showBack={false} />
      <div className="ft-menu-shell">
        <div className="ft-menu-grid">
          <MenuNavCard label="ПОЛЬЗОВАТЕЛИ" to="/users" icon={<IconUsers />} />
          <MenuNavCard label="РАСПИСАНИЕ" to="/schedule" icon={<IconCalendar />} />
          <MenuNavCard label="ПОСЛЕДНИЕ ОПЕРАЦИИ" to="/operations/recent" icon={<IconClock />} />
          <MenuNavCard label="СПОРНЫЕ ОПЕРАЦИИ" to="/operations/disputed" icon={<IconWarning />} />
          <MenuNavCard label="ОПЕРАЦИИ ИЗ API" to="/operations/api" icon={<IconInfo />} />
          <div className="ft-menu-card-cell">
            <div className="ft-menu-card ft-menu-card--export">
              <button type="button" className="ft-menu-card__body" onClick={() => navigate('/export')}>
                <span className="ft-menu-card__label">ЭКСПОРТ В EXCEL</span>
                <div className="ft-menu-card__icon">
                  <IconChart />
                </div>
              </button>
              <span className="ft-menu-card__report" aria-hidden>
                ОТЧЁТ →
              </span>
              <button
                type="button"
                className="ft-menu-card__details-hit ft-menu-card__details-hit--export"
                onClick={() => navigate('/export')}
                aria-label="Подробнее: экспорт"
              >
                <span className="ft-menu-card__more">ПОДРОБНЕЕ →</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default MainMenuPage;
