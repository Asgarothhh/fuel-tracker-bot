import React from 'react';

type Props = {
  open: boolean;
  fileName: string;
  sizeLabel: string;
  onClose: () => void;
  onDownload: () => void;
};

export const ReportReadyModal: React.FC<Props> = ({
  open,
  fileName,
  sizeLabel,
  onClose,
  onDownload,
}) => {
  if (!open) return null;

  return (
    <div className="ft-overlay" role="dialog" aria-modal="true" aria-labelledby="report-ready-title">
      <div className="ft-modal">
        <button type="button" className="ft-modal__close" onClick={onClose} aria-label="Закрыть">
          ×
        </button>
        <h3 id="report-ready-title" className="ft-modal__title" style={{ textTransform: 'uppercase', marginBottom: 12 }}>
          ОТЧЕТ СФОРМИРОВАН
        </h3>
        <p className="ft-modal__row" style={{ marginBottom: 20 }}>
          {fileName} ( {sizeLabel} )
        </p>
        <button type="button" className="ft-btn-pill ft-btn-pill--navy" onClick={onDownload}>
          Скачать
        </button>
      </div>
    </div>
  );
};
