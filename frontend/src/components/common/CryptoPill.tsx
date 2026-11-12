import React, { useState } from 'react';
import { Copy, Check, ShieldCheck } from 'lucide-react';

interface CryptoPillProps {
  label?: string;
  hash: string;
  truncateChars?: number;
  showIcon?: boolean;
}

export const CryptoPill: React.FC<CryptoPillProps> = ({
  label,
  hash,
  truncateChars = 8,
  showIcon = true,
}) => {
  const [copied, setCopied] = useState(false);

  const displayHash =
    hash.length > truncateChars * 2 + 3
      ? `${hash.slice(0, truncateChars)}...${hash.slice(-truncateChars)}`
      : hash;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      onClick={handleCopy}
      title={`Click to copy: ${hash}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        backgroundColor: '#F8FAFC',
        border: '1px solid #E4E7EC',
        borderRadius: '4px',
        padding: '2px 8px',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: '#344054',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        userSelect: 'none',
      }}
    >
      {showIcon && <ShieldCheck size={12} color="#142B45" />}
      {label && <span style={{ color: '#667085', fontWeight: 600 }}>{label}:</span>}
      <span style={{ color: '#101828' }}>{displayHash}</span>
      <span style={{ color: copied ? '#087F5B' : '#98A2B3', display: 'flex' }}>
        {copied ? <Check size={12} /> : <Copy size={11} />}
      </span>
    </div>
  );
};
