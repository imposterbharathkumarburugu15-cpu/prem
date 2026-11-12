import React from 'react';

interface CardProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  noPadding?: boolean;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  badge,
  actions,
  children,
  className = '',
  style = {},
  noPadding = false,
}) => {
  return (
    <div
      className={`card ${className}`}
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E4E7EC',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(16, 24, 40, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
        ...style,
      }}
    >
      {(title || subtitle || badge || actions) && (
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #F2F4F7',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {typeof title === 'string' ? (
                <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#101828' }}>{title}</h3>
              ) : (
                title
              )}
              {badge}
            </div>
            {subtitle && (
              <p style={{ fontSize: '12px', color: '#667085', margin: 0 }}>{subtitle}</p>
            )}
          </div>
          {actions && <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>{actions}</div>}
        </div>
      )}
      <div style={{ padding: noPadding ? '0' : '20px', flex: 1 }}>{children}</div>
    </div>
  );
};
