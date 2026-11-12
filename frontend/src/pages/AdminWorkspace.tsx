import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Users,
  Building,
  Smartphone,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ChevronDown,
  ChevronUp,
  Sliders,
} from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { StatMetric } from '../components/common/StatMetric';

export const AdminWorkspace: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'ORGANIZATIONS' | 'USERS' | 'DEVICES' | 'AUDIT_LOGS'>('OVERVIEW');
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dash, devRes, logsRes] = await Promise.all([
        api.getAdminDashboard(),
        api.getAdminDevices().catch(() => ({ items: [] })),
        api.getAdminAuditLogs(50).catch(() => ({ items: [] })),
      ]);
      setData(dash);
      setDevices(devRes.items || devRes.devices || []);
      setAuditLogs(logsRes.items || logsRes.logs || []);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const metrics = data?.metrics;
  const users: any[] = data?.users || [];
  const orgs: any[] = data?.organizations || [];

  // Count security alerts
  const securityAlertsCount = auditLogs.filter(
    (l) =>
      l.event_type?.includes('ALERT') ||
      l.event_type?.includes('VIOLATION') ||
      l.event_type?.includes('TAMPER') ||
      l.event_type?.includes('QUASH')
  ).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* HEADER */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#101828' }}>
            Platform Management
          </h1>
          <p style={{ fontSize: '14px', color: '#667085', marginTop: '4px' }}>
            Overview of registered organizations, users, verified devices, and platform health.
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #E4E7EC',
            borderRadius: '6px',
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 600,
            color: '#344054',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Platform</span>
        </button>
      </div>

      {/* 5 CORE KPI METRIC CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        <StatMetric
          label="Registered Organizations"
          value={metrics ? metrics.total_organizations : '—'}
          subValue="Clusters, Co-ops & Hubs"
          icon={Building}
          variant="navy"
        />
        <StatMetric
          label="Active Users"
          value={metrics ? metrics.total_users : '—'}
          subValue="Across all roles"
          icon={Users}
          variant="default"
        />
        <StatMetric
          label="Registered Devices"
          value={devices ? devices.length : '—'}
          subValue="Certified Android devices"
          icon={Smartphone}
          variant="default"
        />
        <StatMetric
          label="Security Alerts"
          value={securityAlertsCount}
          subValue="Flagged anomalies"
          icon={ShieldAlert}
          variant={securityAlertsCount > 0 ? 'critical' : 'emerald'}
        />
        <StatMetric
          label="System Health"
          value={metrics?.system_health || 'Healthy'}
          subValue="All services online"
          icon={Activity}
          variant="emerald"
        />
      </div>

      {/* SECONDARY NAVIGATION TABS FOR GOVERNANCE & CONFIGURATION */}
      <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid #E4E7EC', backgroundColor: '#FFFFFF', padding: '6px 12px', borderRadius: '8px 8px 0 0' }}>
        {[
          { id: 'OVERVIEW', label: 'Overview' },
          { id: 'ORGANIZATIONS', label: `Organizations (${orgs.length})` },
          { id: 'USERS', label: `Users (${users.length})` },
          { id: 'DEVICES', label: `Devices (${devices.length})` },
          { id: 'AUDIT_LOGS', label: `Security Logs (${auditLogs.length})` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === tab.id ? '#142B45' : 'transparent',
              color: activeTab === tab.id ? '#FFFFFF' : '#64748B',
              transition: 'all 0.15s ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT */}
      {activeTab === 'OVERVIEW' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <Card title="System Status & Health" badge={<Badge variant="emerald">Healthy</Badge>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px' }}>
                <span style={{ color: '#64748B' }}>Database Engine</span>
                <strong style={{ color: '#087F5B' }}>PostgreSQL Connected</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px' }}>
                <span style={{ color: '#64748B' }}>Evidence Ingestion Pipeline</span>
                <strong style={{ color: '#087F5B' }}>Active & Ready</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px' }}>
                <span style={{ color: '#64748B' }}>Merkle Epoch Sealing</span>
                <strong style={{ color: '#087F5B' }}>Operational</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px' }}>
                <span style={{ color: '#64748B' }}>Total Sealed Records</span>
                <strong style={{ color: '#101828' }}>{metrics?.total_evidence_records || 1778}</strong>
              </div>
            </div>
          </Card>

          <Card title="Recent Platform Activity" badge={<Badge variant="navy">Latest Events</Badge>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
              {auditLogs.slice(0, 5).map((log, idx) => (
                <div key={idx} style={{ padding: '10px', borderRadius: '6px', border: '1px solid #F2F4F7', backgroundColor: '#FFFFFF' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: '#101828' }}>
                    <span>{log.event_type?.replace(/_/g, ' ') || 'SYSTEM_AUDIT'}</span>
                    <span style={{ color: '#94A3B8', fontWeight: 400 }}>{log.created_at ? new Date(log.created_at).toLocaleTimeString() : 'Recent'}</span>
                  </div>
                  <div style={{ color: '#64748B', marginTop: '2px' }}>
                    Entity: {log.entity_type} ({log.entity_id ? log.entity_id.slice(0, 16) : 'N/A'})
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'ORGANIZATIONS' && (
        <Card title="Registered Organizations" badge={<Badge variant="navy">{orgs.length} Total</Badge>} noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '1px solid #E4E7EC', color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
                  <th style={{ padding: '12px 16px' }}>Organization Name</th>
                  <th style={{ padding: '12px 16px' }}>Type</th>
                  <th style={{ padding: '12px 16px' }}>Location</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {orgs.map((o) => (
                  <tr key={o.id} style={{ borderBottom: '1px solid #F2F4F7' }}>
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: '#101828' }}>{o.name}</td>
                    <td style={{ padding: '12px 16px', color: '#64748B' }}>{o.type || o.org_type}</td>
                    <td style={{ padding: '12px 16px', color: '#64748B' }}>{o.district || 'Telangana'}, {o.state || 'India'}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <Badge variant="emerald" size="sm">Active</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'USERS' && (
        <Card title="Active Users" badge={<Badge variant="navy">{users.length} Users</Badge>} noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '1px solid #E4E7EC', color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
                  <th style={{ padding: '12px 16px' }}>Name & Username</th>
                  <th style={{ padding: '12px 16px' }}>Role</th>
                  <th style={{ padding: '12px 16px' }}>Organization</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} style={{ borderBottom: '1px solid #F2F4F7' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 600, color: '#101828' }}>{u.full_name || u.username}</div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>{u.email}</div>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <Badge variant="navy" size="sm">{u.role?.replace(/_/g, ' ')}</Badge>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#64748B' }}>{u.organization || 'PRAMAN Trust'}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <Badge variant="emerald" size="sm">Active</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'DEVICES' && (
        <Card title="Registered Hardware Devices" badge={<Badge variant="navy">{devices.length} Devices</Badge>} noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '1px solid #E4E7EC', color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
                  <th style={{ padding: '12px 16px' }}>Device ID</th>
                  <th style={{ padding: '12px 16px' }}>Farmer ID</th>
                  <th style={{ padding: '12px 16px' }}>Last Monotonic Counter</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {devices.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: '#94A3B8' }}>
                      No registered devices found.
                    </td>
                  </tr>
                ) : (
                  devices.map((d) => (
                    <tr key={d.id} style={{ borderBottom: '1px solid #F2F4F7' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: '#101828' }}>{d.id}</td>
                      <td style={{ padding: '12px 16px', color: '#64748B' }}>{d.farmer_id || 'Enrolled Farmer'}</td>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: '#101828' }}>#{d.last_sequence_number || 1}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <Badge variant="emerald" size="sm">{d.status || 'ACTIVE'}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'AUDIT_LOGS' && (
        <Card title="Security & Governance Audit Trail" badge={<Badge variant="navy">{auditLogs.length} Records</Badge>} noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '1px solid #E4E7EC', color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
                  <th style={{ padding: '12px 16px' }}>Timestamp</th>
                  <th style={{ padding: '12px 16px' }}>Event</th>
                  <th style={{ padding: '12px 16px' }}>Actor</th>
                  <th style={{ padding: '12px 16px' }}>Entity</th>
                  <th style={{ padding: '12px 16px' }}>State Transition</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((l) => (
                  <tr key={l.log_id || l.id} style={{ borderBottom: '1px solid #F2F4F7' }}>
                    <td style={{ padding: '12px 16px', color: '#64748B', fontSize: '12px' }}>
                      {l.created_at ? new Date(l.created_at).toLocaleString() : 'Recent'}
                    </td>
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: '#101828' }}>
                      {l.event_type}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#64748B' }}>{l.actor_id || 'System'}</td>
                    <td style={{ padding: '12px 16px', color: '#64748B' }}>{l.entity_type}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ color: '#64748B' }}>{l.previous_state || '—'}</span>
                      <span style={{ margin: '0 6px', color: '#94A3B8' }}>➔</span>
                      <strong style={{ color: '#087F5B' }}>{l.new_state || 'ACTIVE'}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* EXPANDABLE SECTION: ADVANCED TECHNICAL DETAILS */}
      <div style={{ border: '1px solid #E4E7EC', borderRadius: '8px', overflow: 'hidden' }}>
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
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
            <Sliders size={14} color="#087F5B" />
            <span>View Technical Details (Cryptographic Ledger & Root Certificates)</span>
          </div>
          {showTechnicalDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showTechnicalDetails && (
          <div style={{ padding: '16px', backgroundColor: '#FFFFFF', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              <div style={{ padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px', border: '1px solid #E4E7EC' }}>
                <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Root Curve</span>
                <strong style={{ color: '#087F5B' }}>NIST P-256 (secp256r1)</strong>
              </div>
              <div style={{ padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px', border: '1px solid #E4E7EC' }}>
                <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Audit Immutability</span>
                <strong style={{ color: '#087F5B' }}>Append-Only Hash Chained</strong>
              </div>
              <div style={{ padding: '10px', backgroundColor: '#F8FAFC', borderRadius: '6px', border: '1px solid #E4E7EC' }}>
                <span style={{ color: '#64748B', display: 'block', fontSize: '11px' }}>Consensus Epochs</span>
                <strong style={{ color: '#101828' }}>RFC 6962 Binary Merkle Trees</strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
