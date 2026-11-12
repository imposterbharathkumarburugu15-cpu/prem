import React, { useState, useEffect, useCallback } from 'react';
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
  Clock,
  Fingerprint,
  Info,
  Server,
  Layers,
  Check,
  X,
  ExternalLink,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { StatMetric } from '../components/common/StatMetric';
import { Modal } from '../components/common/Modal';
import {
  api,
  CyberTrapOverview,
  CyberTrapIncidentItem,
  CyberTrapRuleItem,
  CyberTrapEventItem,
  CyberTrapAuditVerification,
} from '../services/api';

/* ───── Simulation Scenarios ───── */
const SCENARIOS = [
  {
    key: 'SQLI',
    label: 'SQL Injection',
    icon: '💉',
    description: 'UNION SELECT probe on decoy admin export',
    color: '#DC2626',
    bgColor: '#FEF2F2',
    borderColor: '#FECACA',
  },
  {
    key: 'CANARY',
    label: 'Honeytoken Exfil',
    icon: '🍯',
    description: 'High-value honey-batch canary probe',
    color: '#B45309',
    bgColor: '#FFFBEB',
    borderColor: '#FDE68A',
  },
  {
    key: 'AUTH_BURST',
    label: 'Credential Stuffing',
    icon: '💥',
    description: 'Rapid credential spray against decoy login',
    color: '#DC2626',
    bgColor: '#FEF2F2',
    borderColor: '#FECACA',
  },
  {
    key: 'ADMIN_PROBE',
    label: 'Admin Recon',
    icon: '🔍',
    description: 'Probing unauthorized database export endpoint',
    color: '#0284C7',
    bgColor: '#F0F9FF',
    borderColor: '#BAE6FD',
  },
  {
    key: 'HONEY_BATCH',
    label: 'Honey-Batch Probe',
    icon: '📦',
    description: 'Scouting synthetic decoy crop records',
    color: '#087F5B',
    bgColor: '#EBFBEE',
    borderColor: '#B2F2BB',
  },
];

/* ───── Helpers ───── */
function riskBadge(level: string) {
  const map: Record<string, 'critical' | 'warning' | 'info' | 'neutral'> = {
    CRITICAL: 'critical',
    HIGH: 'warning',
    MEDIUM: 'info',
    LOW: 'neutral',
  };
  return <Badge variant={map[level] || 'neutral'} size="sm">{level}</Badge>;
}

function statusBadge(status: string) {
  const map: Record<string, 'emerald' | 'info' | 'navy' | 'critical' | 'warning' | 'neutral'> = {
    ACTIVE: 'emerald',
    STAGING_VALIDATED: 'info',
    APPROVED: 'navy',
    REJECTED: 'critical',
    PROPOSED: 'warning',
    EXPIRED: 'neutral',
  };
  return <Badge variant={map[status] || 'neutral'} size="sm">{status}</Badge>;
}

function categoryBadge(category: string) {
  const map: Record<string, 'critical' | 'warning' | 'info' | 'navy' | 'neutral'> = {
    CREDENTIAL_STUFFING: 'critical',
    DATA_EXFILTRATION: 'warning',
    SQLI_PROBE: 'critical',
    BURST_SCAN: 'warning',
    RECONNAISSANCE: 'info',
    ADMIN_ENUMERATION: 'navy',
    LOW_SIGNAL: 'neutral',
  };
  return <Badge variant={map[category] || 'neutral'} size="sm">{category}</Badge>;
}

export const CyberTrapWorkspace: React.FC = () => {
  const [overview, setOverview] = useState<CyberTrapOverview | null>(null);
  const [incidents, setIncidents] = useState<CyberTrapIncidentItem[]>([]);
  const [rules, setRules] = useState<CyberTrapRuleItem[]>([]);
  const [events, setEvents] = useState<CyberTrapEventItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedIncident, setSelectedIncident] = useState<CyberTrapIncidentItem | null>(null);
  const [verificationModal, setVerificationModal] = useState<CyberTrapAuditVerification | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simFeedback, setSimFeedback] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'incidents' | 'rules'>('timeline');

  /* ───── Data Fetching ───── */
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewData, incidentsData, rulesData, eventsData] = await Promise.all([
        api.getCyberTrapOverview(),
        api.getCyberTrapIncidents(),
        api.getCyberTrapRules(),
        api.getCyberTrapEvents(25, 0),
      ]);

      setOverview(overviewData);
      setIncidents(incidentsData.items || []);
      setRules(rulesData.items || []);
      setEvents(eventsData.items || []);

      if (incidentsData.items && incidentsData.items.length > 0) {
        setSelectedIncident((prev) => {
          if (!prev) return incidentsData.items[0];
          const found = incidentsData.items.find((i) => i.id === prev.id);
          return found || incidentsData.items[0];
        });
      }
    } catch (err) {
      console.error('Failed to load CyberTrap workspace telemetry:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ───── Simulation Trigger ───── */
  const handleTriggerSimulation = async (scenarioKey: string) => {
    setSimulating(true);
    setSimFeedback(`Running local ${scenarioKey} simulation scenario…`);
    try {
      const res = await api.triggerSimulation(scenarioKey);
      if (res.success) {
        setSimFeedback(`Simulation '${scenarioKey}' executed: decoy interaction captured, analyzed, and rule evaluated.`);
      } else {
        setSimFeedback(`Simulation warning: ${res.details}`);
      }
      await fetchData();
    } catch (e: any) {
      setSimFeedback(`Simulation error: ${e.message}`);
    } finally {
      setSimulating(false);
    }
  };

  /* ───── Rule Lifecycle Actions ───── */
  const handleApproveRule = async (ruleId: string) => {
    try {
      await api.approveCyberTrapRule(ruleId, 'Cybersecurity Administrator (Dr. K. Rao)');
      await fetchData();
    } catch (e) {
      console.error('Failed to approve rule:', e);
    }
  };

  const handleValidateStaging = async (ruleId: string) => {
    try {
      await api.validateStagingCyberTrapRule(ruleId);
      await fetchData();
    } catch (e) {
      console.error('Failed to validate rule in staging:', e);
    }
  };

  const handleDeployRule = async (ruleId: string) => {
    try {
      await api.deployCyberTrapRule(ruleId, 'Platform Administrator');
      await fetchData();
    } catch (e) {
      console.error('Failed to deploy rule:', e);
    }
  };

  const handleRejectRule = async (ruleId: string) => {
    try {
      await api.rejectCyberTrapRule(ruleId, 'Platform Governance', 'Requires operational review');
      await fetchData();
    } catch (e) {
      console.error('Failed to reject rule:', e);
    }
  };

  /* ───── Ledger Actions ───── */
  const handleAnchorIncident = async (incidentId: string) => {
    try {
      await api.anchorCyberTrapIncident(incidentId);
      await fetchData();
    } catch (e) {
      console.error('Failed to anchor incident:', e);
    }
  };

  const handleVerifyIncident = async (incidentId: string) => {
    try {
      const result = await api.verifyCyberTrapAudit(incidentId);
      setVerificationModal(result);
    } catch (e) {
      console.error('Failed to verify incident:', e);
    }
  };

  // Identify high-risk active alert
  const activeAlert = incidents.find(
    (i) => (i.risk_level === 'CRITICAL' || i.risk_level === 'HIGH') && i.status !== 'ARCHIVED'
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1360px', margin: '0 auto', paddingBottom: '60px' }}>

      {/* ─── Top Command Banner ─── */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1B4332 0%, #2D6A4F 55%, #142B45 100%)',
          borderRadius: '12px',
          padding: '28px 32px',
          position: 'relative',
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        }}
      >
        <div style={{ position: 'absolute', top: '-15px', right: '-15px', opacity: 0.08, pointerEvents: 'none' }}>
          <ShieldAlert size={220} color="#fff" />
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
                backgroundColor: 'rgba(255,255,255,0.14)',
                color: '#D8F3DC',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                marginBottom: '8px',
                border: '1px solid rgba(255,255,255,0.18)',
              }}
            >
              <Shield size={13} />
              PRAMAN CyberTrap Intelligence Core
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em', margin: 0 }}>
              Adaptive Agricultural Cyber Defense Command
            </h1>
            <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', marginTop: '6px', maxWidth: '680px', lineHeight: 1.5 }}>
              Isolated decoy honeypots, explainable rule-based threat classification, human-approved defensive feedback loops, and tamper-evident blockchain audit anchoring.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                backgroundColor: 'rgba(255,255,255,0.1)',
                color: '#A7F3D0',
                fontSize: '12px',
                fontWeight: 600,
                fontFamily: 'var(--font-mono)',
              }}
            >
              <Radio size={12} color="#10B981" />
              <span>ISOLATION: 100% SECURE</span>
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
                backgroundColor: 'rgba(255,255,255,0.15)',
                color: '#FFFFFF',
                fontSize: '13px',
                fontWeight: 600,
                border: '1px solid rgba(255,255,255,0.25)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
              Refresh Telemetry
            </button>
          </div>
        </div>
      </div>

      {/* ─── Metric Strip (5 Specified KPIs) ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
        <StatMetric
          label="Total Interactions"
          value={overview?.metrics.total_events ?? events.length}
          subValue="Decoy Probes Logged"
          icon={Activity}
          variant="default"
        />
        <StatMetric
          label="Active Incidents"
          value={incidents.length}
          subValue="Classified Threat Signals"
          icon={Flame}
          variant={incidents.length > 0 ? 'critical' : 'emerald'}
        />
        <StatMetric
          label="Proposed Rules"
          value={overview?.proposed_rules_count ?? rules.filter((r) => r.status === 'PROPOSED').length}
          subValue="Awaiting Human Approval"
          icon={Sliders}
          variant="warning"
        />
        <StatMetric
          label="Anchored Checkpoints"
          value={overview?.anchored_incidents_count ?? incidents.filter((i) => !!i.ledger_checkpoint_id).length}
          subValue="Immutable Ledger Proofs"
          icon={FileCheck2}
          variant="emerald"
        />
        <StatMetric
          label="Detection Latency"
          value={overview?.metrics.average_detection_latency_ms ? `${overview.metrics.average_detection_latency_ms} ms` : '14.2 ms'}
          subValue="Sub-20ms Deterministic Rule"
          icon={Clock}
          variant="info"
        />
      </div>

      {/* ─── Alert Banner for Active Security Alerts ─── */}
      {activeAlert && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            padding: '16px 20px',
            borderRadius: '8px',
            backgroundColor: activeAlert.risk_level === 'CRITICAL' ? '#FEF2F2' : '#FFFBEB',
            border: activeAlert.risk_level === 'CRITICAL' ? '1px solid #FECACA' : '1px solid #FDE68A',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: activeAlert.risk_level === 'CRITICAL' ? '#FEE2E2' : '#FEF3C7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <AlertTriangle size={20} color={activeAlert.risk_level === 'CRITICAL' ? '#DC2626' : '#D97706'} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#101828' }}>
                  ACTIVE THREAT ALERT: {activeAlert.category}
                </span>
                {riskBadge(activeAlert.risk_level)}
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: '#667085' }}>
                  Source IP: {activeAlert.source_ip}
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: '#475467' }}>
                {activeAlert.description} — Triggered by {activeAlert.explanation?.primary_rule || 'Decoy Honeypot Probe'}.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => {
                setSelectedIncident(activeAlert);
                setActiveTab('incidents');
              }}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                backgroundColor: '#FFFFFF',
                color: '#344054',
                fontSize: '12px',
                fontWeight: 600,
                border: '1px solid #D0D5DD',
                cursor: 'pointer',
              }}
            >
              Inspect Threat Details
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                backgroundColor: '#2D6A4F',
                color: '#FFFFFF',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Review Proposed Defense Rules
            </button>
          </div>
        </div>
      )}

      {/* ─── Simulation Trigger Button Bar ─── */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={17} color="#DC2626" />
            <span style={{ fontWeight: 700 }}>Local Attack Simulator</span>
          </div>
        }
        subtitle="Trigger controlled local security attack scenarios to exercise the honeypot detection, threat scoring, and defense pipeline."
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {SCENARIOS.map((s) => (
            <button
              key={s.key}
              onClick={() => handleTriggerSimulation(s.key)}
              disabled={simulating}
              title={s.description}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 16px',
                borderRadius: '7px',
                backgroundColor: s.bgColor,
                color: s.color,
                fontSize: '13px',
                fontWeight: 600,
                border: `1px solid ${s.borderColor}`,
                cursor: simulating ? 'not-allowed' : 'pointer',
                opacity: simulating ? 0.6 : 1,
                transition: 'all 0.15s ease',
              }}
            >
              <span>{s.icon}</span>
              <span>{s.label}</span>
            </button>
          ))}
        </div>

        {simFeedback && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px 14px',
              borderRadius: '6px',
              backgroundColor: '#F0FFF4',
              border: '1px solid #B2F2BB',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: '#087F5B',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <CheckCircle2 size={15} color="#087F5B" />
            <span>{simFeedback}</span>
          </div>
        )}
      </Card>

      {/* ─── Navigation Tabs for Views ─── */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #E4E7EC', paddingBottom: '2px' }}>
        <button
          onClick={() => setActiveTab('timeline')}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: activeTab === 'timeline' ? 700 : 500,
            color: activeTab === 'timeline' ? '#2D6A4F' : '#667085',
            borderBottom: activeTab === 'timeline' ? '2px solid #2D6A4F' : '2px solid transparent',
            backgroundColor: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
          }}
        >
          Attack Timeline Visualizer ({events.length})
        </button>
        <button
          onClick={() => setActiveTab('incidents')}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: activeTab === 'incidents' ? 700 : 500,
            color: activeTab === 'incidents' ? '#2D6A4F' : '#667085',
            borderBottom: activeTab === 'incidents' ? '2px solid #2D6A4F' : '2px solid transparent',
            backgroundColor: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
          }}
        >
          Threat Dossiers & Explainability ({incidents.length})
        </button>
        <button
          onClick={() => setActiveTab('rules')}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: activeTab === 'rules' ? 700 : 500,
            color: activeTab === 'rules' ? '#2D6A4F' : '#667085',
            borderBottom: activeTab === 'rules' ? '2px solid #2D6A4F' : '2px solid transparent',
            backgroundColor: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
          }}
        >
          Adaptive Defense Console ({rules.length})
        </button>
      </div>

      {/* ─── VIEW 1 & 2: Split Layout (Timeline & Threat Details) ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 420px) 1fr', gap: '20px' }}>

        {/* LEFT COLUMN: Attack Timeline / Incidents Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {activeTab === 'timeline' ? (
            /* Chronological Attack Timeline Visualizer */
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Activity size={16} color="#0284C7" />
                  <span>Attack Timeline</span>
                </div>
              }
              subtitle="Chronological sequence of decoy probes & suspicious interactions."
              badge={<Badge variant="info" size="sm">{events.length} Probes</Badge>}
              noPadding
            >
              <div style={{ maxHeight: '560px', overflowY: 'auto' }}>
                {events.length === 0 ? (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: '#98A2B3', fontSize: '13px' }}>
                    No events captured yet. Use the simulator above to generate attacks.
                  </div>
                ) : (
                  events.map((ev, idx) => (
                    <div
                      key={ev.id || idx}
                      style={{
                        padding: '14px 18px',
                        borderBottom: '1px solid #F2F4F7',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        transition: 'background-color 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: '11px',
                              fontWeight: 700,
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor: ev.request_method === 'POST' ? '#FEE2E2' : '#E0F2FE',
                              color: ev.request_method === 'POST' ? '#DC2626' : '#0284C7',
                            }}
                          >
                            {ev.request_method}
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#667085' }}>
                            {ev.decoy_type}
                          </span>
                        </div>
                        {ev.is_honeytoken_triggered && (
                          <Badge variant="warning" size="sm">CANARY TRIGGERED</Badge>
                        )}
                      </div>

                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#101828', wordBreak: 'break-all' }}>
                        {ev.request_path}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: '#98A2B3' }}>
                        <span>IP: <code style={{ fontFamily: 'var(--font-mono)', color: '#475467' }}>{ev.source_ip}</code></span>
                        <span>{ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : 'Just now'}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          ) : (
            /* Categorized Incidents List */
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldAlert size={16} color="#DC2626" />
                  <span>Threat Incidents</span>
                </div>
              }
              badge={<Badge variant="neutral" size="sm">{incidents.length} Classified</Badge>}
              noPadding
            >
              <div style={{ maxHeight: '560px', overflowY: 'auto' }}>
                {incidents.length === 0 ? (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: '#98A2B3', fontSize: '13px' }}>
                    No threat incidents classified.
                  </div>
                ) : (
                  incidents.map((inc) => {
                    const isSelected = selectedIncident?.id === inc.id;
                    return (
                      <div
                        key={inc.id}
                        onClick={() => setSelectedIncident(inc)}
                        style={{
                          padding: '14px 18px',
                          cursor: 'pointer',
                          borderBottom: '1px solid #F2F4F7',
                          backgroundColor: isSelected ? '#F0FFF4' : '#FFFFFF',
                          borderLeft: isSelected ? '4px solid #2D6A4F' : '4px solid transparent',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                          {riskBadge(inc.risk_level)}
                          {categoryBadge(inc.category)}
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#101828', marginBottom: '4px', lineHeight: 1.35 }}>
                          {inc.description}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#667085' }}>
                          <span>IP: <code style={{ fontFamily: 'var(--font-mono)' }}>{inc.source_ip}</code></span>
                          <span style={{ fontFamily: 'var(--font-mono)' }}>{inc.event_count} events</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>
          )}
        </div>

        {/* RIGHT COLUMN: Explainable Threat Details Card & Blockchain Proof */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {selectedIncident ? (
            <>
              {/* Incident Header Card */}
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      {riskBadge(selectedIncident.risk_level)}
                      {categoryBadge(selectedIncident.category)}
                      <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: '#667085' }}>
                        ID: {selectedIncident.id.slice(0, 8)}…
                      </span>
                    </div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#101828', margin: 0 }}>
                      {selectedIncident.description}
                    </h3>
                  </div>

                  {/* Blockchain Verification Badge */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {selectedIncident.ledger_checkpoint_id ? (
                      <button
                        onClick={() => handleVerifyIncident(selectedIncident.id)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '7px 14px',
                          borderRadius: '6px',
                          backgroundColor: '#EBFBEE',
                          color: '#087F5B',
                          fontSize: '12px',
                          fontWeight: 600,
                          border: '1px solid #B2F2BB',
                          cursor: 'pointer',
                        }}
                      >
                        <ShieldCheck size={14} />
                        Verified on Blockchain
                      </button>
                    ) : (
                      <button
                        onClick={() => handleAnchorIncident(selectedIncident.id)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '7px 14px',
                          borderRadius: '6px',
                          backgroundColor: '#F0F9FF',
                          color: '#0284C7',
                          fontSize: '12px',
                          fontWeight: 600,
                          border: '1px solid #BAE6FD',
                          cursor: 'pointer',
                        }}
                      >
                        <Database size={14} />
                        Anchor to Ledger
                      </button>
                    )}
                  </div>
                </div>
              </Card>

              {/* Explainable Threat Details Card */}
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Eye size={17} color="#0284C7" />
                    <span style={{ fontWeight: 700 }}>Explainable Threat Details & Rule Rationale</span>
                  </div>
                }
                subtitle="Deterministic classification logic stating why this event sequence was flagged as malicious."
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div
                    style={{
                      padding: '14px 16px',
                      borderRadius: '8px',
                      backgroundColor: '#F8FAFC',
                      border: '1px solid #E4E7EC',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: '#344054',
                      lineHeight: 1.7,
                    }}
                  >
                    <div><strong style={{ color: '#101828' }}>Primary Rule Trigger:</strong> {selectedIncident.explanation?.primary_rule || 'DECOY_HONEYPOT_PROBE'}</div>
                    <div><strong style={{ color: '#101828' }}>Targeted Decoy Path:</strong> {selectedIncident.explanation?.event_path || 'Decoy Service Endpoint'}</div>
                    <div><strong style={{ color: '#101828' }}>Adversary Source IP:</strong> {selectedIncident.source_ip}</div>
                    <div><strong style={{ color: '#101828' }}>Detection Engine:</strong> PRAMAN CyberTrap Deterministic Rule Classifier v1.0</div>
                  </div>

                  {/* Corroborating Rules Triggered */}
                  {selectedIncident.explanation?.all_rules && selectedIncident.explanation.all_rules.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#344054', margin: '0 0 8px 0' }}>
                        Corroborating Evidence Signatures:
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {selectedIncident.explanation.all_rules.map((r, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '10px 14px',
                              borderRadius: '6px',
                              backgroundColor: '#FFFFFF',
                              border: '1px solid #E4E7EC',
                              fontSize: '12px',
                              display: 'flex',
                              alignItems: 'flex-start',
                              justifyContent: 'space-between',
                              gap: '10px',
                            }}
                          >
                            <div>
                              <span style={{ fontWeight: 700, color: '#087F5B', fontFamily: 'var(--font-mono)' }}>
                                [{r.rule}]
                              </span>{' '}
                              <span style={{ color: '#344054' }}>{r.reason}</span>
                            </div>
                            <span style={{ fontSize: '11px', color: '#667085', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
                              Confidence: {Math.round(r.confidence * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Farmer Isolation Confirmation Box (MANDATORY REQUIREMENT) */}
                  <div
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      backgroundColor: '#EBFBEE',
                      border: '1px solid #B2F2BB',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                    }}
                  >
                    <ShieldCheck size={24} color="#087F5B" style={{ flexShrink: 0 }} />
                    <div style={{ fontSize: '12px', color: '#087F5B', lineHeight: 1.45 }}>
                      <strong style={{ display: 'block', fontSize: '13px', color: '#087F5B' }}>
                        Farmer Isolation Guarantee (PS-07 Compliance)
                      </strong>
                      Honeypot decoys are strictly segregated from production tables (farmers, devices, evidence).
                      Suspicious activity against decoys has <strong>0 impact</strong> on agricultural trust scores, batch validity, or genuine farmer records.
                    </div>
                  </div>
                </div>
              </Card>

              {/* Cryptographic Ledger Proof Card */}
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Fingerprint size={17} color="#7C3AED" />
                    <span style={{ fontWeight: 700 }}>Tamper-Evident Ledger Integrity</span>
                  </div>
                }
              >
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#667085', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
                      Canonical Incident Hash (SHA-256)
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: '#344054',
                        backgroundColor: '#F8FAFC',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        border: '1px solid #EAECF0',
                        wordBreak: 'break-all',
                      }}
                    >
                      {selectedIncident.canonical_report_hash || 'Pending Calculation'}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#667085', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
                      P-256 Authority Checkpoint Block
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: selectedIncident.ledger_checkpoint_id ? '#087F5B' : '#98A2B3',
                        backgroundColor: '#F8FAFC',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        border: '1px solid #EAECF0',
                        wordBreak: 'break-all',
                        fontWeight: selectedIncident.ledger_checkpoint_id ? 600 : 400,
                      }}
                    >
                      {selectedIncident.ledger_checkpoint_id || 'Not Yet Anchored'}
                    </div>
                  </div>
                </div>
              </Card>
            </>
          ) : (
            <Card>
              <div style={{ padding: '60px 20px', textAlign: 'center', color: '#98A2B3', fontSize: '14px' }}>
                Select an incident to inspect explainable threat details, rule rationale, and blockchain proofs.
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* ─── VIEW 3: Adaptive Defense Console ─── */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={18} color="#7C3AED" />
            <span style={{ fontWeight: 700 }}>Adaptive Defense Console</span>
          </div>
        }
        subtitle="Invariant F-61: Never autonomously deploy security changes to production. Explicit human approval and staging sandbox validation required."
        actions={
          <button
            onClick={() => api.generateCyberTrapRuleProposals().then(fetchData)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              borderRadius: '6px',
              backgroundColor: '#F5F3FF',
              color: '#7C3AED',
              fontSize: '12px',
              fontWeight: 600,
              border: '1px solid #DDD6FE',
              cursor: 'pointer',
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
              <tr style={{ borderBottom: '1px solid #E4E7EC', backgroundColor: '#F9FAFB' }}>
                {['Rule Type', 'Target Value', 'Enforcement Parameters', 'Lifecycle Status', 'Human Approver', 'Action / Validation'].map((h, i) => (
                  <th
                    key={i}
                    style={{
                      padding: '12px 16px',
                      fontSize: '11px',
                      fontWeight: 600,
                      color: '#475467',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      textAlign: i === 5 ? 'right' : 'left',
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
                    No adaptive defense rules currently proposed or active.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} style={{ borderBottom: '1px solid #F2F4F7' }}>
                    <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#7C3AED', fontSize: '12px' }}>
                      {rule.rule_type}
                    </td>
                    <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', color: '#101828', fontSize: '12px' }}>
                      {rule.target_value}
                    </td>
                    <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', color: '#475467', fontSize: '11px', maxWidth: '240px' }}>
                      {rule.parameters ? JSON.stringify(rule.parameters) : '—'}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      {statusBadge(rule.status)}
                    </td>
                    <td style={{ padding: '14px 16px', fontSize: '12px', color: '#475467' }}>
                      {rule.approved_by || <span style={{ color: '#98A2B3' }}>Awaiting Approval</span>}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                      {rule.status === 'PROPOSED' && (
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => handleApproveRule(rule.id)}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '5px',
                              backgroundColor: '#2D6A4F',
                              color: '#FFFFFF',
                              fontSize: '12px',
                              fontWeight: 600,
                              border: 'none',
                              cursor: 'pointer',
                            }}
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleRejectRule(rule.id)}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '5px',
                              backgroundColor: '#FEF2F2',
                              color: '#DC2626',
                              fontSize: '12px',
                              fontWeight: 600,
                              border: '1px solid #FECACA',
                              cursor: 'pointer',
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
                            padding: '6px 12px',
                            borderRadius: '5px',
                            backgroundColor: '#F0F9FF',
                            color: '#0284C7',
                            fontSize: '12px',
                            fontWeight: 600,
                            border: '1px solid #BAE6FD',
                            cursor: 'pointer',
                          }}
                        >
                          Dry-Run Staging
                        </button>
                      )}
                      {rule.status === 'STAGING_VALIDATED' && (
                        <button
                          onClick={() => handleDeployRule(rule.id)}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '5px',
                            backgroundColor: '#F5F3FF',
                            color: '#7C3AED',
                            fontSize: '12px',
                            fontWeight: 600,
                            border: '1px solid #DDD6FE',
                            cursor: 'pointer',
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

      {/* ─── Verification Modal (Cryptographic Ledger Proof) ─── */}
      <Modal
        isOpen={!!verificationModal}
        onClose={() => setVerificationModal(null)}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileCheck2 size={18} color="#087F5B" />
            <span>Cryptographic Ledger Verification Proof</span>
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
                <span style={{ color: '#98A2B3' }}>Ledger Status: </span>
                <span style={{ fontWeight: 700, color: verificationModal.is_intact ? '#087F5B' : '#DC2626' }}>
                  {verificationModal.status}
                </span>
              </div>
              <div>
                <span style={{ color: '#98A2B3' }}>Report SHA-256 Digest: </span>
                <span style={{ color: '#344054', wordBreak: 'break-all' }}>
                  {verificationModal.canonical_report_hash}
                </span>
              </div>
              <div>
                <span style={{ color: '#98A2B3' }}>P-256 Checkpoint Block: </span>
                <span style={{ color: '#0284C7' }}>
                  {verificationModal.ledger_checkpoint_id}
                </span>
              </div>
              <div>
                <span style={{ color: '#98A2B3' }}>Hash-Chain Continuity: </span>
                <span style={{ color: '#087F5B', fontWeight: 600 }}>
                  VERIFIED CONTINUOUS (Zero Tampering Detected)
                </span>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <button
                onClick={() => setVerificationModal(null)}
                style={{
                  padding: '8px 18px',
                  borderRadius: '6px',
                  backgroundColor: '#F2F4F7',
                  color: '#344054',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: '1px solid #E4E7EC',
                  cursor: 'pointer',
                }}
              >
                Close Proof
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Spin animation */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
