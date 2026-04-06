import React from 'react';

const PumpIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} width="22" height="28" viewBox="0 0 24 32" fill="none" aria-hidden>
    <path
      d="M4 8V26H14V8H10V4H8V8H4Z"
      fill="currentColor"
    />
    <rect x="14" y="10" width="6" height="4" rx="1" fill="currentColor" />
    <path d="M18 14V22L22 24V12L18 14Z" fill="currentColor" />
  </svg>
);

export const LogoBadge: React.FC = () => (
  <div className="ft-logo" aria-hidden>
    <div className="ft-logo__pump">
      <PumpIcon />
    </div>
    <span className="ft-logo__ft">FT</span>
    <div className="ft-logo__check">
      <svg viewBox="0 0 12 12" fill="none">
        <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  </div>
);
