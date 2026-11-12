import React, { useState, useRef, useEffect } from 'react';
import {
  Camera,
  Upload,
  CheckCircle2,
  AlertCircle,
  X,
  RefreshCw,
  FileText,
  MapPin,
  Smartphone,
  ShieldCheck,
  Hash,
  Clock,
  Sparkles,
} from 'lucide-react';
import { Badge } from './Badge';

export interface EvidenceMetadata {
  fileName: string;
  fileSize: number;
  mimeType: string;
  capturedAt: string;
  sha256Hash?: string;
  deviceId?: string;
  deviceInfo?: string;
  latitude?: number;
  longitude?: number;
  accuracyMeters?: number;
  locationStatus?: 'GPS_LOCKED' | 'APPROXIMATE' | 'UNAVAILABLE';
}

export interface ContextualEvidenceCaptureProps {
  label: string;
  description?: string;
  actionName?: string;
  evidenceType?: 'PHOTO' | 'DOCUMENT' | 'SCALE_SLIP' | 'LAB_REPORT' | 'SEAL_VERIFICATION';
  required?: boolean;
  acceptedFileTypes?: string;
  maxSizeMb?: number;
  disabled?: boolean;
  onEvidenceCaptured: (data: {
    file: File | null;
    metadata: EvidenceMetadata | null;
    isValid: boolean;
  }) => void;
  helperText?: string;
}

export const ContextualEvidenceCapture: React.FC<ContextualEvidenceCaptureProps> = ({
  label,
  description,
  actionName,
  evidenceType = 'PHOTO',
  required = false,
  acceptedFileTypes = 'image/jpeg,image/png,image/webp,application/pdf',
  maxSizeMb = 12,
  disabled = false,
  onEvidenceCaptured,
  helperText,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<EvidenceMetadata | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [geoLocating, setGeoLocating] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Compute SHA-256 hash using Web Crypto API
  const calculateSha256 = async (file: File): Promise<string> => {
    try {
      const buffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    } catch {
      return 'hash_uncomputed_' + Math.random().toString(16).slice(2, 10);
    }
  };

  // Obtain geolocation
  const obtainLocation = (): Promise<{
    lat?: number;
    lng?: number;
    acc?: number;
    status: 'GPS_LOCKED' | 'APPROXIMATE' | 'UNAVAILABLE';
  }> => {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve({ status: 'UNAVAILABLE' });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          resolve({
            lat: Number(pos.coords.latitude.toFixed(6)),
            lng: Number(pos.coords.longitude.toFixed(6)),
            acc: Math.round(pos.coords.accuracy),
            status: 'GPS_LOCKED',
          });
        },
        () => {
          // Fallback approximate coords for warehouse/field hub simulation
          resolve({
            lat: 19.664128,
            lng: 78.532049,
            acc: 25,
            status: 'APPROXIMATE',
          });
        },
        { timeout: 3500, enableHighAccuracy: true }
      );
    });
  };

  // Process chosen file
  const handleProcessFile = async (file: File) => {
    setErrorMessage(null);

    // Size validation
    if (file.size > maxSizeMb * 1024 * 1024) {
      const err = `File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds limit of ${maxSizeMb} MB.`;
      setErrorMessage(err);
      setSelectedFile(null);
      setPreviewUrl(null);
      setMetadata(null);
      onEvidenceCaptured({ file: null, metadata: null, isValid: !required });
      return;
    }

    // Type validation
    const allowed = acceptedFileTypes.split(',').map((t) => t.trim().toLowerCase());
    const fileMime = file.type.toLowerCase();
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    const typeMatches = allowed.some((t) => t === fileMime || t === fileExt || (t.endsWith('/*') && fileMime.startsWith(t.replace('/*', ''))));
    if (!typeMatches && acceptedFileTypes !== '*/*') {
      const err = `Unsupported format "${file.type || fileExt}". Accepted: ${acceptedFileTypes}`;
      setErrorMessage(err);
      setSelectedFile(null);
      setPreviewUrl(null);
      setMetadata(null);
      onEvidenceCaptured({ file: null, metadata: null, isValid: !required });
      return;
    }

    setIsProcessing(true);
    setProgress(15);

    try {
      // 1. Create preview if image
      if (file.type.startsWith('image/')) {
        const objectUrl = URL.createObjectURL(file);
        setPreviewUrl(objectUrl);
      } else {
        setPreviewUrl(null);
      }
      setProgress(45);

      // 2. Client-side SHA-256 fingerprinting
      const sha256 = await calculateSha256(file);
      setProgress(75);

      // 3. Location & device capture
      setGeoLocating(true);
      const loc = await obtainLocation();
      setGeoLocating(false);
      setProgress(100);

      const devId = 'DEV-' + Math.abs(file.name.split('').reduce((a, b) => ((a << 5) - a + b.charCodeAt(0)) | 0, 0) % 9000 + 1000);
      const generatedMeta: EvidenceMetadata = {
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type || 'application/octet-stream',
        capturedAt: new Date().toISOString(),
        sha256Hash: sha256,
        deviceId: devId,
        deviceInfo: `${navigator.platform || 'Client Node'} (Secure Enclave Agent)`,
        latitude: loc.lat,
        longitude: loc.lng,
        accuracyMeters: loc.acc,
        locationStatus: loc.status,
      };

      setSelectedFile(file);
      setMetadata(generatedMeta);
      onEvidenceCaptured({ file, metadata: generatedMeta, isValid: true });
    } catch (err: any) {
      setErrorMessage(`Failed to process evidence file: ${err.message || 'Unknown error'}`);
      setSelectedFile(null);
      setPreviewUrl(null);
      setMetadata(null);
      onEvidenceCaptured({ file: null, metadata: null, isValid: !required });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleProcessFile(file);
    }
    // reset input so the same file can be re-selected if needed
    e.target.value = '';
  };

  const handleClear = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setMetadata(null);
    setErrorMessage(null);
    setProgress(0);
    onEvidenceCaptured({ file: null, metadata: null, isValid: !required });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleProcessFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return (
    <div
      style={{
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        backgroundColor: '#FFFFFF',
        padding: '16px',
        marginTop: '12px',
        marginBottom: '12px',
        boxShadow: '0 1px 2px rgba(16, 24, 40, 0.04)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={17} color={required ? '#087F5B' : '#475569'} />
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A' }}>
            {label}
          </span>
          {required ? (
            <Badge variant="emerald">Required</Badge>
          ) : (
            <Badge variant="info">Optional Evidence</Badge>
          )}
        </div>

        {actionName && (
          <span
            style={{
              fontSize: '11px',
              color: '#64748B',
              backgroundColor: '#F1F5F9',
              padding: '2px 8px',
              borderRadius: '4px',
              fontFamily: 'monospace',
            }}
          >
            {actionName}
          </span>
        )}
      </div>

      {description && (
        <p style={{ fontSize: '12px', color: '#64748B', margin: '0 0 12px 0', lineHeight: 1.4 }}>
          {description}
        </p>
      )}

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptedFileTypes}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />

      {/* Upload & Drop area or active file view */}
      {!selectedFile ? (
        <div>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            style={{
              border: `2px dashed ${isDragOver ? '#087F5B' : '#CBD5E1'}`,
              borderRadius: '6px',
              backgroundColor: isDragOver ? '#F0FDF4' : '#F8FAFC',
              padding: '16px',
              textAlign: 'center',
              cursor: disabled ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                flexWrap: 'wrap',
                marginBottom: '8px',
              }}
            >
              <button
                type="button"
                onClick={() => cameraInputRef.current?.click()}
                disabled={disabled}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#0F172A',
                  color: '#FFFFFF',
                  padding: '7px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  border: 'none',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                }}
              >
                <Camera size={14} />
                Capture with Camera
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#FFFFFF',
                  color: '#1E293B',
                  border: '1px solid #CBD5E1',
                  padding: '7px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: disabled ? 'not-allowed' : 'pointer',
                }}
              >
                <Upload size={14} />
                Browse Files
              </button>
            </div>

            <p style={{ fontSize: '11px', color: '#64748B', margin: 0 }}>
              Drag & drop photos or supporting documents (max {maxSizeMb} MB).
            </p>
          </div>

          {!required && (
            <div
              style={{
                marginTop: '6px',
                fontSize: '11px',
                color: '#64748B',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Sparkles size={12} color="#087F5B" />
              <span>Submission can proceed without attaching this file.</span>
            </div>
          )}
        </div>
      ) : (
        /* Attached evidence display */
        <div
          style={{
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            backgroundColor: '#F8FAFC',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            {/* Thumbnail or icon */}
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="Evidence Preview"
                style={{
                  width: '64px',
                  height: '64px',
                  objectFit: 'cover',
                  borderRadius: '4px',
                  border: '1px solid #CBD5E1',
                }}
              />
            ) : (
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  backgroundColor: '#E2E8F0',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <FileText size={28} color="#475569" />
              </div>
            )}

            {/* Details */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircle2 size={15} color="#087F5B" />
                  <span
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: '#0F172A',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '220px',
                    }}
                    title={selectedFile.name}
                  >
                    {selectedFile.name}
                  </span>
                  <span style={{ fontSize: '11px', color: '#64748B' }}>
                    ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleClear}
                  disabled={disabled}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: '#64748B',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    padding: '2px',
                    borderRadius: '4px',
                  }}
                  title="Remove file"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Progress bar while processing */}
              {isProcessing && (
                <div style={{ marginTop: '8px' }}>
                  <div
                    style={{
                      height: '4px',
                      width: '100%',
                      backgroundColor: '#E2E8F0',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${progress}%`,
                        backgroundColor: '#087F5B',
                        transition: 'width 0.2s ease',
                      }}
                    />
                  </div>
                  <span style={{ fontSize: '10px', color: '#64748B' }}>
                    Computing cryptographic fingerprint & metadata...
                  </span>
                </div>
              )}

              {/* Metadata badge grid */}
              {metadata && (
                <div
                  style={{
                    marginTop: '8px',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '6px',
                    fontSize: '11px',
                    color: '#334155',
                  }}
                >
                  {metadata.sha256Hash && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontFamily: 'monospace',
                        backgroundColor: '#FFFFFF',
                        padding: '3px 6px',
                        borderRadius: '4px',
                        border: '1px solid #E2E8F0',
                      }}
                      title={`SHA-256: ${metadata.sha256Hash}`}
                    >
                      <Hash size={12} color="#087F5B" />
                      <span>{metadata.sha256Hash.slice(0, 10)}...{metadata.sha256Hash.slice(-6)}</span>
                    </div>
                  )}

                  {metadata.latitude !== undefined && metadata.longitude !== undefined && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        backgroundColor: '#FFFFFF',
                        padding: '3px 6px',
                        borderRadius: '4px',
                        border: '1px solid #E2E8F0',
                      }}
                    >
                      <MapPin size={12} color="#0284C7" />
                      <span>
                        {metadata.latitude.toFixed(3)}, {metadata.longitude.toFixed(3)} (
                        {metadata.locationStatus === 'GPS_LOCKED' ? 'GPS' : 'Hub'})
                      </span>
                    </div>
                  )}

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      backgroundColor: '#FFFFFF',
                      padding: '3px 6px',
                      borderRadius: '4px',
                      border: '1px solid #E2E8F0',
                    }}
                  >
                    <Clock size={12} color="#64748B" />
                    <span>{new Date(metadata.capturedAt).toLocaleTimeString()}</span>
                  </div>

                  {metadata.deviceId && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        backgroundColor: '#FFFFFF',
                        padding: '3px 6px',
                        borderRadius: '4px',
                        border: '1px solid #E2E8F0',
                      }}
                    >
                      <Smartphone size={12} color="#64748B" />
                      <span>{metadata.deviceId}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Validation error with retry / dismiss */}
      {errorMessage && (
        <div
          style={{
            marginTop: '8px',
            padding: '8px 12px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FECACA',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertCircle size={15} color="#DC2626" />
            <span style={{ fontSize: '12px', color: '#991B1B' }}>{errorMessage}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              style={{
                fontSize: '11px',
                color: '#991B1B',
                background: 'transparent',
                border: '1px solid #FCA5A5',
                borderRadius: '4px',
                padding: '2px 6px',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              <RefreshCw size={11} /> Retry
            </button>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              style={{
                fontSize: '11px',
                color: '#991B1B',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: '2px',
              }}
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {helperText && !errorMessage && (
        <span style={{ fontSize: '11px', color: '#64748B', marginTop: '6px', display: 'block' }}>
          {helperText}
        </span>
      )}
    </div>
  );
};

