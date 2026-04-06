import React, { useEffect, useState } from 'react';
import { message } from 'antd';
import { PageHeading } from '../components/admin/PageHeading';
import { ScheduleIntroModal } from '../components/admin/modals/ScheduleIntroModal';

const STORAGE_KEY = 'fuel-tracker-schedule-v1';
const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

type WeekRow = { id: string; time: string; cells: string[] };

function loadRows(): WeekRow[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as WeekRow[];
  } catch {
    /* ignore */
  }
  return [];
}

const defaultTemplate = (): WeekRow[] => [
  { id: '1', time: '09:00', cells: ['', '', '', '', '', '', ''] },
  { id: '2', time: '12:00', cells: ['', '', '', '', '', '', ''] },
  { id: '3', time: '18:00', cells: ['', '', '', '', '', '', ''] },
];

const SchedulePage: React.FC = () => {
  const [rows, setRows] = useState<WeekRow[]>(loadRows);
  const [showIntro, setShowIntro] = useState(false);

  const hasSchedule = rows.length > 0;

  useEffect(() => {
    if (!hasSchedule) {
      setShowIntro(true);
    }
  }, []);

  useEffect(() => {
    if (rows.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
    }
  }, [rows]);

  const onSetNew = () => {
    if (rows.length === 0) {
      setRows(defaultTemplate());
    }
    setShowIntro(false);
  };

  const updateCell = (rowId: string, dayIndex: number, value: string) => {
    setRows((prev) =>
      prev.map((r) =>
        r.id === rowId ? { ...r, cells: r.cells.map((c, i) => (i === dayIndex ? value : c)) } : r
      )
    );
  };

  const updateTime = (rowId: string, time: string) => {
    setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, time } : r)));
  };

  const addRow = () => {
    setRows((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        time: '00:00',
        cells: ['', '', '', '', '', '', ''],
      },
    ]);
  };

  return (
    <>
      <PageHeading title="Расписание" lineVariant="step" />

      <ScheduleIntroModal
        open={showIntro}
        hasSchedule={hasSchedule}
        onClose={() => setShowIntro(false)}
        onSetNew={onSetNew}
      />

      {!hasSchedule && !showIntro && (
        <div className="ft-table-card" style={{ padding: 22, textAlign: 'center' }}>
          <p style={{ margin: '0 0 14px', fontSize: '0.9rem', color: '#333' }}>
            Расписание ещё не задано.
          </p>
          <button
            type="button"
            className="ft-btn-pill ft-btn-pill--navy"
            style={{ marginBottom: 0 }}
            onClick={() => setShowIntro(true)}
          >
            Открыть окно расписания
          </button>
        </div>
      )}

      {hasSchedule && (
        <div className="ft-table-card ft-schedule-wrap">
          <div className="ft-schedule-toolbar">
            <button type="button" className="ft-schedule-add" onClick={addRow}>
              + Строка
            </button>
            <button
              type="button"
              className="ft-schedule-add ft-schedule-add--ghost"
              onClick={() => message.success('Сохранено локально в браузере')}
            >
              Сохранить
            </button>
          </div>
          <div className="ft-schedule-scroll">
            <table className="ft-schedule-table">
              <thead>
                <tr>
                  <th>Время</th>
                  {DAYS.map((d) => (
                    <th key={d}>{d}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <input
                        className="ft-schedule-time"
                        type="time"
                        value={row.time}
                        onChange={(e) => updateTime(row.id, e.target.value)}
                      />
                    </td>
                    {row.cells.map((cell, di) => (
                      <td key={di}>
                        <input
                          className="ft-schedule-cell"
                          type="text"
                          placeholder="—"
                          value={cell}
                          onChange={(e) => updateCell(row.id, di, e.target.value)}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="ft-schedule-hint">Данные хранятся в браузере.</p>
        </div>
      )}
    </>
  );
};

export default SchedulePage;
