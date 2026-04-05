import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Table, message } from 'antd';
import api from '../api';
import { PageHeading } from '../components/admin/PageHeading';
import { PaginationBar } from '../components/admin/PaginationBar';
import { UserDetailModal, type UserRow } from '../components/admin/modals/UserDetailModal';

const PAGE_SIZE = 10;

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<UserRow | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/users/');
      setUsers(res.data);
      setPage(1);
    } catch {
      message.error('Не удалось загрузить пользователей');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const pageCount = Math.max(1, Math.ceil(users.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), pageCount);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [users.length, page, pageCount]);

  const paged = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return users.slice(start, start + PAGE_SIZE);
  }, [users, safePage]);

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 52,
      className: 'ft-cell--id',
    },
    {
      title: 'ФИО',
      dataIndex: 'full_name',
      key: 'full_name',
    },
    {
      title: 'Статус',
      dataIndex: 'active',
      key: 'active',
      render: (active: boolean) => (active ? 'Активен' : 'Неактивен'),
    },
    {
      title: '',
      key: 'actions',
      width: 52,
      render: (_: unknown, u: UserRow) => (
        <button type="button" className="ft-action-btn" onClick={() => setSelected(u)}>
          ···
        </button>
      ),
    },
  ];

  return (
    <>
      <PageHeading title="Пользователи" lineVariant="step" />

      <div className="ft-table-card">
        <div className="ft-table-scroll">
        <Table<UserRow>
          className="ft-table"
          columns={columns}
          dataSource={paged}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
        </div>
        <PaginationBar page={safePage} pageSize={PAGE_SIZE} total={users.length} onChange={setPage} />
      </div>

      <UserDetailModal
        open={selected != null}
        user={selected}
        cardLabel="—"
        onClose={() => setSelected(null)}
        onGenerateCode={() => message.info('Генерация кода — в разработке')}
        onBlock={() => message.info('Блокировка — в разработке')}
      />
    </>
  );
};

export default UsersPage;
