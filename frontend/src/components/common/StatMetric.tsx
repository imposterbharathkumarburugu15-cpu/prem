import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatMetricProps {
  label: string;
  value: string | number;
  subValue?: string;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  icon?: LucideIcon;
  variant?: 'default' | 'emerald' | 'navy' | 'warning' | 'critical' | 'info';
}

export const StatMetric: React.FC<StatMetricProps> = ({
  label,
  value,
  subValue,
  trend,
  trendDirection = 'neutral',
  icon: Icon,
  variant = 'default',
}) => {
  const getAccentColor = () => {
    switch (variant) {
      case 'emerald':
        return '#087F5B';
      case 'navy':
        return '#142B45';
      case 'info':
        return '#0284C7';
      case 'warning':
        return '#D97706';
      case 'critical':
        return '#DC2626';
      default:
        return '#344054';
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E4E7EC',
        borderRadius: '8px',
        padding: '16px 20px',
        boxShadow: '0 1px 2px rgba(16, 24, 40, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '13px', fontWeight: 500, color: '#667085' }}>{label}</span>
        {Icon && (
          <div
            style={{
              padding: '6px',
              borderRadius: '6px',
              backgroundColor: '#F8FAFC',
              color: getAccentColor(),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Icon size={16} />
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span
          className="mono-num"
          style={{
            fontSize: '24px',
            fontWeight: 700,
            color: '#101828',
            letterSpacing: '-0.02em',
          }}
        >
          {value}
        </span>
        {subValue && (
          <span style={{ fontSize: '12px', color: '#98A2B3' }}>{subValue}</span>
        )}
      </div>

      {trend && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
          <span
            style={{
              fontWeight: 600,
              color:
                trendDirection === 'up'
                  ? '#087F5B'
                  : trendDirection === 'down'
                  ? '#DC2626'
                  : '#667085',
            }}
          >
            {trend}
          </span>
        </div>
      )}
    </div>
  );
};
