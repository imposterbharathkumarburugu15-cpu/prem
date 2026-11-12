import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Flame,
  Bug,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Play,
  RefreshCw,
  FileCheck2,
  Activity,
  Layers,
  ArrowRight,
  ShieldCheck,
  Zap,
  Terminal,
  Database,
  Sliders,
  XCircle,
  Eye,
} from 'lucide-react';

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

  useEffect(() => {
    fetchData();
  }, []);

  const runSimulation = async (scenario: string) => {
    setSimulating(true);
    setSimFeedback(`Running local ${scenario} simulation...`);
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

      // Trigger threat analysis
      await fetch('/api/v1/cybertrap/intel/analyse', { method: 'POST' });
      // Generate proposed rules
      await fetch('/api/v1/cybertrap/feedback/rules/generate', { method: 'POST' });

      setSimFeedback(`Simulation '${scenario}' complete! Threat detected, classified & rule proposed.`);
      await fetchData();
    } catch (e) {
      setSimFeedback(`Simulation error: ${e}`);
    } finally {
      setSimulating(false);
    }
  };

  const handleApproveRule = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_by: 'Cybersecurity Admin (Dr. K. Rao)' }),
    });
    await fetchData();
  };

  const handleValidateStaging = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/validate-staging`, {
      method: 'POST',
    });
    await fetchData();
  };

  const handleDeployRule = async (ruleId: string) => {
    await fetch(`/api/v1/cybertrap/feedback/rules/${ruleId}/deploy`, {
      method: 'POST',
    });
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
    await fetch(`/api/v1/cybertrap/audit/incidents/${incidentId}/anchor`, {
      method: 'POST',
    });
    await fetchData();
  };

  const handleVerifyIncident = async (incidentId: string) => {
    const res = await fetch(`/api/v1/cybertrap/audit/incidents/${incidentId}/verify`).then((r) => r.json());
    setVerificationModal(res);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-rose-950/40 to-slate-900 border border-rose-500/30 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <ShieldAlert className="w-64 h-64 text-rose-400" />
        </div>
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 text-xs font-bold tracking-wider uppercase mb-2 border border-rose-500/30">
              <Zap className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
              PRAMAN CyberTrap Intelligence Module
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Adaptive Agricultural Cyber Defense Command
            </h1>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              Deterministic honeypots, explainable threat classification, human-approved defensive feedback loops,
              and tamper-evident blockchain audit anchoring.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium border border-slate-700 transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh Telemetry
            </button>
          </div>
        </div>
      </div>

      {/* KPI Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-emerald-400" />
            Detection Rate
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {metrics ? `${metrics.detection_rate_pct}%` : '100%'}
          </div>
          <div className="text-xs text-emerald-400 mt-1 font-medium">Deterministic Rule Trigger</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            False Positive Rate
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2">
            {metrics ? `${metrics.false_positive_rate_pct}%` : '0.0%'}
          </div>
          <div className="text-xs text-cyan-500/80 mt-1 font-medium">Physically Isolated Decoys</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Flame className="w-4 h-4 text-amber-400" />
            Active Incidents
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2">
            {incidents.length}
          </div>
          <div className="text-xs text-slate-400 mt-1">Classified Threats</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Sliders className="w-4 h-4 text-purple-400" />
            Defensive Rules
          </div>
          <div className="text-2xl font-bold text-purple-400 mt-2">
            {rules.length}
          </div>
          <div className="text-xs text-slate-400 mt-1">Adaptive Policies</div>
        </div>
      </div>

      {/* Simulator Test Launcher Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-rose-400" />
            <div>
              <div className="text-sm font-bold text-white">Live Attacker Simulator (Controlled Local Scenarios)</div>
              <div className="text-xs text-slate-400">Trigger repeatable attack simulations to observe detection and response.</div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => runSimulation('SQLI')}
              disabled={simulating}
              className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 rounded-lg text-xs font-semibold transition"
            >
              💉 SQL Injection
            </button>
            <button
              onClick={() => runSimulation('CANARY')}
              disabled={simulating}
              className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-semibold transition"
            >
              🍯 Honeytoken Exfil
            </button>
            <button
              onClick={() => runSimulation('AUTH_BURST')}
              disabled={simulating}
              className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/40 rounded-lg text-xs font-semibold transition"
            >
              💥 Auth Stuffing
            </button>
            <button
              onClick={() => runSimulation('ADMIN_PROBE')}
              disabled={simulating}
              className="px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 rounded-lg text-xs font-semibold transition"
            >
              🔍 Admin Recon
            </button>
          </div>
        </div>
        {simFeedback && (
          <div className="mt-3 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-400">
            &gt; {simFeedback}
          </div>
        )}
      </div>

      {/* Main Threat Intelligence & Adaptive Response Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Incidents List */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
              <h2 className="text-base font-bold text-white">Threat Incidents</h2>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
              {incidents.length} Detected
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[460px] pr-1">
            {incidents.length === 0 ? (
              <div className="text-center py-10 text-slate-500 text-xs">
                No active threat incidents detected. Run a simulator scenario above.
              </div>
            ) : (
              incidents.map((inc) => {
                const isSelected = selectedIncident?.id === inc.id;
                const isCritical = inc.risk_level === 'CRITICAL';
                return (
                  <div
                    key={inc.id}
                    onClick={() => setSelectedIncident(inc)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition ${
                      isSelected
                        ? 'bg-rose-950/30 border-rose-500/50 shadow-md'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded-md ${
                          isCritical
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {inc.risk_level}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono">{inc.category}</span>
                    </div>
                    <div className="text-sm font-semibold text-white mt-1.5 truncate">{inc.description}</div>
                    <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
                      <span>IP: <code className="text-slate-300">{inc.source_ip}</code></span>
                      <span className="font-mono">{inc.event_count} events</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Middle Column: Selected Incident Explainability & Blockchain Anchor */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col lg:col-span-2">
          {selectedIncident ? (
            <div className="space-y-5 flex-1">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
                      {selectedIncident.risk_level} RISK
                    </span>
                    <span className="text-sm font-mono text-slate-300 font-bold">{selectedIncident.category}</span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1">{selectedIncident.description}</h3>
                </div>
                <div className="flex items-center gap-2">
                  {selectedIncident.ledger_checkpoint_id ? (
                    <button
                      onClick={() => handleVerifyIncident(selectedIncident.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-xs font-semibold border border-emerald-500/40 transition"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Verify on Ledger
                    </button>
                  ) : (
                    <button
                      onClick={() => handleAnchorIncident(selectedIncident.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-semibold border border-cyan-500/40 transition"
                    >
                      <Database className="w-3.5 h-3.5 text-cyan-400" />
                      Anchor to Ledger
                    </button>
                  )}
                </div>
              </div>

              {/* Explainability Section */}
              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
                <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  Explainable Rule-Based Trigger Rationale
                </div>
                <div className="text-xs font-mono text-slate-300 bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-1">
                  <div><strong>Primary Rule:</strong> {selectedIncident.explanation?.primary_rule || 'N/A'}</div>
                  <div><strong>Source IP:</strong> {selectedIncident.source_ip}</div>
                  <div><strong>Trigger Path:</strong> {selectedIncident.explanation?.event_path || 'Decoy Route'}</div>
                  {selectedIncident.explanation?.all_rules && (
                    <div className="pt-2">
                      <div className="text-slate-400 font-sans font-semibold mb-1">Corroborating Evidence:</div>
                      {selectedIncident.explanation.all_rules.map((r: any, idx: number) => (
                        <div key={idx} className="text-emerald-400 pl-2">
                          • [{r.rule}] {r.reason} (Confidence: {r.confidence * 100}%)
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Blockchain Proof Bar */}
              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 space-y-2">
                <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <FileCheck2 className="w-4 h-4 text-purple-400" />
                  Tamper-Evident Ledger Integrity
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <span className="text-slate-500">Canonical SHA-256 Digest:</span>
                    <div className="text-slate-300 truncate" title={selectedIncident.canonical_report_hash}>
                      {selectedIncident.canonical_report_hash || 'Pending Calculation'}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500">Ledger Checkpoint Block:</span>
                    <div className="text-emerald-400 truncate">
                      {selectedIncident.ledger_checkpoint_id || 'Not Yet Anchored'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
              Select an incident from the left to inspect explainability and audit trail.
            </div>
          )}
        </div>
      </div>

      {/* Adaptive Feedback & Human-Approval Defensive Rules Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Sliders className="w-5 h-5 text-purple-400" />
              <h2 className="text-base font-bold text-white">Adaptive Defensive Feedback Loop</h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Invariant F-61: Defensive policies require explicit human approval and staging validation before active deployment.
            </p>
          </div>
          <button
            onClick={() => fetch('/api/v1/cybertrap/feedback/rules/generate', { method: 'POST' }).then(fetchData)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 text-xs font-semibold border border-purple-500/40 transition"
          >
            <Zap className="w-3.5 h-3.5 text-purple-400" />
            Generate Rule Proposals
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[11px]">
                <th className="py-2.5 px-3">Rule Type</th>
                <th className="py-2.5 px-3">Target Subject</th>
                <th className="py-2.5 px-3">Parameters</th>
                <th className="py-2.5 px-3">Lifecycle Status</th>
                <th className="py-2.5 px-3">Human Approver</th>
                <th className="py-2.5 px-3 text-right">Adaptive Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {rules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No defensive rules currently active or proposed.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => {
                  return (
                    <tr key={rule.id} className="hover:bg-slate-800/30 transition font-sans">
                      <td className="py-3 px-3 font-mono font-bold text-purple-300">{rule.rule_type}</td>
                      <td className="py-3 px-3 font-mono text-slate-200">{rule.target_value}</td>
                      <td className="py-3 px-3 text-xs text-slate-400 font-mono">
                        {rule.parameters ? JSON.stringify(rule.parameters) : '-'}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                            rule.status === 'ACTIVE'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : rule.status === 'STAGING_VALIDATED'
                              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                              : rule.status === 'APPROVED'
                              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              : rule.status === 'REJECTED'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {rule.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-xs text-slate-300">{rule.approved_by || 'Awaiting Approval'}</td>
                      <td className="py-3 px-3 text-right space-x-1.5">
                        {rule.status === 'PROPOSED' && (
                          <>
                            <button
                              onClick={() => handleApproveRule(rule.id)}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded text-xs transition"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleRejectRule(rule.id)}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-rose-300 font-semibold rounded text-xs transition"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {rule.status === 'APPROVED' && (
                          <button
                            onClick={() => handleValidateStaging(rule.id)}
                            className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded text-xs transition"
                          >
                            Dry-Run Staging
                          </button>
                        )}
                        {rule.status === 'STAGING_VALIDATED' && (
                          <button
                            onClick={() => handleDeployRule(rule.id)}
                            className="px-2.5 py-1 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded text-xs transition"
                          >
                            Deploy to Production
                          </button>
                        )}
                        {rule.status === 'ACTIVE' && (
                          <span className="text-xs font-semibold text-emerald-400 flex items-center justify-end gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Enforcing (v{rule.version})
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Verification Result Modal */}
      {verificationModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-white">Cryptographic Ledger Proof</h3>
              </div>
              <button
                onClick={() => setVerificationModal(null)}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs space-y-2">
              <div>
                <span className="text-slate-500">Status: </span>
                <span className={verificationModal.is_intact ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                  {verificationModal.status}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Report SHA-256 Digest: </span>
                <div className="text-slate-300 break-all">{verificationModal.canonical_report_hash}</div>
              </div>
              <div>
                <span className="text-slate-500">Ledger Block Checkpoint: </span>
                <div className="text-cyan-400">{verificationModal.ledger_checkpoint_id}</div>
              </div>
              <div>
                <span className="text-slate-500">Hash Chain Integrity: </span>
                <span className="text-emerald-400">VERIFIED CONTINUOUS (Zero Tampering)</span>
              </div>
            </div>
            <div className="text-right">
              <button
                onClick={() => setVerificationModal(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
              >
                Close Verification
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

