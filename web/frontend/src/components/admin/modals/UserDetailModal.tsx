import React from 'react';

export type UserRow = {
  id: number;
  full_name: string;
  telegram_id?: number | null;
  active: boolean;
  cars?: string[];
  role?: string;
};

type Props = {
  open: boolean;
  user: UserRow | null;
  cardLabel?: string;
  onClose: () => void;
  onGenerateCode?: () => void;
  onBlock?: () => void;
};

export const UserDetailModal: React.FC<Props> = ({
  open,
  user,
  cardLabel = '—',
  onClose,
  onGenerateCode,
  onBlock,
}) => {
  if (!open || !user) return null;

  const car = user.cars?.[0] ?? '—';

  return (
    <div className="ft-overlay" role="dialog" aria-modal="true">
      <div className="ft-modal">
        <button type="button" className="ft-modal__close" onClick={onClose} aria-label="Закрыть">
          ×
        </button>
        <div className="ft-modal__head">
          <div className="ft-logo" style={{ width: 48, height: 48, padding: 5 }}>
            <div className="ft-logo__pump">
              <svg width="22" height="28" viewBox="0 0 24 32" fill="none" aria-hidden>
                <path d="M4 8V26H14V8H10V4H8V8H4Z" fill="currentColor" />
              </svg>
            </div>
            <span className="ft-logo__ft">FT</span>
            <div className="ft-logo__check">
              <svg viewBox="0 0 12 12" fill="none">
                <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
          </div>
          <div style={{ minWidth: 0 }}>
            <h3 className="ft-modal__title">{user.full_name}</h3>
            <div
              className="ft-modal__underline"
              style={{ width: 72, clipPath: 'polygon(0 100%, 0 30%, 8px 0, 100% 0, 100% 100%)' }}
            />
          </div>
        </div>

        <div className="ft-modal__row">
          <strong>ID:</strong> {user.id}
        </div>
        <div className="ft-modal__row">
          <strong>TELEGRAM:</strong> id:{user.telegram_id ?? '—'}
        </div>
        <div className="ft-modal__row">
          <strong>Карта:</strong> {cardLabel}
        </div>
        <div className="ft-modal__row">
          <strong>Авто:</strong> {car}
        </div>
        <div className="ft-modal__row">
          <strong>Активен:</strong>{' '}
          {user.active ? (
            <span className="ft-status-check">✓</span>
          ) : (
            <span style={{ color: '#999' }}>нет</span>
          )}
        </div>

        <button type="button" className="ft-btn-pill ft-btn-pill--navy" style={{ marginTop: 16 }} onClick={onGenerateCode}>
          Сгенерировать код
        </button>
        <button type="button" className="ft-btn-pill ft-btn-pill--red" onClick={onBlock}>
          Заблокировать
        </button>

        <div className="ft-modal__footer-art">
          <div className="ft-decor__dots" />
          <div className="ft-decor__blob ft-decor__blob--navy" />
          <div className="ft-decor__blob ft-decor__blob--red" />
        </div>
      </div>
    </div>
  );
};
