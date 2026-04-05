import React from 'react';
import { useNavigate } from 'react-router-dom';

type Props = {
  title: string;
  showBack?: boolean;
  lineVariant?: 'default' | 'step';
};

export const PageHeading: React.FC<Props> = ({ title, showBack = true, lineVariant = 'default' }) => {
  const navigate = useNavigate();

  return (
    <div className="ft-page-head">
      <div className="ft-page-head__title-wrap">
        <h2 className="ft-page-head__title">{title}</h2>
        <div
          className={lineVariant === 'step' ? 'ft-page-head__line ft-page-head__line--step' : 'ft-page-head__line'}
          aria-hidden
        />
      </div>
      {showBack && (
        <button
          type="button"
          className="ft-page-head__back"
          onClick={() => navigate(-1)}
          aria-label="Назад"
        >
          ←
        </button>
      )}
    </div>
  );
};
