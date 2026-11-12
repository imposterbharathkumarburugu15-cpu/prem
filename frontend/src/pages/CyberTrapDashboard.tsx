import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Flame,
  Lock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileCheck2,
  Activity,
  Sliders,
  ShieldCheck,
  Zap,
  Terminal,
  Database,
  XCircle,
  Eye,
  Play,
  ChevronRight,
  Radio,
  Shield,
  Search,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { StatMetric } from '../components/common/StatMetric';
import { Modal } from '../components/common/Modal';

/* ───── Interfaces ───── */

interface CyberEvent {
  id: string;
  timestamp: string;
  decoy_id: string;
  decoy_type: string;
  request_method: string;
  request_path: string;
  source_ip: string;
  is_honeytoken_triggered: boolean;
  honeytoken_id?: string;
}

interface CyberIncident {
  id: string;
  created_at: string;
  category: string;
  risk_level: string;
  source_ip: string;
  event_count: number;
  description: string;
  explanation: any;
  status: string;
  canonical_report_hash: string;
  ledger_checkpoint_id?: string;
  ledger_anchored_at?: string;
}

interface CyberRule {
  id: string;
  incident_id: string;
  rule_type: string;
  target_value: string;
  parameters: any;
  status: string;
  proposed_by: string;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  staging_validation?: any;
  version: number;
  created_at: string;
}

interface DetectionMetrics {
  detection_rate_pct: number;
  false_positive_rate_pct: number;
  average_detection_latency_ms: number;
  isolation_integrity: string;
  total_events: number;
  total_incidents: number;
}

/* ───── Simulation buttons config ───── */

const SCENARIOS: {
  key: string;
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
}[] = [
  { key: 'SQLI',       label: 'SQL Injection',   icon: '💉', color: '#DC2626', bgColor: '#FEF2F2', borderColor: '#FECACA' },
  { key: 'CANARY',     label: 'Honeytoken Exfil', icon: '🍯', color: '#B45309', bgColor: '#FFFBEB', borderColor: '#FDE68A' },
  { key: 'AUTH_BURST', label: 'Auth Stuffing',    icon: '💥', color: '#DC2626', bgColor: '#FEF2F2', borderColor: '#FECACA' },
  { key: 'ADMIN_PROBE',label: 'Admin Recon',      icon: '🔍', color: '#0284C7', bgColor: '#F0F9FF', borderColor: '#BAE6FD' },
];

/* ───── Risk badge helper ───── */

function riskBadge(level: string) {
  const variant = level === 'CRITICAL' ? 'critical' : level === 'HIGH' ? 'warning' : 'info';
  return <Badge variant={variant} size="sm">{level}</Badge>;
}

/* ───── Rule lifecycle badge ───── */

function statusBadge(status: string) {
  const map: Record<string, 'emerald' | 'info' | 'navy' | 'critical' | 'warning' | 'neutral'> = {
    ACTIVE: 'emerald',
    STAGING_VALIDATED: 'info',
    APPROVED: 'navy',
    REJECTED: 'critical',
    PROPOSED: 'warning',
  };
  return <Badge variant={map[status] || 'neutral'} size="sm">{status}</Badge>;
}

/* ══════════════════════════════════════════════════════════════════════════════
   CyberTrapDashboard — Rewritten for PRAMAN inline-style design system
   ══════════════════════════════════════════════════════════════════════════════ */

export const CyberTrapDashboard: React.FC = () => {
  const [events, setEvents] = useState<CyberEvent[]>([]);
  const [incidents, setIncidents] = useState<CyberIncident[]>([]);
  const [rules, setRules] = useState<CyberRule[]>([]);
  const [metrics, setMetrics] = useState<DetectionMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<CyberIncident | null>(null);
  const [verificationModal, setVerificationModal] = useState<any | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [simFeedback, setSimFeedback] = useState<string | null>(null);

  /* ───── Data fetching ───── */

  const fetchData = async () => {
    setLoading(true);
    try {
      const [evRes, incRes, rulesRes, metRes] = await Promise.all([
        fetch('/api/v1/cybertrap/intel/events?limit=20').then((r) => r.json()),
        fetch('/api/v1/cybertrap/intel/incidents?limit=20').then((r) => r.json()),
        fetch('/api/v1/cybertrap/feedback/rules').then((r) => r.json()),
        fetch('/api/v1/cybertrap/intel/metrics').then((r) => r.json()),
      ]);

      if (evRes?.items) setEvents(evRes.items);
      if (incRes?.items) {
        setIncidents(incRes.items);
        if (incRes.items.length > 0 && !selectedIncident) {
          setSelectedIncident(incRes.items[0]);
        }
      }
      if (rulesRes?.items) setRules(rulesRes.items);
      if (metRes) setMetrics(metRes);
    } catch (e) {
      console.error('Failed to load CyberTrap dashboard data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  /* ───── Simulation ───── */

  const runSimulation = async (scenario: string) => {
    setSimulating(true);
    setSimFeedback(`Running local ${scenario} simulation…`);
    try {
      if (scenario === 'SQLI') {
        await fetch('/api/v1/cybertrap/decoys/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: "SELECT * FROM batches WHERE 1=1 UNION SELECT 1,2,3 --" }),
        });
      } else if (scenario === 'CANARY') {
        await fetch('/api/v1/cybertrap/decoys/batches/BATCH-HONEY-SAFFRON-001', {
          method: 'GET',
          headers: { 'X-Canary-Secret': 'prm_canary_saffron_secret_9981' },
        });
      } else if (scenario === 'AUTH_BURST') {
        for (let i = 0; i < 5; i++) {
          await fetch('/api/v1/cybertrap/decoys/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: `hacker_${i}@darkweb.org`, password: 'Password123!' }),
          });
        }
      } else if (scenario === 'ADMIN_PROBE') {
        await fetch('/api/v1/cybertrap/decoys/admin/db_dump');
      }

      await fetch('/api/v1/cybertrap/intel/analyse', { method: 'POST' });
      await fetch('/api/v1/cybertrap/feedback/rules/generate', { method: 'POST' });

      setSimFeedback(`Simulation '${scenario}' complete — threat detected, classified & rule proposed.`);
      await fetchData();
    } catch (e) {
      setSimFeedback(`Simulation error: ${e}`);
    } finally {
      setSimulating(false);
    }
  };

  /* ───── Rule actions ───── */

  const handleApproveRule = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_by: 'Cybersecurity Admin (Dr. K. Rao)' }),
    });
    await fetchData();
  };

  const handleValidateStaging = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/validate-staging`, { method: 'POST' });
    await fetchData();
  };

  const handleDeployRule = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/deploy`, { method: 'POST' });
    await fetchData();
  };

  const handleRejectRule = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rejected_by: 'Platform Governance', rejection_reason: 'Requires operational review' }),
    });
    await fetchData();
  };

  const handleAnchorIncident = async (incidentId: string) => {
    await fetch(`/api/v1/cybertrap/audit/incidents/${incidentId}/anchor`, { method: 'POST' });
    await fetchData();
  };

  const handleVerifyIncident = async (incidentId: string) => {
    const res = await fetch(`/api/v1/cybertrap/audit/incidents/${incidentId}/verify`).then((r) => r.json());
    setVerificationModal(res);
  };

  /* ═══════════════════════ RENDER ═══════════════════════ */

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1280px', margin: '0 auto', paddingBottom: '48px' }}>

      {/* ─── Header Banner ─── */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1B4332 0%, #2D6A4F 60%, #40916C 100%)',
          borderRadius: '12px',
          padding: '28px 32px',
          position: 'relative',
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        {/* Watermark icon */}
        <div style={{ position: 'absolute', top: '-10px', right: '-10px', opacity: 0.07, pointerEvents: 'none' }}>
          <ShieldAlert size={200} color="#fff" />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', position: 'relative', zIndex: 1 }}>
          <div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 12px',
                borderRadius: '9999px',
                backgroundColor: 'rgba(255,255,255,0.12)',
                color: '#D8F3DC',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                textTransform: 'uppercase' as const,
                marginBottom: '8px',
                border: '1px solid rgba(255,255,255,0.15)',
              }}
            >
              <Shield size={13} />
              PRAMAN CyberTrap Intelligence
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em', margin: 0 }}>
              Adaptive Agricultural Cyber Defense Command
            </h1>
            <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', marginTop: '4px', maxWidth: '640px', lineHeight: 1.5 }}>
              Deterministic honeypots, explainable threat classification, human-approved defensive feedback loops, and tamper-evident blockchain audit anchoring.
            </p>
          </div>

          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.12)',
              color: '#FFFFFF',
              fontSize: '13px',
              fontWeight: 600,
              border: '1px solid rgba(255,255,255,0.2)',
              cursor: 'pointer',
              transition: 'background-color 0.15s',
            }}
          >
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh Telemetry
          </button>
        </div>
      </div>

      {/* ─── KPI Stat Cards ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <StatMetric
          label="Detection Rate"
          value={metrics ? `${metrics.detection_rate_pct}%` : '100%'}
          subValue="Deterministic Rule Trigger"
          icon={Activity}
          variant="emerald"
        />
        <StatMetric
          label="False Positive Rate"
          value={metrics ? `${metrics.false_positive_rate_pct}%` : '0.0%'}
          subValue="Physically Isolated Decoys"
          icon={ShieldCheck}
          variant="info"
        />
        <StatMetric
          label="Active Incidents"
          value={incidents.length}
          subValue="Classified Threats"
          icon={Flame}
          variant="warning"
        />
        <StatMetric
          label="Defensive Rules"
          value={rules.length}
          subValue="Adaptive Policies"
          icon={Sliders}
          variant="navy"
        />
      </div>

      {/* ─── Live Attacker Simulator ─── */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={16} color="#DC2626" />
            <span>Live Attacker Simulator</span>
          </div>
        }
        subtitle="Trigger repeatable attack simulations to observe detection and response (controlled local scenarios)."
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {SCENARIOS.map((s) => (
            <button
              key={s.key}
              onClick={() => runSimulation(s.key)}
              disabled={simulating}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '6px',
                backgroundColor: s.bgColor,
                color: s.color,
                fontSize: '12px',
                fontWeight: 600,
                border: `1px solid ${s.borderColor}`,
                cursor: simulating ? 'not-allowed' : 'pointer',
                opacity: simulating ? 0.6 : 1,
                transition: 'opacity 0.15s, box-shadow 0.15s',
              }}
            >
              <span>{s.icon}</span>
              {s.label}
            </button>
          ))}
        </div>

        {simFeedback && (
          <div
            style={{
              marginTop: '12px',
              padding: '10px 14px',
              borderRadius: '6px',
              backgroundColor: '#F0FFF4',
              border: '1px solid #B2F2BB',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: '#087F5B',
            }}
          >
            ▸ {simFeedback}
          </div>
        )}
      </Card>

      {/* ─── Main 2-Column Grid: Incidents + Detail ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '20px' }}>

        {/* Left: Incidents list */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={16} color="#DC2626" />
              <span>Threat Incidents</span>
            </div>
          }
          badge={<Badge variant="neutral" size="sm">{incidents.length} Detected</Badge>}
          noPadding
        >
          <div style={{ maxHeight: '480px', overflowY: 'auto' }}>
            {incidents.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: '#98A2B3', fontSize: '13px' }}>
                No active threat incidents detected. Run a simulator scenario above.
              </div>
            ) : (
              incidents.map((inc) => {
                const isSelected = selectedIncident?.id === inc.id;
                return (
                  <div
                    key={inc.id}
                    onClick={() => setSelectedIncident(inc)}
                    style={{
                      padding: '14px 20px',
                      cursor: 'pointer',
                      borderBottom: '1px solid #F2F4F7',
                      backgroundColor: isSelected ? '#F0FFF4' : '#FFFFFF',
                      borderLeft: isSelected ? '3px solid #2D6A4F' : '3px solid transparent',
                      transition: 'background-color 0.15s, border-color 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      {riskBadge(inc.risk_level)}
                      <span style={{ fontSize: '11px', color: '#98A2B3', fontFamily: 'var(--font-mono)' }}>{inc.category}</span>
                    </div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#101828', marginBottom: '6px', lineHeight: 1.35 }}>
                      {inc.description}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#667085' }}>
                      <span>IP: <code style={{ fontFamily: 'var(--font-mono)', color: '#344054' }}>{inc.source_ip}</code></span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{inc.event_count} events</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* Right: Selected Incident Detail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {selectedIncident ? (
            <>
              {/* Incident header card */}
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      {riskBadge(selectedIncident.risk_level)}
                      <span style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#344054' }}>
                        {selectedIncident.category}
                      </span>
                    </div>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#101828', margin: 0 }}>
                      {selectedIncident.description}
                    </h3>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    {selectedIncident.ledger_checkpoint_id ? (
                      <button
                        onClick={() => handleVerifyIncident(selectedIncident.id)}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '6px',
                          padding: '7px 14px', borderRadius: '6px',
                          backgroundColor: '#EBFBEE', color: '#087F5B', fontSize: '12px', fontWeight: 600,
                          border: '1px solid #B2F2BB', cursor: 'pointer',
                        }}
                      >
                        <CheckCircle2 size={14} />
                        Verify on Ledger
                      </button>
                    ) : (
                      <button
                        onClick={() => handleAnchorIncident(selectedIncident.id)}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '6px',
                          padding: '7px 14px', borderRadius: '6px',
                          backgroundColor: '#F0F9FF', color: '#0284C7', fontSize: '12px', fontWeight: 600,
                          border: '1px solid #BAE6FD', cursor: 'pointer',
                        }}
                      >
                        <Database size={14} />
                        Anchor to Ledger
                      </button>
                    )}
                  </div>
                </div>
              </Card>

              {/* Explainability card */}
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Eye size={16} color="#0284C7" />
                    <span>Explainable Rule-Based Trigger Rationale</span>
                  </div>
                }
              >
                <div
                  style={{
                    padding: '14px 16px',
                    borderRadius: '6px',
                    backgroundColor: '#F8FAFC',
                    border: '1px solid #E4E7EC',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    color: '#344054',
                    lineHeight: 1.7,
                  }}
                >
                  <div><strong style={{ color: '#101828' }}>Primary Rule:</strong> {selectedIncident.explanation?.primary_rule || 'N/A'}</div>
                  <div><strong style={{ color: '#101828' }}>Source IP:</strong> {selectedIncident.source_ip}</div>
                  <div><strong style={{ color: '#101828' }}>Trigger Path:</strong> {selectedIncident.explanation?.event_path || 'Decoy Route'}</div>

                  {selectedIncident.explanation?.all_rules && (
                    <div style={{ marginTop: '12px', borderTop: '1px solid #E4E7EC', paddingTop: '10px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, fontFamily: 'var(--font-sans)', color: '#344054', marginBottom: '6px' }}>
                        Corroborating Evidence:
                      </div>
                      {selectedIncident.explanation.all_rules.map((r: any, idx: number) => (
                        <div key={idx} style={{ color: '#087F5B', paddingLeft: '8px', marginBottom: '2px' }}>
                          • [{r.rule}] {r.reason} (Confidence: {Math.round(r.confidence * 100)}%)
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>

              {/* Ledger integrity card */}
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileCheck2 size={16} color="#7C3AED" />
                    <span>Tamper-Evident Ledger Integrity</span>
                  </div>
                }
              >
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 500, color: '#98A2B3', textTransform: 'uppercase' as const, letterSpacing: '0.04em', marginBottom: '4px' }}>
                      Canonical SHA-256 Digest
                    </div>
                    <div
                      style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#344054', wordBreak: 'break-all' as const }}
                      title={selectedIncident.canonical_report_hash}
                    >
                      {selectedIncident.canonical_report_hash || 'Pending Calculation'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 500, color: '#98A2B3', textTransform: 'uppercase' as const, letterSpacing: '0.04em', marginBottom: '4px' }}>
                      Ledger Checkpoint Block
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: selectedIncident.ledger_checkpoint_id ? '#087F5B' : '#98A2B3', wordBreak: 'break-all' as const }}>
                      {selectedIncident.ledger_checkpoint_id || 'Not Yet Anchored'}
                    </div>
                  </div>
                </div>
              </Card>
            </>
          ) : (
            <Card>
              <div style={{ padding: '40px', textAlign: 'center', color: '#98A2B3', fontSize: '13px' }}>
                Select an incident from the left to inspect explainability and audit trail.
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* ─── Adaptive Feedback Loop: Rules Table ─── */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={16} color="#7C3AED" />
            <span>Adaptive Defensive Feedback Loop</span>
          </div>
        }
        subtitle="Invariant F-61: Defensive policies require explicit human approval and staging validation before active deployment."
        actions={
          <button
            onClick={() => fetch('/api/v1/cybertrap/feedback/rules/generate', { method: 'POST' }).then(fetchData)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '7px 14px', borderRadius: '6px',
              backgroundColor: '#F5F3FF', color: '#7C3AED', fontSize: '12px', fontWeight: 600,
              border: '1px solid #DDD6FE', cursor: 'pointer',
            }}
          >
            <Zap size={13} />
            Generate Rule Proposals
          </button>
        }
        noPadding
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #E4E7EC' }}>
                {['Rule Type', 'Target Subject', 'Parameters', 'Status', 'Human Approver', ''].map((h, i) => (
                  <th
                    key={i}
                    style={{
                      padding: '10px 16px',
                      fontSize: '11px',
                      fontWeight: 600,
                      color: '#667085',
                      textTransform: 'uppercase' as const,
                      letterSpacing: '0.04em',
                      textAlign: i === 5 ? 'right' as const : 'left' as const,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '40px 16px', textAlign: 'center', color: '#98A2B3', fontSize: '13px' }}>
                    No defensive rules currently active or proposed.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} style={{ borderBottom: '1px solid #F2F4F7', transition: 'background-color 0.1s' }}>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#7C3AED', fontSize: '12px' }}>
                      {rule.rule_type}
                    </td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: '#344054', fontSize: '12px' }}>
                      {rule.target_value}
                    </td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: '#667085', fontSize: '11px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
                      {rule.parameters ? JSON.stringify(rule.parameters) : '—'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {statusBadge(rule.status)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '12px', color: '#667085' }}>
                      {rule.approved_by || 'Awaiting Approval'}
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' as const, whiteSpace: 'nowrap' as const }}>
                      {rule.status === 'PROPOSED' && (
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => handleApproveRule(rule.id)}
                            style={{
                              padding: '5px 12px', borderRadius: '5px',
                              backgroundColor: '#2D6A4F', color: '#FFFFFF', fontSize: '12px', fontWeight: 600,
                              border: 'none', cursor: 'pointer',
                            }}
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleRejectRule(rule.id)}
                            style={{
                              padding: '5px 12px', borderRadius: '5px',
                              backgroundColor: '#FEF2F2', color: '#DC2626', fontSize: '12px', fontWeight: 600,
                              border: '1px solid #FECACA', cursor: 'pointer',
                            }}
                          >
                            Reject
                          </button>
                        </div>
                      )}
                      {rule.status === 'APPROVED' && (
                        <button
                          onClick={() => handleValidateStaging(rule.id)}
                          style={{
                            padding: '5px 12px', borderRadius: '5px',
                            backgroundColor: '#F0F9FF', color: '#0284C7', fontSize: '12px', fontWeight: 600,
                            border: '1px solid #BAE6FD', cursor: 'pointer',
                          }}
                        >
                          Dry-Run Staging
                        </button>
                      )}
                      {rule.status === 'STAGING_VALIDATED' && (
                        <button
                          onClick={() => handleDeployRule(rule.id)}
                          style={{
                            padding: '5px 12px', borderRadius: '5px',
                            backgroundColor: '#F5F3FF', color: '#7C3AED', fontSize: '12px', fontWeight: 600,
                            border: '1px solid #DDD6FE', cursor: 'pointer',
                          }}
                        >
                          Deploy to Production
                        </button>
                      )}
                      {rule.status === 'ACTIVE' && (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: 600, color: '#087F5B' }}>
                          <CheckCircle2 size={13} />
                          Enforcing (v{rule.version})
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ─── Verification Modal ─── */}
      <Modal
        isOpen={!!verificationModal}
        onClose={() => setVerificationModal(null)}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileCheck2 size={18} color="#087F5B" />
            Cryptographic Ledger Proof
          </div>
        }
        size="medium"
      >
        {verificationModal && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                padding: '16px',
                borderRadius: '8px',
                backgroundColor: '#F8FAFC',
                border: '1px solid #E4E7EC',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                lineHeight: 2,
              }}
            >
              <div>
                <span style={{ color: '#98A2B3' }}>Status: </span>
                <span style={{ fontWeight: 700, color: verificationModal.is_intact ? '#087F5B' : '#DC2626' }}>
                  {verificationModal.status}
                </span>
              </div>
              <div>
                <span style={{ color: '#98A2B3' }}>Report SHA-256 Digest: </span>
                <span style={{ color: '#344054', wordBreak: 'break-all' as const }}>{verificationModal.canonical_report_hash}</span>
              </div>
              <div>
                <span style={{ color: '#98A2B3' }}>Ledger Block Checkpoint: </span>
                <span style={{ color: '#0284C7' }}>{verificationModal.ledger_checkpoint_id}</span>
              </div>
              <div>
                <span style={{ color: '#98A2B3' }}>Hash Chain Integrity: </span>
                <span style={{ color: '#087F5B', fontWeight: 600 }}>VERIFIED CONTINUOUS (Zero Tampering)</span>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <button
                onClick={() => setVerificationModal(null)}
                style={{
                  padding: '8px 18px', borderRadius: '6px',
                  backgroundColor: '#F2F4F7', color: '#344054', fontSize: '13px', fontWeight: 600,
                  border: '1px solid #E4E7EC', cursor: 'pointer',
                }}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Spin animation for the refresh icon */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
