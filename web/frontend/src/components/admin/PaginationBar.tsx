import React, { useMemo } from 'react';

type Props = {
  page: number;
  pageSize: number;
  total: number;
  onChange: (p: number) => void;
};

/** Строит список страниц с многоточием так, чтобы текущая страница всегда была видна. */
function buildPageItems(current: number, pageCount: number): (number | 'ellipsis')[] {
  if (pageCount <= 1) return [1];
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, i) => i + 1);
  }

  const set = new Set<number>();
  set.add(1);
  set.add(pageCount);
  for (let p = current - 1; p <= current + 1; p++) {
    if (p >= 1 && p <= pageCount) set.add(p);
  }

  const sorted = [...set].sort((a, b) => a - b);
  const out: (number | 'ellipsis')[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      out.push('ellipsis');
    }
    out.push(sorted[i]);
  }
  return out;
}

export const PaginationBar: React.FC<Props> = ({ page, pageSize, total, onChange }) => {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), pageCount);
  const canPrev = safePage > 1;
  const canNext = safePage < pageCount;

  const items = useMemo(() => buildPageItems(safePage, pageCount), [safePage, pageCount]);

  return (
    <nav className="ft-pager" aria-label="Страницы">
      <button
        type="button"
        className="ft-pager__arrow ft-pager__arrow--prev"
        disabled={!canPrev}
        onClick={() => onChange(safePage - 1)}
        aria-label="Предыдущая страница"
      >
        ‹
      </button>
      {items.map((item, i) =>
        item === 'ellipsis' ? (
          <span key={`e-${i}`} className="ft-pager__dots">
            ···
          </span>
        ) : (
          <button
            key={item}
            type="button"
            className={`ft-pager__num${item === safePage ? ' ft-pager__num--active' : ''}`}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        )
      )}
      <button
        type="button"
        className="ft-pager__arrow ft-pager__arrow--next"
        disabled={!canNext}
        onClick={() => onChange(safePage + 1)}
        aria-label="Следующая страница"
      >
        ›
      </button>
    </nav>
  );
};
