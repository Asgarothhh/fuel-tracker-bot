import React, { useState } from 'react';

export type OperationRow = {
  id: number;
  doc_number?: string | null;
  date_time?: string | null;
  amount?: number;
  fuel_type?: string;
  car?: string;
  user_name?: string;
  status?: string;
};

type Props = {
  open: boolean;
  record: OperationRow | null;
  title?: string;
  onClose: () => void;
  onConfirm?: () => void;
  onDispute?: () => void;
  onAssignUser?: () => void;
};

function fmtDate(iso?: string | null) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export const OperationDetailModal: React.FC<Props> = ({
  open,
  record,
  title = 'Новая операция из API',
  onClose,
  onConfirm,
  onDispute,
  onAssignUser,
}) => {
  const [q, setQ] = useState('');

  if (!open || !record) return null;

  return (
    <div className="ft-overlay" role="dialog" aria-modal="true">
      <div className="ft-modal">
        <button type="button" className="ft-modal__close" onClick={onClose} aria-label="Закрыть">
          ×
        </button>
        <div className="ft-modal__head">
          <div style={{ flexShrink: 0 }}>
            <div className="ft-logo" style={{ width: 48, height: 48, padding: 5 }}>
              <div className="ft-logo__pump" style={{ transform: 'scale(0.85)' }}>
                <svg width="22" height="28" viewBox="0 0 24 32" fill="none" aria-hidden>
                  <path d="M4 8V26H14V8H10V4H8V8H4Z" fill="currentColor" />
                  <rect x="14" y="10" width="6" height="4" rx="1" fill="currentColor" />
                </svg>
              </div>
              <span className="ft-logo__ft">FT</span>
              <div className="ft-logo__check">
                <svg viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
            </div>
          </div>
          <div>
            <h3 className="ft-modal__title">{title}</h3>
            <div className="ft-modal__underline" />
          </div>
        </div>

        <div className="ft-modal__row">
          <strong>ID:</strong> {record.id}
        </div>
        <div className="ft-modal__row">
          <strong>Дата и время:</strong> {fmtDate(record.date_time)}
        </div>
        <div className="ft-modal__row">
          <strong>Карта:</strong> —
        </div>
        <div className="ft-modal__row">
          <strong>АЗС:</strong> —
        </div>
        <div className="ft-modal__row">
          <strong>Чек:</strong> {record.doc_number ?? '—'}
        </div>
        <div className="ft-modal__row">
          <strong>Количество топлива:</strong>{' '}
          {record.amount != null ? `${record.amount} л.` : '—'}
        </div>

        <p className="ft-modal__section-title">Назначить на ...</p>
        <div className="ft-modal__search-wrap">
          <input
            className="ft-modal__search"
            placeholder="Поиск пользователя"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <span className="ft-modal__search-icon">🔍</span>
        </div>

        <button type="button" className="ft-btn-pill ft-btn-pill--grey" onClick={onAssignUser}>
          Назначить пользователя
        </button>
        <button type="button" className="ft-btn-pill ft-btn-pill--red" onClick={onDispute}>
          Спорная
        </button>
        <button type="button" className="ft-btn-pill ft-btn-pill--green" onClick={onConfirm}>
          Подтвердить
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
