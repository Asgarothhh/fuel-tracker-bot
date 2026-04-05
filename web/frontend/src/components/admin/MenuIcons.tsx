import React from 'react';

const gradId = (id: string) => `url(#${id})`;

export const IconUsers: React.FC = () => (
  <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden>
    <defs>
      <linearGradient id="g-users" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ff6b8a" />
        <stop offset="100%" stopColor="#8a1a38" />
      </linearGradient>
    </defs>
    <ellipse cx="26" cy="42" rx="14" ry="16" fill="#f4a0b4" transform="rotate(-8 26 42)" />
    <circle cx="44" cy="28" r="12" fill={gradId('g-users')} />
    <rect x="34" y="38" width="22" height="24" rx="11" fill={gradId('g-users')} />
  </svg>
);

export const IconCalendar: React.FC = () => (
  <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden>
    <defs>
      <linearGradient id="g-cal" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#e94e77" />
        <stop offset="100%" stopColor="#5c0f28" />
      </linearGradient>
    </defs>
    <rect x="14" y="22" width="40" height="34" rx="6" fill="#f06292" transform="rotate(-6 34 39)" />
    <rect x="20" y="16" width="44" height="40" rx="8" fill="url(#g-cal)" />
    <rect x="24" y="24" width="36" height="4" rx="1" fill="#fff" opacity="0.9" />
    <circle cx="28" cy="36" r="2.5" fill="#fff" />
    <circle cx="36" cy="36" r="2.5" fill="#fff" />
    <circle cx="44" cy="36" r="2.5" fill="#fff" />
    <circle cx="28" cy="44" r="2.5" fill="#fff" />
    <circle cx="36" cy="44" r="2.5" fill="#fff" />
    <circle cx="44" cy="44" r="2.5" fill="#fff" />
    <rect x="30" y="14" width="4" height="10" rx="2" fill="#fff" opacity="0.85" />
    <rect x="42" y="14" width="4" height="10" rx="2" fill="#fff" opacity="0.85" />
  </svg>
);

export const IconClock: React.FC = () => (
  <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden>
    <defs>
      <linearGradient id="g-clock" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ff7a9c" />
        <stop offset="100%" stopColor="#9b1538" />
      </linearGradient>
    </defs>
    <circle cx="36" cy="38" r="22" fill="url(#g-clock)" />
    <circle cx="36" cy="38" r="18" fill="#2e3159" />
    <path d="M36 38V24" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
    <path d="M36 38H46" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="36" cy="38" r="3" fill="#fff" />
  </svg>
);

export const IconWarning: React.FC = () => (
  <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden>
    <defs>
      <linearGradient id="g-warn" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ff5c7a" />
        <stop offset="100%" stopColor="#b01030" />
      </linearGradient>
    </defs>
    <path d="M36 14L58 52H14L36 14Z" fill="url(#g-warn)" />
    <rect x="33" y="28" width="6" height="14" rx="2" fill="#fff" />
    <circle cx="36" cy="48" r="3" fill="#fff" />
  </svg>
);

export const IconInfo: React.FC = () => (
  <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden>
    <defs>
      <linearGradient id="g-info" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ff6b90" />
        <stop offset="100%" stopColor="#7c1234" />
      </linearGradient>
    </defs>
    <rect x="18" y="18" width="36" height="36" rx="10" fill="url(#g-info)" />
    <rect x="32" y="26" width="8" height="22" rx="3" fill="#fff" />
    <circle cx="36" cy="22" r="3" fill="#fff" />
  </svg>
);

export const IconChart: React.FC = () => (
  <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden>
    <defs>
      <linearGradient id="g-chart" x1="0%" y1="100%" x2="0%" y2="0%">
        <stop offset="0%" stopColor="#c41e3a" />
        <stop offset="100%" stopColor="#ff8fa8" />
      </linearGradient>
    </defs>
    <rect x="16" y="44" width="12" height="18" rx="3" fill="url(#g-chart)" />
    <rect x="30" y="32" width="12" height="30" rx="3" fill="url(#g-chart)" />
    <rect x="44" y="24" width="12" height="38" rx="3" fill="url(#g-chart)" />
  </svg>
);
