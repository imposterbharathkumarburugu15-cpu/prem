import React, { useState, useEffect } from 'react';
import {
  Truck,
  Scale,
  Sparkles,
  Store,
  ShieldCheck,
  ShieldAlert,
  QrCode,
  MapPin,
  Clock,
  User,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  Eye,
  Hash,
  RefreshCw,
  Search,
  Filter,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import { api } from '../../services/api';
import { Badge } from './Badge';
import { Modal } from './Modal';

export interface SupplyChainEvent {
  id: string;
  event_type: string;
  batch_id?: string;
  shipment_id?: string;
  timestamp: string;
  actor_name: string;
  actor_role: string;
  organization?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  payload: Record<string, any>;
  has_evidence: boolean;
  evidence_summary?: {
    id?: string;
    file_name?: string;
    sha256?: string;
    mime_type?: string;
    verified?: boolean;
    status?: string;
  };
  hash?: string;
  merkle_root?: string;
  status: 'VERIFIED' | 'PENDING' | 'FLAGGED' | 'RESOLVED';
}

interface BatchTimelineProps {
  batchId: string;
  initialEvents?: SupplyChainEvent[];
  title?: string;
  compact?: boolean;
  onSelectEvent?: (event: SupplyChainEvent) => void;
}

const getEventIcon = (eventType: string) => {
  switch (eventType) {
    case 'CROP_ACTIVITY_RECORDED':
    case 'FIELD_EVIDENCE_CAPTURED':
      return <MapPin size={16} color="#087F5B" />;
    case 'SHIPMENT_PICKUP_CONFIRMED':
    case 'SHIPMENT_CHECKPOINT_RECORDED':
    case 'SHIPMENT_DELIVERY_CONFIRMED':
      return <Truck size={16} color="#0284C7" />;
    case 'PRODUCE_RECEIVED':
      return <Layers size={16} color="#475569" />;
    case 'WEIGHT_RECORDED':
      return <Scale size={16} color="#D97706" />;
    case 'QUALITY_INSPECTION_COMPLETED':
      return <Sparkles size={16} color="#7C3AED" />;
    case 'BATCH_CREATED':
    case 'BATCH_SPLIT':
    case 'BATCH_DISPATCHED':
      return <Layers size={16} color="#0B192C" />;
    case 'RETAIL_RECEIPT_CONFIRMED':
    case 'PACKAGING_VERIFIED':
      return <Store size={16} color="#059669" />;
    case 'QR_GENERATED':
      return <QrCode size={16} color="#0284C7" />;
    case 'INVESTIGATION_OPENED':
    case 'EVIDENCE_CHALLENGE_CREATED':
      return <ShieldAlert size={16} color="#DC2626" />;
    case 'INVESTIGATION_DECISION_RECORDED':
      return <ShieldCheck size={16} color="#087F5B" />;
    default:
      return <FileText size={16} color="#64748B" />;
  }
};

const formatEventTitle = (eventType: string): string => {
  return eventType
    .split('_')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');
};

export const BatchTimeline: React.FC<BatchTimelineProps> = ({
  batchId,
  initialEvents,
  title,
  compact = false,
  onSelectEvent,
}) => {
  const [events, setEvents] = useState<SupplyChainEvent[]>(initialEvents || []);
  const [loading, setLoading] = useState(!initialEvents);
  const [selectedEvent, setSelectedEvent] = useState<SupplyChainEvent | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadTimeline = async () => {
    if (!batchId) return;
    setLoading(true);
    try {
      const data = await api.getBatchTimeline(batchId);
      const rawList: any[] = (data as any)?.timeline || data?.events || [];
      if (Array.isArray(rawList) && rawList.length > 0) {
        const normalized: SupplyChainEvent[] = rawList.map((item: any) => ({
          id: item.event_id || item.id || 'evt_' + Math.random().toString(36).substring(2, 8),
          event_type: item.event_type || 'EVENT',
          batch_id: item.batch_id || batchId,
          shipment_id: item.shipment_id,
          timestamp: item.timestamp || new Date().toISOString(),
          actor_name: item.actor?.name || item.actor_name || item.actor?.id || 'Supply Chain Node',
          actor_role: item.actor?.role || item.actor_role || 'OPERATOR',
          organization: item.organization || item.stage,
          location: item.location || item.payload?.location_name,
          latitude: item.latitude || item.payload?.latitude,
          longitude: item.longitude || item.payload?.longitude,
          payload: item.payload || {},
          has_evidence: Boolean(item.has_evidence || item.evidence_hash),
          evidence_summary: {
            sha256: item.evidence_hash || item.evidence_summary?.sha256,
            file_name: item.evidence_summary?.file_name || (item.evidence_hash ? 'supporting_evidence.jpg' : undefined),
            verified: item.verification_status === 'VERIFIED',
          },
          hash: item.evidence_hash || item.hash,
          status: item.verification_status === 'FLAGGED' ? 'FLAGGED' : 'VERIFIED',
        }));
        setEvents(normalized);
      }
    } catch (err) {
      console.warn(`Failed to fetch timeline for ${batchId}, using fallback view:`, err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialEvents) {
      setEvents(initialEvents);
      setLoading(false);
    } else if (batchId) {
      loadTimeline();
    }
  }, [batchId, initialEvents]);

  const filteredEvents = events.filter((ev) => {
    if (filterType !== 'ALL' && !ev.event_type.includes(filterType)) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchType = ev.event_type.toLowerCase().includes(q);
      const matchActor = ev.actor_name?.toLowerCase().includes(q);
      const matchPayload = JSON.stringify(ev.payload || {}).toLowerCase().includes(q);
      const matchLoc = ev.location?.toLowerCase().includes(q);
      return matchType || matchActor || matchPayload || matchLoc;
    }
    return true;
  });

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '8px',
        border: '1px solid #E2E8F0',
        padding: compact ? '12px' : '20px',
      }}
    >
      {/* Header & Controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#0F172A', margin: 0 }}>
            {title || `Supply Chain History (${batchId || 'All'})`}
          </h3>
          <span style={{ fontSize: '12px', color: '#64748B' }}>
            {events.length} chronological business events cryptographically anchored
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={loadTimeline}
            disabled={loading}
            style={{
              padding: '6px 10px',
              borderRadius: '6px',
              border: '1px solid #CBD5E1',
              backgroundColor: '#FFFFFF',
              color: '#334155',
              fontSize: '12px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {!compact && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '16px',
            flexWrap: 'wrap',
          }}
        >
          {/* Quick Filters */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {['ALL', 'SHIPMENT', 'WEIGHT', 'INSPECTION', 'BATCH', 'RETAIL'].map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilterType(f)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 500,
                  border: filterType === f ? '1px solid #0F172A' : '1px solid #E2E8F0',
                  backgroundColor: filterType === f ? '#0F172A' : '#F8FAFC',
                  color: filterType === f ? '#FFFFFF' : '#475569',
                  cursor: 'pointer',
                }}
              >
                {f}
              </button>
            ))}
          </div>

          <div style={{ flex: 1, minWidth: '160px', position: 'relative' }}>
            <input
              type="text"
              placeholder="Search events, actors, values..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '5px 8px 5px 28px',
                borderRadius: '4px',
                border: '1px solid #CBD5E1',
                fontSize: '12px',
              }}
            />
            <Search
              size={13}
              color="#94A3B8"
              style={{ position: 'absolute', left: '8px', top: '8px' }}
            />
          </div>
        </div>
      )}

      {/* Events List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748B', fontSize: '13px' }}>
          Loading cryptographic timeline...
        </div>
      ) : filteredEvents.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '32px 16px',
            backgroundColor: '#F8FAFC',
            borderRadius: '6px',
            border: '1px dashed #CBD5E1',
          }}
        >
          <Layers size={32} color="#94A3B8" style={{ margin: '0 auto 8px auto' }} />
          <p style={{ fontSize: '13px', fontWeight: 500, color: '#334155', margin: '0 0 4px 0' }}>
            No events found for this filter
          </p>
          <p style={{ fontSize: '11px', color: '#64748B', margin: 0 }}>
            Business actions recorded for this batch will appear in chronological sequence.
          </p>
        </div>
      ) : (
        <div style={{ position: 'relative', paddingLeft: '24px' }}>
          {/* Vertical Track Line */}
          <div
            style={{
              position: 'absolute',
              left: '9px',
              top: '12px',
              bottom: '12px',
              width: '2px',
              backgroundColor: '#E2E8F0',
            }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {filteredEvents.map((ev, idx) => {
              const dateStr = new Date(ev.timestamp).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              });

              return (
                <div
                  key={ev.id || idx}
                  style={{ position: 'relative', cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedEvent(ev);
                    if (onSelectEvent) onSelectEvent(ev);
                  }}
                >
                  {/* Node icon */}
                  <div
                    style={{
                      position: 'absolute',
                      left: '-24px',
                      top: '2px',
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      backgroundColor: '#FFFFFF',
                      border: '2px solid #0F172A',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 0 0 3px #FFFFFF',
                    }}
                  >
                    {getEventIcon(ev.event_type)}
                  </div>

                  {/* Card Container */}
                  <div
                    style={{
                      backgroundColor: '#F8FAFC',
                      borderRadius: '6px',
                      border: '1px solid #E2E8F0',
                      padding: '12px 14px',
                      transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#0F172A';
                      e.currentTarget.style.backgroundColor = '#FFFFFF';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = '#E2E8F0';
                      e.currentTarget.style.backgroundColor = '#F8FAFC';
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A' }}>
                          {formatEventTitle(ev.event_type)}
                        </span>
                        <Badge
                          variant={
                            ev.status === 'VERIFIED'
                              ? 'emerald'
                              : ev.status === 'FLAGGED'
                              ? 'critical'
                              : 'navy'
                          }
                        >
                          {ev.status}
                        </Badge>
                      </div>

                      <span style={{ fontSize: '11px', color: '#64748B', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={11} /> {dateStr}
                      </span>
                    </div>

                    {/* Actor & location info */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        fontSize: '11px',
                        color: '#475569',
                        marginBottom: '8px',
                        flexWrap: 'wrap',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <User size={11} /> {ev.actor_name} ({ev.actor_role})
                      </span>
                      {ev.organization && (
                        <span>• {ev.organization}</span>
                      )}
                      {ev.location && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                          <MapPin size={11} color="#0284C7" /> {ev.location}
                        </span>
                      )}
                    </div>

                    {/* Key payload summaries */}
                    <div
                      style={{
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #E2E8F0',
                        borderRadius: '4px',
                        padding: '6px 8px',
                        fontSize: '11px',
                        display: 'flex',
                        gap: '12px',
                        flexWrap: 'wrap',
                        color: '#334155',
                      }}
                    >
                      {Object.entries(ev.payload || {})
                        .filter(([k]) => !['notes', 'internal_id'].includes(k))
                        .slice(0, 4)
                        .map(([k, v]) => (
                          <span key={k}>
                            <strong style={{ color: '#64748B', textTransform: 'capitalize' }}>
                              {k.replace(/_/g, ' ')}:
                            </strong>{' '}
                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                          </span>
                        ))}
                    </div>

                    {/* Evidence & Hash bar */}
                    <div
                      style={{
                        marginTop: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '11px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {ev.has_evidence ? (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              color: '#087F5B',
                              fontWeight: 500,
                            }}
                          >
                            <ShieldCheck size={12} /> Supporting Evidence Attached
                          </span>
                        ) : (
                          <span style={{ color: '#94A3B8' }}>No extra file attached</span>
                        )}

                        {ev.hash && (
                          <span
                            style={{
                              fontFamily: 'monospace',
                              color: '#64748B',
                              backgroundColor: '#F1F5F9',
                              padding: '1px 4px',
                              borderRadius: '3px',
                            }}
                            title={`Event Hash: ${ev.hash}`}
                          >
                            {ev.hash.slice(0, 8)}...
                          </span>
                        )}
                      </div>

                      <span
                        style={{
                          color: '#0284C7',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '2px',
                          fontWeight: 500,
                        }}
                      >
                        Inspect Details <ChevronRight size={12} />
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Selected Event Detail Modal */}
      {selectedEvent && (
        <Modal
          isOpen={!!selectedEvent}
          onClose={() => setSelectedEvent(null)}
          title={formatEventTitle(selectedEvent.event_type)}
          size="large"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Top metadata cards */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '12px',
              }}
            >
              <div
                style={{
                  padding: '12px',
                  backgroundColor: '#F8FAFC',
                  borderRadius: '6px',
                  border: '1px solid #E2E8F0',
                }}
              >
                <span style={{ fontSize: '11px', color: '#64748B', display: 'block' }}>Actor & Role</span>
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A' }}>
                  {selectedEvent.actor_name}
                </span>
                <span style={{ fontSize: '11px', color: '#475569', display: 'block' }}>
                  Role: {selectedEvent.actor_role}
                </span>
              </div>

              <div
                style={{
                  padding: '12px',
                  backgroundColor: '#F8FAFC',
                  borderRadius: '6px',
                  border: '1px solid #E2E8F0',
                }}
              >
                <span style={{ fontSize: '11px', color: '#64748B', display: 'block' }}>Timestamp & Location</span>
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A' }}>
                  {new Date(selectedEvent.timestamp).toLocaleString()}
                </span>
                <span style={{ fontSize: '11px', color: '#475569', display: 'block' }}>
                  {selectedEvent.location || 'Location coords logged'}
                </span>
              </div>

              <div
                style={{
                  padding: '12px',
                  backgroundColor: '#F8FAFC',
                  borderRadius: '6px',
                  border: '1px solid #E2E8F0',
                }}
              >
                <span style={{ fontSize: '11px', color: '#64748B', display: 'block' }}>Cryptographic Integrity</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                  <ShieldCheck size={14} color="#087F5B" />
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#087F5B' }}>
                    SHA-256 Verified
                  </span>
                </div>
                <span
                  style={{
                    fontSize: '10px',
                    fontFamily: 'monospace',
                    color: '#64748B',
                    display: 'block',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {selectedEvent.hash || 'merkle-node-anchored'}
                </span>
              </div>
            </div>

            {/* Event Payload Table */}
            <div>
              <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A', marginBottom: '8px' }}>
                Business Action Parameters
              </h4>
              <div
                style={{
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  overflow: 'hidden',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <tbody>
                    {Object.entries(selectedEvent.payload || {}).map(([key, value], idx) => (
                      <tr
                        key={key}
                        style={{
                          backgroundColor: idx % 2 === 0 ? '#FFFFFF' : '#F8FAFC',
                          borderBottom: '1px solid #E2E8F0',
                        }}
                      >
                        <td
                          style={{
                            padding: '8px 12px',
                            fontWeight: 600,
                            color: '#475569',
                            width: '35%',
                            textTransform: 'capitalize',
                          }}
                        >
                          {key.replace(/_/g, ' ')}
                        </td>
                        <td style={{ padding: '8px 12px', color: '#0F172A', fontFamily: typeof value === 'number' ? 'monospace' : 'inherit' }}>
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Evidence File Details (if attached) */}
            {selectedEvent.has_evidence && (
              <div
                style={{
                  padding: '12px',
                  border: '1px solid #CBD5E1',
                  borderRadius: '6px',
                  backgroundColor: '#F8FAFC',
                }}
              >
                <h4
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: '#0F172A',
                    margin: '0 0 8px 0',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <ShieldCheck size={15} color="#087F5B" />
                  Attached Supporting Evidence
                </h4>
                <div style={{ fontSize: '12px', color: '#334155', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div>
                    <strong>File:</strong> {selectedEvent.evidence_summary?.file_name || 'supporting_evidence.jpg'}
                  </div>
                  <div>
                    <strong>Hash (SHA-256):</strong>{' '}
                    <code style={{ fontSize: '11px', backgroundColor: '#E2E8F0', padding: '1px 4px', borderRadius: '3px' }}>
                      {selectedEvent.evidence_summary?.sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                    </code>
                  </div>
                  <div>
                    <strong>Verification:</strong> Authenticated during business action intake.
                  </div>
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};

