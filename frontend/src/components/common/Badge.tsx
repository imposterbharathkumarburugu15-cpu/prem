import React from 'react';

export type BadgeVariant = 'emerald' | 'navy' | 'warning' | 'critical' | 'info' | 'neutral';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  icon,
  className = '',
}) => {
  const getColors = () => {
    switch (variant) {
      case 'emerald':
        return {
          bg: '#EBFBEE',
          color: '#087F5B',
          border: '#B2F2BB',
        };
      case 'navy':
        return {
          bg: '#F0F6FC',
          color: '#142B45',
          border: '#D0E2FF',
        };
      case 'warning':
        return {
          bg: '#FFFBEB',
          color: '#B45309',
          border: '#FDE68A',
        };
      case 'critical':
        return {
          bg: '#FEF2F2',
          color: '#DC2626',
          border: '#FECACA',
        };
      case 'info':
        return {
          bg: '#F0F9FF',
          color: '#0284C7',
          border: '#BAE6FD',
        };
      case 'neutral':
      default:
        return {
          bg: '#F1F5F9',
          color: '#475467',
          border: '#E4E7EC',
        };
    }
  };

  const styleColors = getColors();

  return (
    <span
      className={`badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: size === 'sm' ? '1px 6px' : '3px 8px',
        fontSize: size === 'sm' ? '11px' : '12px',
        fontWeight: 500,
        borderRadius: '4px',
        backgroundColor: styleColors.bg,
        color: styleColors.color,
        border: `1px solid ${styleColors.border}`,
        lineHeight: 1.3,
        letterSpacing: '0.01em',
      }}
    >
      {icon && <span style={{ display: 'inline-flex', alignItems: 'center' }}>{icon}</span>}
      {children}
    </span>
  );
};
