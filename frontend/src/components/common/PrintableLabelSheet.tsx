import React, { useRef } from 'react';
import {
  Printer,
  Download,
  QrCode,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  MapPin,
  Package,
  Layers,
} from 'lucide-react';

export interface PrintableLabelSheetProps {
  batchCode: string;
  cropType: string;
  qrToken: string;
  publicUrl?: string;
  labelSize?: '2x1' | '3x2' | '4x3';
  quantity?: number;
  farmOrigin?: string;
  harvestDate?: string;
  expiryDate?: string;
  sku?: string;
  packageWeight?: string | number;
  packageIdPrefix?: string;
  onClose?: () => void;
}

export const PrintableLabelSheet: React.FC<PrintableLabelSheetProps> = ({
  batchCode,
  cropType,
  qrToken,
  publicUrl,
  labelSize = '3x2',
  quantity = 12,
  farmOrigin = 'Green Valley FPO, Adilabad',
  harvestDate = '2026-10-14',
  expiryDate = '2027-10-14',
  sku = 'SKU-PRM-COTTON-500G',
  packageWeight = '0.5 KG',
  packageIdPrefix = 'PKG',
  onClose,
}) => {
  const printContainerRef = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    window.print();
  };

  const handleExportPNG = () => {
    alert(`Label sheet for SKU ${sku} (${quantity} units) prepared for export.`);
  };

  // Dimensions based on selected sticker size
  const getLabelDimensions = () => {
    switch (labelSize) {
      case '2x1':
        return { width: '220px', minHeight: '120px', fontSize: '10px', qrSize: 52 };
      case '4x3':
        return { width: '340px', minHeight: '210px', fontSize: '12px', qrSize: 84 };
      case '3x2':
      default:
        return { width: '280px', minHeight: '160px', fontSize: '11px', qrSize: 68 };
    }
  };

  const dims = getLabelDimensions();

  // Generate array of package items with unique serialized IDs
  const packages = Array.from({ length: quantity }, (_, i) => {
    const padNum = String(i + 1).padStart(3, '0');
    const pkgId = `${packageIdPrefix}-${batchCode.replace(/[^a-zA-Z0-9]/g, '').slice(-4)}-${padNum}`;
    return {
      index: i + 1,
      pkgId,
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* ACTION BAR (HIDDEN IN PRINT) */}
      <div
        className="no-print"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#F8F9FA',
          padding: '12px 16px',
          borderRadius: '8px',
          border: '1px solid #E5E7EB',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#111827', margin: 0 }}>
            Printable Package QR Sticker Sheet ({quantity} Units)
          </h4>
          <span style={{ fontSize: '12px', color: '#64748B' }}>
            Size: {labelSize} inches • SKU: {sku} • Batch: {batchCode}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={handleExportPNG}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 12px',
              borderRadius: '6px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #D1D5DB',
              color: '#374151',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Download size={14} />
            Export PNG/PDF
          </button>

          <button
            type="button"
            onClick={handlePrint}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              borderRadius: '6px',
              backgroundColor: '#1B4332',
              color: '#FFFFFF',
              fontSize: '12px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 1px 2px rgba(27, 67, 50, 0.2)',
            }}
          >
            <Printer size={14} />
            Print Labels
          </button>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '7px 12px',
                borderRadius: '6px',
                backgroundColor: 'transparent',
                color: '#64748B',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              Done
            </button>
          )}
        </div>
      </div>

      {/* PRINTABLE SHEET CONTAINER */}
      <div
        ref={printContainerRef}
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(auto-fill, minmax(${dims.width}, 1fr))`,
          gap: '12px',
          padding: '16px',
          backgroundColor: '#FFFFFF',
          borderRadius: '8px',
          border: '1px solid #E5E7EB',
          maxHeight: '600px',
          overflowY: 'auto',
        }}
      >
        {packages.map((pkg) => (
          <div
            key={pkg.pkgId}
            style={{
              width: '100%',
              minHeight: dims.minHeight,
              border: '1px dashed #1B4332',
              borderRadius: '6px',
              padding: '10px 12px',
              backgroundColor: '#FFFFFF',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
              position: 'relative',
              breakInside: 'avoid',
            }}
          >
            {/* Header: Seal & Brand */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid #E5E7EB',
                paddingBottom: '4px',
                marginBottom: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={14} color="#1B4332" />
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 800,
                    letterSpacing: '0.04em',
                    color: '#1B4332',
                  }}
                >
                  PRAMAN VERIFIED
                </span>
              </div>
              <span
                style={{
                  fontSize: '9px',
                  fontFamily: 'monospace',
                  color: '#64748B',
                  fontWeight: 600,
                }}
              >
                {pkg.pkgId}
              </span>
            </div>

            {/* Middle: QR & Details */}
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              {/* QR Code Container */}
              <div
                style={{
                  width: `${dims.qrSize}px`,
                  height: `${dims.qrSize}px`,
                  border: '1px solid #1B4332',
                  borderRadius: '4px',
                  backgroundColor: '#FFFFFF',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '2px',
                  flexShrink: 0,
                  overflow: 'hidden',
                }}
              >
                <img
                  src={`/api/v1/platform/retailer/qr-image/${qrToken || 'prm_3152005f74824af1b6b4715603f8b302'}?target=png`}
                  alt="Scannable QR"
                  style={{ width: `${dims.qrSize - 4}px`, height: `${dims.qrSize - 4}px`, objectFit: 'contain' }}
                />
              </div>

              {/* Package Details */}
              <div style={{ flex: 1, minWidth: 0, fontSize: dims.fontSize }}>
                <div style={{ fontWeight: 700, color: '#111827', marginBottom: '2px' }}>
                  {cropType}
                </div>
                <div style={{ color: '#4B5563', fontSize: '10px', marginBottom: '2px' }}>
                  <strong>Batch:</strong> {batchCode}
                </div>
                <div style={{ color: '#4B5563', fontSize: '10px', marginBottom: '2px' }}>
                  <strong>Origin:</strong> {farmOrigin}
                </div>
                <div style={{ color: '#4B5563', fontSize: '10px' }}>
                  <strong>Net Wt:</strong> {packageWeight}
                </div>
              </div>
            </div>

            {/* Footer: Expiry & Cryptographic Guarantee */}
            <div
              style={{
                marginTop: '6px',
                paddingTop: '4px',
                borderTop: '1px solid #F3F4F6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '9px',
                color: '#6B7280',
              }}
            >
              <span>Harvest: {harvestDate}</span>
              <span style={{ fontWeight: 600, color: '#1B4332' }}>Scan to Verify</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
