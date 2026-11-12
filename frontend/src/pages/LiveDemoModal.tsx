import React, { useState, useEffect } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  X,
  ShieldCheck,
  ShieldAlert,
  Camera,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Sliders,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';
import { Badge } from '../components/common/Badge';

interface LiveDemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface DemoStep {
  number: number;
  title: string;
  simpleExplanation: string;
  statusBadge: { label: string; variant: 'emerald' | 'warning' | 'critical' | 'navy' };
  keyFacts: Array<{ label: string; value: string }>;
  technicalDetails?: {
    hashOrDigest: string;
    algorithm: string;
    securityAction: string;
  };
}

const DEMO_STEPS: DemoStep[] = [
  {
    number: 1,
    title: 'A farmer submits a photograph',
    simpleExplanation:
      'A registered farmer captures a photograph of newly harvested organic cotton in their field in Adilabad, Telangana.',
    statusBadge: { label: 'EVIDENCE CAPTURED', variant: 'navy' },
    keyFacts: [
      { label: 'Farmer', value: 'Ramesh Reddy (Adilabad Co-op)' },
      { label: 'Crop Batch', value: 'Cotton Lot #B-2026-01' },
      { label: 'Submission Source', value: 'Farmer Mobile App' },
    ],
    technicalDetails: {
      hashOrDigest: 'Raw Sony IMX sensor buffer acquisition (1080p)',
      algorithm: 'Direct hardware camera pipeline',
      securityAction: 'Gallery file uploads disallowed; photo captured directly at farm.',
    },
  },
  {
    number: 2,
    title: 'PRAMAN securely protects the photograph',
    simpleExplanation:
      'PRAMAN instantly creates a tamper-proof digital fingerprint and seals the photo with the phone’s secure hardware key.',
    statusBadge: { label: 'CRYPTOGRAPHICALLY SEALED', variant: 'emerald' },
    keyFacts: [
      { label: 'Digital Seal', value: 'Protected against tampering' },
      { label: 'Hardware Key', value: 'Verified authentic device' },
      { label: 'Sequence Counter', value: 'Anti-replay order #1042' },
    ],
    technicalDetails: {
      hashOrDigest: 'SHA-256: 6e73f31af86f9811a24f0664bebfcb20d9f79f90',
      algorithm: 'ECDSA NIST P-256 (secp256r1) asymmetric signature',
      securityAction: 'Private key never leaves phone silicon enclave (TrustZone TEE).',
    },
  },
  {
    number: 3,
    title: 'A previously used photograph is submitted again',
    simpleExplanation:
      'An attempted duplicate submission occurs: another party attempts to reuse the same photo to claim an unauthorized second batch.',
    statusBadge: { label: 'DUPLICATE ATTEMPT', variant: 'warning' },
    keyFacts: [
      { label: 'Second Batch ID', value: 'Batch #B-2026-99 (Flagged)' },
      { label: 'Claimed Quantity', value: '500 KG' },
      { label: 'Detection Pipeline', value: 'Automatic Image Comparison' },
    ],
    technicalDetails: {
      hashOrDigest: 'Attacker slightly cropped and re-saved the JPEG image file',
      algorithm: 'Perceptual Hash (DCT pHash 64-bit)',
      securityAction: 'Evaluates perceptual similarity despite cropping or re-encoding.',
    },
  },
  {
    number: 4,
    title: 'PRAMAN detects suspicious duplication',
    simpleExplanation:
      'PRAMAN’s AI forensics compares visual patterns and detects an 89% duplicate match with previously submitted evidence.',
    statusBadge: { label: 'SUSPICIOUS DUPLICATE DETECTED', variant: 'critical' },
    keyFacts: [
      { label: 'Visual Match', value: '89.4% similarity detected' },
      { label: 'Anomaly Flag', value: 'Reused Harvest Photograph' },
      { label: 'Automatic Action', value: 'Halted automatic ledger approval' },
    ],
    technicalDetails: {
      hashOrDigest: 'Bitwise Hamming Distance: 3 (Threshold ≤ 5 triggers collision)',
      algorithm: 'Perceptual Hashing & Error Level Analysis (ELA)',
      securityAction: 'Identifies fraudulent harvest recycling across different farms.',
    },
  },
  {
    number: 5,
    title: 'Location information is checked',
    simpleExplanation:
      'PRAMAN checks the GPS coordinates against the farmer’s registered land parcel and confirms regional satellite consistency.',
    statusBadge: { label: 'LOCATION CHECKED', variant: 'warning' },
    keyFacts: [
      { label: 'Registered Parcel', value: 'Adilabad Lot Survey #491' },
      { label: 'Location Result', value: 'Requires officer verification' },
      { label: 'Satellite Status', value: 'Vegetation density recorded' },
    ],
    technicalDetails: {
      hashOrDigest: 'Cadastral GIS perimeter polygon distance: 180m',
      algorithm: 'WGS84 ray-casting spatial boundary evaluation',
      securityAction: 'Ensures crops cannot be claimed on ghost or unregistered land.',
    },
  },
  {
    number: 6,
    title: 'The evidence is sent for investigation',
    simpleExplanation:
      'Because suspicious duplication was detected, the case is automatically escalated to the Evidence Verification Centre.',
    statusBadge: { label: 'OPEN INVESTIGATION', variant: 'navy' },
    keyFacts: [
      { label: 'Assigned Desk', value: 'Evidence Verification Centre' },
      { label: 'Priority', value: 'High Attention Required' },
      { label: 'Status', value: 'Waiting for Officer Review' },
    ],
    technicalDetails: {
      hashOrDigest: 'Case ID: ev_f842b109c13 (Decoupled Truth Score: 64.2%)',
      algorithm: 'Truth Engine multi-axis confidence scoring',
      securityAction: 'Veto rule prevents suspicious submissions from bypassing human review.',
    },
  },
  {
    number: 7,
    title: 'An officer requests fresh evidence',
    simpleExplanation:
      'The investigation officer reviews the 6-step checklist and requests fresh, verified photographic evidence from the field.',
    statusBadge: { label: 'CHALLENGE DISPATCHED', variant: 'warning' },
    keyFacts: [
      { label: 'Officer Decision', value: 'Request New Evidence' },
      { label: 'Requirement', value: 'Fresh photo within farm perimeter' },
      { label: 'Time Window', value: '24 Hours to respond' },
    ],
    technicalDetails: {
      hashOrDigest: 'Attributable officer decision: REQUEST_FRESH_EVIDENCE',
      algorithm: 'Cryptographic challenge-response protocol',
      securityAction: 'Protects honest farmers from mistakes while halting systemic fraud.',
    },
  },
  {
    number: 8,
    title: 'Evidence history is preserved',
    simpleExplanation:
      'Every submission, anomaly detection, and officer decision is recorded in an immutable, tamper-evident audit history.',
    statusBadge: { label: 'IMMUTABLE AUDIT TRAIL', variant: 'emerald' },
    keyFacts: [
      { label: 'Audit Log', value: 'Append-only ledger' },
      { label: 'Actor Non-Repudiation', value: 'All decisions signed & attributed' },
      { label: 'Integrity', value: 'Cannot be altered or deleted' },
    ],
    technicalDetails: {
      hashOrDigest: 'Merkle Leaf Commitment: 0x44136fa355b3... ➔ Epoch Root',
      algorithm: 'RFC 6962 binary Merkle tree folding',
      securityAction: 'Ensures accountability for both farmers and inspection officers.',
    },
  },
  {
    number: 9,
    title: 'The final result is displayed',
    simpleExplanation:
      'The farmer submits authentic fresh evidence, the duplicate attempt is rejected, and only genuine produce is certified for consumer QR provenance.',
    statusBadge: { label: 'AUTHENTIC PROVENANCE ISSUED', variant: 'emerald' },
    keyFacts: [
      { label: 'Fraud Attempt', value: 'Blocked & Logged' },
      { label: 'Genuine Produce', value: 'Verified & Certified' },
      { label: 'Consumer QR', value: 'Instant transparency for consumers' },
    ],
    technicalDetails: {
      hashOrDigest: 'Consumer QR Token: prm_3152005f74824af1b6b4715603f8b302',
      algorithm: 'Zero-knowledge coarse privacy + public verification API',
      securityAction: 'Shoppers can scan the QR code in stores to verify trusted provenance.',
    },
  },
];

export const LiveDemoModal: React.FC<LiveDemoModalProps> = ({ isOpen, onClose }) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showTechnical, setShowTechnical] = useState(false);

  useEffect(() => {
    let timer: any = null;
    if (isPlaying && isOpen) {
      timer = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev >= DEMO_STEPS.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 5000);
    }
    return () => clearInterval(timer);
  }, [isPlaying, isOpen]);

  if (!isOpen) return null;

  const currentStep = DEMO_STEPS[currentStepIndex];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(11, 25, 44, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '820px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: '0 24px 48px -12px rgba(16, 24, 40, 0.25)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* MODAL HEADER */}
        <div
          style={{
            padding: '20px 24px',
            backgroundColor: '#142B45',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: '#087F5B',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Sparkles size={18} color="#FFFFFF" />
            </div>
            <div>
              <div style={{ fontSize: '16px', fontWeight: 700 }}>
                SEE HOW PRAMAN WORKS
              </div>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                Guided Demonstration: Agricultural Produce Verification & Fraud Defense
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor: 'rgba(255, 255, 255, 0.15)',
                color: '#CBD5E1',
                letterSpacing: '0.04em',
              }}
            >
              DEMO DATA — SIMULATED WALKTHROUGH
            </span>
            <button
              onClick={onClose}
              style={{ color: '#FFFFFF', background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* STEP PROGRESS TRACKER (1 through 9) */}
        <div style={{ padding: '14px 24px', backgroundColor: '#F8FAFC', borderBottom: '1px solid #E4E7EC', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', overflowX: 'auto' }}>
          {DEMO_STEPS.map((s, idx) => {
            const isCurrent = idx === currentStepIndex;
            const isCompleted = idx < currentStepIndex;
            return (
              <button
                key={s.number}
                onClick={() => {
                  setCurrentStepIndex(idx);
                  setIsPlaying(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 10px',
                  borderRadius: '20px',
                  border: isCurrent ? '1px solid #087F5B' : '1px solid transparent',
                  backgroundColor: isCurrent ? '#EBFBEE' : isCompleted ? '#F1F5F9' : 'transparent',
                  color: isCurrent ? '#087F5B' : isCompleted ? '#334155' : '#94A3B8',
                  fontSize: '11px',
                  fontWeight: isCurrent ? 700 : 500,
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                <span>{s.number}</span>
                {isCompleted && <CheckCircle2 size={12} color="#087F5B" />}
              </button>
            );
          })}
        </div>

        {/* MAIN STEP CONTENT */}
        <div style={{ padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Step Title & Status Badge */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
            <div>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#087F5B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Step {currentStep.number} of {DEMO_STEPS.length}
              </span>
              <h2 style={{ fontSize: '22px', fontWeight: 800, color: '#101828', marginTop: '4px' }}>
                {currentStep.title}
              </h2>
            </div>
            <Badge variant={currentStep.statusBadge.variant} size="md">
              {currentStep.statusBadge.label}
            </Badge>
          </div>

          {/* Simple Explanation (1-2 sentences) */}
          <div
            style={{
              padding: '16px 20px',
              backgroundColor: '#F8FAFC',
              borderRadius: '10px',
              borderLeft: '4px solid #087F5B',
              fontSize: '15px',
              lineHeight: '1.6',
              color: '#101828',
              fontWeight: 500,
            }}
          >
            {currentStep.simpleExplanation}
          </div>

          {/* Key Facts / Results */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            {currentStep.keyFacts.map((fact, i) => (
              <div
                key={i}
                style={{
                  padding: '12px 14px',
                  borderRadius: '8px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E4E7EC',
                }}
              >
                <div style={{ fontSize: '11px', color: '#667085', fontWeight: 600, textTransform: 'uppercase' }}>
                  {fact.label}
                </div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#101828', marginTop: '4px' }}>
                  {fact.value}
                </div>
              </div>
            ))}
          </div>

          {/* Optional Expandable Technical View */}
          {currentStep.technicalDetails && (
            <div style={{ border: '1px solid #E4E7EC', borderRadius: '8px', overflow: 'hidden' }}>
              <button
                onClick={() => setShowTechnical(!showTechnical)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  backgroundColor: '#F8FAFC',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#344054',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sliders size={13} color="#087F5B" />
                  <span>View Technical Details</span>
                </div>
                {showTechnical ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {showTechnical && (
                <div style={{ padding: '14px 16px', backgroundColor: '#FFFFFF', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                  <div>
                    <span style={{ color: '#64748B' }}>Payload Digest / Hash: </span>
                    <code style={{ color: '#101828', fontWeight: 600 }}>{currentStep.technicalDetails.hashOrDigest}</code>
                  </div>
                  <div>
                    <span style={{ color: '#64748B' }}>Algorithm: </span>
                    <strong style={{ color: '#101828' }}>{currentStep.technicalDetails.algorithm}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748B' }}>Security Significance: </span>
                    <span style={{ color: '#101828' }}>{currentStep.technicalDetails.securityAction}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* MODAL CONTROLS FOOTER: Start / Pause / Continue / Restart */}
        <div
          style={{
            padding: '18px 24px',
            backgroundColor: '#F8FAFC',
            borderTop: '1px solid #E4E7EC',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* Playback Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {!isPlaying ? (
              <button
                onClick={() => setIsPlaying(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#087F5B',
                  color: '#FFFFFF',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Play size={14} fill="#FFFFFF" />
                <span>{currentStepIndex === 0 ? 'Start' : 'Continue'}</span>
              </button>
            ) : (
              <button
                onClick={() => setIsPlaying(false)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#D97706',
                  color: '#FFFFFF',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Pause size={14} fill="#FFFFFF" />
                <span>Pause</span>
              </button>
            )}

            <button
              onClick={() => {
                setCurrentStepIndex(0);
                setIsPlaying(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '6px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #D0D5DD',
                color: '#344054',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={13} />
              <span>Restart</span>
            </button>
          </div>

          {/* Step Navigation Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              disabled={currentStepIndex === 0}
              onClick={() => {
                setCurrentStepIndex((prev) => Math.max(0, prev - 1));
                setIsPlaying(false);
              }}
              style={{
                padding: '8px 14px',
                borderRadius: '6px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #D0D5DD',
                color: currentStepIndex === 0 ? '#CBD5E1' : '#344054',
                fontSize: '13px',
                fontWeight: 600,
                cursor: currentStepIndex === 0 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <ArrowLeft size={14} />
              <span>Previous</span>
            </button>

            <button
              disabled={currentStepIndex === DEMO_STEPS.length - 1}
              onClick={() => {
                setCurrentStepIndex((prev) => Math.min(DEMO_STEPS.length - 1, prev + 1));
                setIsPlaying(false);
              }}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                backgroundColor: currentStepIndex === DEMO_STEPS.length - 1 ? '#F1F5F9' : '#142B45',
                color: currentStepIndex === DEMO_STEPS.length - 1 ? '#94A3B8' : '#FFFFFF',
                fontSize: '13px',
                fontWeight: 600,
                border: 'none',
                cursor: currentStepIndex === DEMO_STEPS.length - 1 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>Next</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
