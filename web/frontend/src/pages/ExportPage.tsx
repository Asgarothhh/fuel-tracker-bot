import React, { useState } from 'react';
import { message } from 'antd';
import { PageHeading } from '../components/admin/PageHeading';
import { ReportReadyModal } from '../components/admin/modals/ReportReadyModal';
import api from '../api';

function parseFilename(cd: string | undefined, fallback: string) {
  if (!cd) return fallback;
  const m = /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i.exec(cd);
  return m ? decodeURIComponent(m[1].replace(/['"]/g, '')) : fallback;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

const ExportPage: React.FC = () => {
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState('');
  const [sizeLabel, setSizeLabel] = useState('');
  const [pendingBlob, setPendingBlob] = useState<Blob | null>(null);

  const generate = async () => {
    setBusy(true);
    try {
      const res = await api.get('/reports/excel', {
        responseType: 'blob',
      });
      const blob = res.data as Blob;
      const fallback = `Full_Fuel_Report_${new Date().toISOString().slice(0, 16).replace(/[-T:]/g, '-')}.xlsx`;
      const name = parseFilename(res.headers['content-disposition'], fallback);
      setFileName(name);
      setSizeLabel(formatSize(blob.size));
      setPendingBlob(blob);
      setReady(true);
      message.success('Отчёт сформирован');
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: Blob } };
      if (err.response?.status === 404) {
        message.warning('В базе нет операций для выгрузки');
      } else {
        message.error('Не удалось сформировать отчёт');
      }
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!pendingBlob) return;
    const url = URL.createObjectURL(pendingBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName.endsWith('.xlsx') ? fileName : `${fileName}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
    setReady(false);
  };

  return (
    <>
      <PageHeading title="Экспорт отчётов" lineVariant="step" />
      <div className="ft-table-card" style={{ padding: 20, textAlign: 'left' }}>
        <p style={{ margin: '0 0 16px', fontSize: '0.9rem', lineHeight: 1.5, color: '#333' }}>
          Полный отчёт в Excel: три листа (по картам, личные средства, спорные), как при выгрузке из
          админ-импорта в боте.
        </p>
        <button
          type="button"
          className="ft-btn-pill ft-btn-pill--navy"
          style={{ marginBottom: 0 }}
          onClick={generate}
          disabled={busy}
        >
          {busy ? 'Формирование…' : 'Сформировать отчёт'}
        </button>
      </div>

      <ReportReadyModal
        open={ready}
        fileName={fileName}
        sizeLabel={sizeLabel}
        onClose={() => setReady(false)}
        onDownload={download}
      />
    </>
  );
};

export default ExportPage;
