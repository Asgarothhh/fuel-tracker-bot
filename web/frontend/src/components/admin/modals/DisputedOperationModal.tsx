import React, { useState } from 'react';
import type { OperationRow } from './OperationDetailModal';

type Props = {
  open: boolean;
  record: OperationRow | null;
  onClose: () => void;
  onConfirmManual?: () => void;
  onAssignUser?: () => void;
};

function fmtDate(iso?: string | null) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('ru-RU');
  } catch {
    return iso;
  }
}

export const DisputedOperationModal: React.FC<Props> = ({
  open,
  record,
  onClose,
  onConfirmManual,
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
        <h3 className="ft-modal__title" style={{ marginBottom: 8 }}>
          Чек {record.doc_number ?? record.id}
        </h3>
        <p className="ft-modal__row" style={{ marginBottom: 18 }}>
          {fmtDate(record.date_time)}
        </p>

        <p className="ft-modal__section-title" style={{ marginTop: 0 }}>
          Подтвердить вручную
        </p>
        <button type="button" className="ft-btn-pill ft-btn-pill--red" onClick={onConfirmManual}>
          Подтвердить
        </button>

        <p className="ft-modal__section-title">Назначить на ...</p>
        <div className="ft-modal__search-wrap">
          <input
            className="ft-modal__search"
            placeholder="Поиск"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <span className="ft-modal__search-icon">🔍</span>
        </div>
        <button type="button" className="ft-btn-pill ft-btn-pill--grey" onClick={onAssignUser}>
          Назначить пользователя
        </button>
      </div>
    </div>
  );
};
