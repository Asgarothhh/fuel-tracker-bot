import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Table, message } from 'antd';
import { useParams } from 'react-router-dom';
import api from '../api';
import { PageHeading } from '../components/admin/PageHeading';
import { PaginationBar } from '../components/admin/PaginationBar';
import { OperationDetailModal } from '../components/admin/modals/OperationDetailModal';
import type { OperationRow } from '../components/admin/modals/OperationDetailModal';
import { DisputedOperationModal } from '../components/admin/modals/DisputedOperationModal';

const PAGE_SIZE = 10;

const STATUS_RU: Record<string, string> = {
  confirmed: 'Подтверждена',
  disputed: 'Спорная',
  pending: 'В процессе',
  new: 'Новая',
  rejected: 'Отклонена',
  loaded: 'Загружена',
  loaded_from_api: 'Загружена из API',
  awaiting_user_confirmation: 'Ожидает подтверждения',
  requires_manual: 'Требует ручной обработки',
  rejected_by_other: 'Отклонена',
  import_error: 'Ошибка импорта',
};

function statusLabel(s: string) {
  return STATUS_RU[s] ?? s;
}

function fmtShort(iso?: string | null) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

type Segment = 'new' | 'recent' | 'disputed' | 'api';

const SEGMENT_TAB: Record<Segment, string> = {
  new: 'pending',
  recent: 'recent',
  disputed: 'disputed',
  api: 'api',
};

const SEGMENT_TITLE: Record<Segment, string> = {
  new: 'Новые операции',
  recent: 'Последние операции',
  disputed: 'Спорные операции',
  api: 'Операции из API',
};

const OperationsListPage: React.FC = () => {
  const { segment } = useParams<{ segment: string }>();
  const allowed: Segment[] = ['new', 'recent', 'disputed', 'api'];
  const seg: Segment = segment && allowed.includes(segment as Segment) ? (segment as Segment) : 'recent';

  const [data, setData] = useState<OperationRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<OperationRow | null>(null);
  const [disputed, setDisputed] = useState<OperationRow | null>(null);
  const [importing, setImporting] = useState(false);

  const tabName = SEGMENT_TAB[seg];
  const title = SEGMENT_TITLE[seg];

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/operations/${tabName}`);
      setData(res.data);
      setPage(1);
    } catch {
      message.error('Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, [tabName]);

  useEffect(() => {
    load();
  }, [load]);

  const pageCount = Math.max(1, Math.ceil(data.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), pageCount);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [data.length, page, pageCount]);

  const paged = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return data.slice(start, start + PAGE_SIZE);
  }, [data, safePage]);

  const runApiImport = async () => {
    setImporting(true);
    try {
      const res = await api.post<{ ok?: boolean; new_count?: number; message?: string }>(
        '/operations/import-from-api'
      );
      message.success(res.data.message ?? `Добавлено операций: ${res.data.new_count ?? 0}`);
      load();
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { detail?: unknown } } };
      const d = ax.response?.data?.detail;
      const text = typeof d === 'string' ? d : d != null ? JSON.stringify(d) : 'Ошибка импорта';
      message.error(text);
    } finally {
      setImporting(false);
    }
  };

  const confirmOp = async (id: number) => {
    try {
      await api.post(`/operations/${id}/confirm`);
      message.success('Подтверждено');
      setDetail(null);
      setDisputed(null);
      load();
    } catch {
      message.error('Не удалось подтвердить');
    }
  };

  const columnsNew = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 56,
      className: 'ft-cell--id',
    },
    {
      title: 'Дата и время',
      dataIndex: 'date_time',
      key: 'date_time',
      render: (d: string) => fmtShort(d),
    },
    {
      title: 'Карта',
      key: 'card',
      render: () => '—',
    },
    {
      title: '',
      key: 'a',
      width: 52,
      render: (_: unknown, r: OperationRow) => (
        <button type="button" className="ft-action-btn" onClick={() => setDetail(r)}>
          ···
        </button>
      ),
    },
  ];

  const columnsRecent = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 56, className: 'ft-cell--id' },
    {
      title: 'Дата и время',
      dataIndex: 'date_time',
      key: 'date_time',
      render: (d: string) => fmtShort(d),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => statusLabel(s),
    },
    {
      title: 'Номер авто',
      dataIndex: 'car',
      key: 'car',
      render: (c: string) => c ?? '—',
    },
  ];

  const columnsDisputed = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 56, className: 'ft-cell--id' },
    {
      title: 'Дата и время',
      dataIndex: 'date_time',
      key: 'date_time',
      render: (d: string) => fmtShort(d),
    },
    {
      title: 'Чек',
      dataIndex: 'doc_number',
      key: 'doc_number',
      render: (d: string) => d ?? '—',
    },
    {
      title: '',
      key: 'a',
      width: 52,
      render: (_: unknown, r: OperationRow) => (
        <button type="button" className="ft-action-btn" onClick={() => setDisputed(r)}>
          ···
        </button>
      ),
    },
  ];

  const columns =
    seg === 'recent' ? columnsRecent : seg === 'disputed' ? columnsDisputed : columnsNew;

  return (
    <>
      <PageHeading title={title} lineVariant="step" />

      {seg === 'api' && (
        <div style={{ marginTop: 8, marginBottom: 10 }}>
          <button
            type="button"
            className="ft-btn-pill ft-btn-pill--navy"
            style={{ marginBottom: 0, maxWidth: '100%' }}
            disabled={importing}
            onClick={runApiImport}
          >
            {importing ? 'Импорт…' : 'Импорт из API (как в боте)'}
          </button>
        </div>
      )}

      <div className="ft-table-card">
        <div className="ft-table-scroll">
        <Table<OperationRow>
          className="ft-table"
          columns={columns as never}
          dataSource={paged}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
        </div>
        <PaginationBar page={safePage} pageSize={PAGE_SIZE} total={data.length} onChange={setPage} />
      </div>

      <OperationDetailModal
        open={detail != null && seg !== 'disputed'}
        record={detail}
        title={seg === 'api' ? 'Новая операция из API' : 'Новая операция'}
        onClose={() => setDetail(null)}
        onConfirm={() => detail && confirmOp(detail.id)}
        onDispute={() => message.info('Статус «Спорная» — в разработке')}
        onAssignUser={() => message.info('Назначение пользователя — в разработке')}
      />

      <DisputedOperationModal
        open={disputed != null}
        record={disputed}
        onClose={() => setDisputed(null)}
        onConfirmManual={() => disputed && confirmOp(disputed.id)}
        onAssignUser={() => message.info('Назначение пользователя — в разработке')}
      />
    </>
  );
};

export default OperationsListPage;
