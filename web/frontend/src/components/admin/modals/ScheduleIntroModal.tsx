import React from 'react';

type Props = {
  open: boolean;
  hasSchedule: boolean;
  onClose: () => void;
  onSetNew: () => void;
};

export const ScheduleIntroModal: React.FC<Props> = ({ open, hasSchedule, onClose, onSetNew }) => {
  if (!open) return null;

  return (
    <div className="ft-overlay" role="dialog" aria-modal="true" aria-labelledby="sched-intro-title">
      <div className="ft-modal ft-modal--schedule-intro">
        <button type="button" className="ft-modal__close" onClick={onClose} aria-label="Закрыть">
          ×
        </button>
        <h3 id="sched-intro-title" className="ft-modal__title ft-modal__title--caps">
          ТЕКУЩЕЕ РАСПИСАНИЕ
        </h3>
        <p className="ft-modal__schedule-status">
          {hasSchedule ? 'Расписание задано. Вы можете изменить его в таблице ниже.' : 'Расписание не задано'}
        </p>
        <button type="button" className="ft-btn-pill ft-btn-pill--navy" onClick={onSetNew}>
          Установить новое
        </button>
      </div>
    </div>
  );
};
