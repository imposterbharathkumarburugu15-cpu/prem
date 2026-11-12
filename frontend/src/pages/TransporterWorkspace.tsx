import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Truck,
  MapPin,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Clock,
  ArrowRight,
  ShieldCheck,
  FileText,
  Activity,
  Layers,
  Gauge,
  Lock,
  Plus,
  Send,
  Eye,
  Camera,
  Navigation,
  Thermometer,
  Droplets,
  AlertOctagon,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { StatMetric } from '../components/common/StatMetric';
import { Modal } from '../components/common/Modal';
import { MultiStepForm, FormStep } from '../components/common/MultiStepForm';
import {
  ContextualEvidenceCapture,
  EvidenceMetadata,
} from '../components/common/ContextualEvidenceCapture';
import { BatchTimeline } from '../components/common/BatchTimeline';

export const TransporterWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'HANDOVER_WIZARD' | 'CHECKPOINT' | 'INCIDENT' | 'HISTORY'>('OVERVIEW');
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Shipments state
  const [shipments, setShipments] = useState<any[]>([
    {
      id: 'shp-001',
      shipment_code: 'SHP-TEL-2026-089',
      driver_id: 'drv_ramesh_01',
      driver_name: 'Ramesh Kumar',
      vehicle_reg: 'TS-08-UB-4912',
      origin_name: 'Adilabad Cluster Gate #2',
      destination_name: 'Adilabad Central Collection Dock',
      stage: 'ASSIGNED',
      status: 'ACTIVE',
      odometer_km: 45210,
      seal_number: 'SEAL-TX-8821',
      pickup_timestamp: null,
      delivery_timestamp: null,
      created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
      items: [
        {
          batch_id: 'batch-f-01',
          batch_code: 'BATCH-TEL-KRM-2026-001',
          crop_type: 'Organic Cotton',
          declared_quantity: 1250,
          unit: 'kg',
        },
      ],
    },
    {
      id: 'shp-002',
      shipment_code: 'SHP-TEL-2026-092',
      driver_id: 'drv_anand_02',
      driver_name: 'Anand Reddy',
      vehicle_reg: 'TS-07-EK-8114',
      origin_name: 'Warangal South Mandi Depot',
      destination_name: 'Hyderabad Apex Supermarket Hub',
      stage: 'IN_TRANSIT',
      status: 'ACTIVE',
      odometer_km: 78420,
      seal_number: 'SEAL-TX-9014',
      pickup_timestamp: new Date(Date.now() - 3600000 * 8).toISOString(),
      delivery_timestamp: null,
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
      items: [
        {
          batch_id: 'batch-f-02',
          batch_code: 'BATCH-TEL-WRG-2026-042',
          crop_type: 'Basmati Rice',
          declared_quantity: 2800,
          unit: 'kg',
        },
      ],
    },
    {
      id: 'shp-003',
      shipment_code: 'SHP-TEL-2026-077',
      driver_id: 'drv_ramesh_01',
      driver_name: 'Ramesh Kumar',
      vehicle_reg: 'TS-08-UB-4912',
      origin_name: 'Khammam Farm Gate #1',
      destination_name: 'Khammam Central Processing Hub',
      stage: 'DELIVERED',
      status: 'COMPLETED',
      odometer_km: 44980,
      seal_number: 'SEAL-TX-7731',
      pickup_timestamp: new Date(Date.now() - 86400000 * 2).toISOString(),
      delivery_timestamp: new Date(Date.now() - 86400000 * 1).toISOString(),
      created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      items: [
        {
          batch_id: 'batch-f-03',
          batch_code: 'BATCH-TEL-KHM-2026-088',
          crop_type: 'Red Chilli',
          declared_quantity: 850,
          unit: 'kg',
        },
      ],
    },
  ]);

  const [selectedShipment, setSelectedShipment] = useState<any>(shipments[0]);
  const [timelineBatchCode, setTimelineBatchCode] = useState<string | null>(null);

  // -------------------------------------------------------------
  // 5-STEP HANDOVER WORKFLOW STATE
  // -------------------------------------------------------------
  const [handoverStep, setHandoverStep] = useState<number>(0);
  const [handoverSubmitting, setHandoverSubmitting] = useState<boolean>(false);

  // Step 0: Selection
  const [wizardShipmentId, setWizardShipmentId] = useState<string>(shipments[0].id);

  // Step 1: Pickup Info
  const [vehicleReg, setVehicleReg] = useState('TS-08-UB-4912');
  const [driverName, setDriverName] = useState('Ramesh Kumar');
  const [driverId, setDriverId] = useState('DRV-TEL-991');
  const [odometerKm, setOdometerKm] = useState('45210');
  const [sealNumber, setSealNumber] = useState('SEAL-TX-8821');
  const [pickupTimestamp, setPickupTimestamp] = useState(new Date().toISOString().substring(0, 16));

  // Step 2: Evidence Capture
  const [handoverEvidence, setHandoverEvidence] = useState<{
    file: File | null;
    metadata: EvidenceMetadata | null;
  }>({ file: null, metadata: null });

  // Step 3: Delivery Info
  const [destinationHub, setDestinationHub] = useState('Adilabad Central Collection Dock');
  const [etaTimestamp, setEtaTimestamp] = useState(new Date(Date.now() + 3600000 * 4).toISOString().substring(0, 16));
  const [receivingContact, setReceivingContact] = useState('Suresh Verma (Dock Lead)');
  const [receivingContactPhone, setReceivingContactPhone] = useState('+91 98480 22334');
  const [cargoCondition, setCargoCondition] = useState('SEALED_INTACT');

  // Checkpoint & Incident form states
  const [checkpointLocation, setCheckpointLocation] = useState('Highway Toll Plaza NH44 - Medchal');
  const [checkpointLat, setCheckpointLat] = useState('17.6297');
  const [checkpointLon, setCheckpointLon] = useState('78.4814');
  const [tempCelsius, setTempCelsius] = useState('24.5');
  const [humidityPct, setHumidityPct] = useState('58');
  const [checkpointCondition, setCheckpointCondition] = useState('NORMAL_IN_TRANSIT');
  const [checkpointSubmitting, setCheckpointSubmitting] = useState(false);

  const [incidentType, setIncidentType] = useState('SEAL_TAMPER_SUSPICION');
  const [incidentSeverity, setIncidentSeverity] = useState('HIGH');
  const [delayHours, setDelayHours] = useState('2.0');
  const [incidentNotes, setIncidentNotes] = useState('Tamper-evident seal was found altered during inspection at weigh checkpost.');
  const [incidentSubmitting, setIncidentSubmitting] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const res = await api.getTransporterDashboard();
      if (res && res.shipments && res.shipments.length > 0) {
        setShipments(res.shipments);
        if (!selectedShipment) {
          setSelectedShipment(res.shipments[0]);
          setWizardShipmentId(res.shipments[0].id);
        }
      }
      setData(res);
    } catch (e) {
      console.warn('Transporter dashboard endpoint fallback:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const wizardShipment = shipments.find((s) => s.id === wizardShipmentId) || shipments[0];

  const handoverSteps: FormStep[] = [
    { id: 0, label: 'Shipment Select', description: 'Assigned produce batch' },
    { id: 1, label: 'Pickup & Vehicle', description: 'Driver, odometer & seal' },
    { id: 2, label: 'Evidence Capture', description: 'Dock & loading photo' },
    { id: 3, label: 'Delivery & Route', description: 'Destination hub & contact' },
    { id: 4, label: 'Review & Sign', description: 'Cryptographic commitment' },
  ];

  // Submit Handover (Pickup directly delivers cargo to Collection Centre dock)
  const handleHandoverSubmit = async () => {
    setHandoverSubmitting(true);
    setActionMsg(null);
    try {
      const isPickupMode = wizardShipment.stage === 'ASSIGNED';

      // 1. If currently ASSIGNED, first record pickup event
      if (isPickupMode) {
        try {
          await api.recordBusinessEvent({
            event_type: 'SHIPMENT_PICKUP_CONFIRMED',
            shipment_id: wizardShipment.id,
            batch_id: wizardShipment.items?.[0]?.batch_id,
            payload: {
              shipment_id: wizardShipment.id,
              vehicle_reg: vehicleReg,
              driver_name: driverName,
              driver_id: driverId,
              odometer_km: parseFloat(odometerKm) || 45210,
              seal_number: sealNumber,
              pickup_timestamp: pickupTimestamp,
              destination_name: destinationHub,
              condition: cargoCondition,
              notes: `Farm gate pickup attested by ${driverName} (${vehicleReg}).`,
            },
            notes: `Transporter Origin Pickup: ${wizardShipment.shipment_code}`,
          });
        } catch (pickupErr) {
          console.warn('Pickup intermediate event note:', pickupErr);
        }
      }

      // 2. Record Delivery event (transitions directly to DELIVERED for Collection Centre intake)
      await api.recordBusinessEvent({
        event_type: 'SHIPMENT_DELIVERY_CONFIRMED',
        shipment_id: wizardShipment.id,
        batch_id: wizardShipment.items?.[0]?.batch_id,
        payload: {
          shipment_id: wizardShipment.id,
          vehicle_reg: vehicleReg,
          driver_name: driverName,
          driver_id: driverId,
          odometer_km: (parseFloat(odometerKm) || 45210) + 85,
          seal_number: sealNumber,
          pickup_timestamp: pickupTimestamp,
          delivery_timestamp: new Date().toISOString(),
          destination_name: destinationHub,
          delivered_quantity: wizardShipment.items?.[0]?.declared_quantity || 1000,
          condition: cargoCondition,
          notes: `Delivered and offloaded at ${destinationHub}. Custody transferred to Collection Centre dock.`,
        },
        evidence_file: handoverEvidence.file,
        evidence_metadata: handoverEvidence.metadata,
        notes: `Transporter Delivery: ${wizardShipment.shipment_code} delivered to ${destinationHub}`,
      });

      // Update local shipment state
      setShipments((prev) =>
        prev.map((s) => {
          if (s.id === wizardShipment.id) {
            return {
              ...s,
              stage: 'DELIVERED',
              vehicle_reg: vehicleReg,
              driver_name: driverName,
              status: 'COMPLETED',
              destination_name: destinationHub,
            };
          }
          return s;
        })
      );

      setActionMsg({
        type: 'success',
        text: `Shipment ${wizardShipment.shipment_code} has been delivered to ${destinationHub}! It is now available at the Collection Centre dock ready for intake and weighing.`,
      });
      setHandoverStep(0);
      setActiveTab('OVERVIEW');
      await fetchDashboardData();
    } catch (err: any) {
      console.error('Handover error:', err);
      setActionMsg({
        type: 'error',
        text: `Handover failed: ${err.message || 'Server error'}`,
      });
    } finally {
      setHandoverSubmitting(false);
    }
  };

  // Submit Checkpoint
  const handleRecordCheckpoint = async () => {
    if (!selectedShipment) return;
    setCheckpointSubmitting(true);
    setActionMsg(null);
    try {
      await api.recordBusinessEvent({
        event_type: 'SHIPMENT_CHECKPOINT_RECORDED',
        shipment_id: selectedShipment.id,
        payload: {
          shipment_id: selectedShipment.id,
          location_name: checkpointLocation,
          latitude: parseFloat(checkpointLat) || 17.6297,
          longitude: parseFloat(checkpointLon) || 78.4814,
          temperature_celsius: parseFloat(tempCelsius) || 24.5,
          humidity_pct: parseFloat(humidityPct) || 58.0,
          condition: checkpointCondition,
          notes: `Logged via Transporter console at ${checkpointLocation}`,
        },
      });

      setActionMsg({
        type: 'success',
        text: `Transit checkpoint at '${checkpointLocation}' logged with telemetry!`,
      });
      setActiveTab('OVERVIEW');
    } catch (err: any) {
      setActionMsg({
        type: 'error',
        text: `Checkpoint failed: ${err.message || 'Error'}`,
      });
    } finally {
      setCheckpointSubmitting(false);
    }
  };

  // Submit Transit Incident
  const handleReportIncident = async () => {
    if (!selectedShipment) return;
    setIncidentSubmitting(true);
    setActionMsg(null);
    try {
      await api.recordBusinessEvent({
        event_type: 'SHIPMENT_CHECKPOINT_RECORDED',
        shipment_id: selectedShipment.id,
        payload: {
          shipment_id: selectedShipment.id,
          location_name: 'Transit Incident Checkpoint',
          condition: 'INCIDENT_FLAGGED',
          incident_type: incidentType,
          severity: incidentSeverity,
          delay_hours: parseFloat(delayHours) || 0,
          notes: `[TRANSIT INCIDENT] ${incidentType}: ${incidentNotes}`,
        },
      });

      setShipments((prev) =>
        prev.map((s) => (s.id === selectedShipment.id ? { ...s, stage: 'INCIDENT_FLAGGED' } : s))
      );

      setActionMsg({
        type: 'success',
        text: `Transit incident flagged and dispatched to Evidence Integrity Officer queue!`,
      });
      setActiveTab('OVERVIEW');
    } catch (err: any) {
      setActionMsg({
        type: 'error',
        text: `Incident reporting failed: ${err.message || 'Error'}`,
      });
    } finally {
      setIncidentSubmitting(false);
    }
  };

  const handleQuickDispatchShipment = async () => {
    try {
      setLoading(true);
      const res = await api.createTransporterShipment({
        batch_code: 'BATCH-2026-001',
        crop_type: 'Organic Shankar-6 Cotton',
        declared_quantity: 1000,
        driver_name: 'Ramesh Kumar',
        vehicle_reg: 'TS-08-UB-4912',
        origin_name: 'Adilabad Cluster Gate #2',
        destination_name: 'Adilabad Central Collection Dock',
      });
      setActionMsg({
        type: 'success',
        text: `New pickup consignment ${res.shipment_code} created and assigned! You can now start the 5-step handover.`,
      });
      await fetchDashboardData();
    } catch (e: any) {
      setActionMsg({ type: 'error', text: `Failed to dispatch shipment: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto', paddingBottom: '48px' }}>
      {/* HEADER SECTION */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', background: 'linear-gradient(135deg, #1B4332 0%, #2D6A4F 100%)', borderRadius: '12px', padding: '24px 28px', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(27, 67, 50, 0.15)' }}>
        <div style={{ maxWidth: '640px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)', padding: '4px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <Truck size={14} />
              Transporter Logistics Command
            </span>
            <span style={{ fontSize: '12px', color: '#B7E4C7' }}>• తెలంగాణ సరుకు రవాణా పర్యవేక్షణ</span>
          </div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>
            Transporter Handover & Logistics Workspace
          </h1>
          <p style={{ fontSize: '14px', margin: 0, color: '#D8F3DC', lineHeight: 1.5 }}>
            Execute secure produce handovers, log GPS waypoints, capture tamper-evident seal evidence, and digitally sign transit custody checkpoints.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            onClick={() => {
              setHandoverStep(0);
              setActiveTab('HANDOVER_WIZARD');
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#52B788',
              color: '#081C15',
              padding: '11px 20px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
              transition: 'all 0.15s ease',
            }}
          >
            <Plus size={16} />
            <span>Start Handover Workflow</span>
          </button>
        </div>
      </div>

      {/* TOAST MESSAGE */}
      {actionMsg && (
        <div
          style={{
            padding: '12px 18px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: actionMsg.type === 'success' ? '#EDFDF2' : '#FEF3F2',
            color: actionMsg.type === 'success' ? '#1B4332' : '#B42318',
            border: `1px solid ${actionMsg.type === 'success' ? '#B7E4C7' : '#FECDCA'}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {actionMsg.type === 'success' ? <CheckCircle2 size={16} color="#2D6A4F" /> : <AlertTriangle size={16} color="#D92D20" />}
            <span>{actionMsg.text}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {actionMsg.type === 'success' && (
              <button
                type="button"
                onClick={() => navigate('/centre')}
                style={{
                  backgroundColor: '#1B4332',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '5px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
              >
                Open Collection Centre <ArrowRight size={13} />
              </button>
            )}
            <button
              onClick={() => setActionMsg(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 600 }}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* NAVIGATION TABS */}
      <div style={{ display: 'flex', gap: '6px', borderBottom: '1px solid #E2E8F0', paddingBottom: '2px' }}>
        {[
          { id: 'OVERVIEW', label: 'Fleet & Active Shipments', icon: Truck },
          { id: 'HANDOVER_WIZARD', label: '5-Step Handover Workflow', icon: ShieldCheck },
          { id: 'CHECKPOINT', label: 'Log Waypoint Checkpoint', icon: MapPin },
          { id: 'INCIDENT', label: 'Report Transit Incident', icon: AlertOctagon },
          { id: 'HISTORY', label: 'Delivery History', icon: Clock },
        ].map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
          const handleQuickDispatchShipment = async () => {
    try {
      setLoading(true);
      const res = await api.createTransporterShipment({
        batch_code: 'BATCH-2026-001',
        crop_type: 'Organic Shankar-6 Cotton',
        declared_quantity: 1000,
        driver_name: 'Ramesh Kumar',
        vehicle_reg: 'TS-08-UB-4912',
        origin_name: 'Adilabad Cluster Gate #2',
        destination_name: 'Adilabad Central Collection Dock',
      });
      setActionMsg({
        type: 'success',
        text: `New pickup consignment ${res.shipment_code} created and assigned! You can now start the 5-step handover.`,
      });
      await fetchDashboardData();
    } catch (e: any) {
      setActionMsg({ type: 'error', text: `Failed to dispatch shipment: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                borderRadius: '8px 8px 0 0',
                border: 'none',
                borderBottom: isSelected ? '3px solid #1B4332' : '3px solid transparent',
                backgroundColor: isSelected ? '#FFFFFF' : 'transparent',
                color: isSelected ? '#1B4332' : '#64748B',
                fontWeight: isSelected ? 700 : 500,
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: FLEET & SHIPMENTS OVERVIEW */}
      {activeTab === 'OVERVIEW' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* STAT METRICS */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            <StatMetric
              label="Assigned Pickups"
              value={shipments.filter((s) => s.stage === 'ASSIGNED').length.toString()}
              subValue="Awaiting origin handover"
              icon={Clock}
            />
            <StatMetric
              label="Active In-Transit"
              value={shipments.filter((s) => s.stage === 'IN_TRANSIT').length.toString()}
              subValue="En route with live telemetry"
              icon={Truck}
            />
            <StatMetric
              label="Completed Deliveries"
              value={shipments.filter((s) => s.stage === 'DELIVERED').length.toString()}
              subValue="Receipt signed at dock"
              icon={CheckCircle2}
            />
            <StatMetric
              label="Transit Incidents"
              value={shipments.filter((s) => s.stage === 'INCIDENT_FLAGGED').length.toString()}
              subValue="Under officer review"
              icon={AlertTriangle}
            />
          </div>

          {/* ACTIVE SHIPMENTS TABLE */}
          <Card
            title="Active Logistics Shipments & Custody Status"
            badge={
              <button
                type="button"
                onClick={handleQuickDispatchShipment}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#1B4332',
                  color: '#FFFFFF',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Plus size={14} /> Dispatch New Pickup
              </button>
            }
          >
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px 12px' }}>Shipment Code</th>
                    <th style={{ padding: '10px 12px' }}>Assigned Driver & Vehicle</th>
                    <th style={{ padding: '10px 12px' }}>Route (Origin → Dest)</th>
                    <th style={{ padding: '10px 12px' }}>Cargo Items</th>
                    <th style={{ padding: '10px 12px' }}>Transit Stage</th>
                    <th style={{ padding: '10px 12px' }}>Seal Status</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {shipments.map((s) => (
                    <tr key={s.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#1B4332' }}>
                        {s.shipment_code}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div>{s.driver_name || 'Ramesh Kumar'}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>{s.vehicle_reg || 'TS-08-UB-4912'}</div>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 500 }}>{s.origin_name || s.origin || 'Adilabad Cluster Gate #2'}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>→ {s.destination_name || s.destination || 'Adilabad Central Collection Dock'}</div>
                      </td>
                      <td style={{ padding: '12px' }}>
                        {s.items && s.items.length > 0 ? (
                          s.items.map((it: any, idx: number) => (
                            <div key={idx}>
                              <span style={{ fontWeight: 600 }}>{it.declared_quantity || 1000} {it.unit || 'kg'}</span> {it.crop_type || 'Organic Cotton'}
                              <div style={{ fontSize: '11px', color: '#64748B' }}>{it.batch_code || 'BATCH-2026-001'}</div>
                            </div>
                          ))
                        ) : (
                          <div>
                            <span style={{ fontWeight: 600 }}>1000 kg</span> Organic Cotton
                            <div style={{ fontSize: '11px', color: '#64748B' }}>BATCH-2026-001</div>
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 600,
                            backgroundColor: s.stage === 'IN_TRANSIT' ? '#EBFBEE' : s.stage === 'DELIVERED' ? '#E2E8F0' : '#FEF3F2',
                            color: s.stage === 'IN_TRANSIT' ? '#2D6A4F' : s.stage === 'DELIVERED' ? '#334155' : '#B42318',
                          }}
                        >
                          {s.stage.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#2D6A4F', fontWeight: 500 }}>
                          <Lock size={12} />
                          {s.seal_number || 'INTACT'}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          {s.stage === 'DELIVERED' ? (
                            <button
                              onClick={() => navigate('/centre')}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                backgroundColor: '#2D6A4F',
                                color: '#FFFFFF',
                                border: 'none',
                                fontSize: '12px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <CheckCircle size={13} /> Open Centre
                            </button>
                          ) : (
                            <button
                              onClick={() => {
                                setSelectedShipment(s);
                                setWizardShipmentId(s.id);
                                if (s.vehicle_reg) setVehicleReg(s.vehicle_reg);
                                if (s.driver_name) setDriverName(s.driver_name);
                                if (s.destination_name || s.destination) setDestinationHub(s.destination_name || s.destination);
                                setHandoverStep(1);
                                setActiveTab('HANDOVER_WIZARD');
                              }}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                backgroundColor: '#1B4332',
                                color: '#FFFFFF',
                                border: 'none',
                                fontSize: '12px',
                                fontWeight: 600,
                                cursor: 'pointer',
                              }}
                            >
                              {s.stage === 'ASSIGNED' ? 'Pickup' : 'Deliver'}
                            </button>
                          )}
                          <button
                            onClick={() => {
                              const bCode = s.items?.[0]?.batch_code;
                              if (bCode) setTimelineBatchCode(bCode);
                            }}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '6px',
                              border: '1px solid #CBD5E1',
                              backgroundColor: '#FFFFFF',
                              color: '#334155',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            <Eye size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: 5-STEP HANDOVER WORKFLOW */}
      {activeTab === 'HANDOVER_WIZARD' && (
        <Card title="5-Step Transporter Handover Workflow">
          <MultiStepForm
            steps={handoverSteps}
            currentStep={handoverStep}
            onPrev={() => setHandoverStep((prev) => Math.max(prev - 1, 0))}
            onNext={() => setHandoverStep((prev) => Math.min(prev + 1, handoverSteps.length - 1))}
            onSubmit={handleHandoverSubmit}
            submitting={handoverSubmitting}
            submitLabel="Digitally Sign & Confirm Handover"
          >
            {/* STEP 0: SHIPMENT SELECTION */}
            {handoverStep === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 1: Select Active Shipment for Handover</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Choose the assigned shipment to initiate pickup or confirm destination delivery.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
                  {shipments.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => setWizardShipmentId(s.id)}
                      style={{
                        padding: '16px',
                        borderRadius: '8px',
                        border: wizardShipmentId === s.id ? '2px solid #2D6A4F' : '1px solid #E2E8F0',
                        backgroundColor: wizardShipmentId === s.id ? '#F4FBF7' : '#FFFFFF',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332' }}>{s.shipment_code}</span>
                        <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#E2E8F0', color: '#334155' }}>
                          {s.stage}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#334155' }}>
                        <strong>Driver:</strong> {s.driver_name} ({s.vehicle_reg})
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                        {s.origin_name} → {s.destination_name}
                      </div>
                      <div style={{ fontSize: '12px', color: '#2D6A4F', fontWeight: 600, marginTop: '6px' }}>
                        Produce: {s.items?.[0]?.declared_quantity} {s.items?.[0]?.unit} {s.items?.[0]?.crop_type}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* STEP 1: PICKUP & VEHICLE INFO */}
            {handoverStep === 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 2: Vehicle & Driver Registration Info</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Record exact transport vehicle, driver credentials, and initial odometer reading.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Vehicle Registration Number</label>
                    <input
                      type="text"
                      value={vehicleReg}
                      onChange={(e) => setVehicleReg(e.target.value)}
                      placeholder="e.g. TS-08-UB-4912"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Assigned Driver Name</label>
                    <input
                      type="text"
                      value={driverName}
                      onChange={(e) => setDriverName(e.target.value)}
                      placeholder="e.g. Ramesh Kumar"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Driver Commercial License ID</label>
                    <input
                      type="text"
                      value={driverId}
                      onChange={(e) => setDriverId(e.target.value)}
                      placeholder="e.g. DL-TEL-2024-88192"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Odometer Reading (km)</label>
                    <input
                      type="number"
                      value={odometerKm}
                      onChange={(e) => setOdometerKm(e.target.value)}
                      placeholder="e.g. 45210"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Container Seal Serial Number</label>
                    <input
                      type="text"
                      value={sealNumber}
                      onChange={(e) => setSealNumber(e.target.value)}
                      placeholder="e.g. SEAL-TX-8821"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Pickup Timestamp</label>
                    <input
                      type="datetime-local"
                      value={pickupTimestamp}
                      onChange={(e) => setPickupTimestamp(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: EVIDENCE CAPTURE */}
            {handoverStep === 2 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 3: Loading Dock & Container Seal Proof</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                    Capture photographic proof of the vehicle license plate, loaded cargo, or tamper seal. Optional evidence adds cryptographic integrity and never blocks submission.
                  </p>
                </div>

                <ContextualEvidenceCapture
                  label="Handover Physical Evidence (Optional)"
                  description="Upload or take a live photo of the loaded cargo, container seal, or gate pass. Cryptographic fingerprinting applied automatically."
                  actionName="Transporter Handover Custody Attestation"
                  evidenceType="SEAL_VERIFICATION"
                  required={false}
                  onEvidenceCaptured={(data) => {
                    setHandoverEvidence({
                      file: data.file,
                      metadata: data.metadata,
                    });
                  }}
                />
              </div>
            )}

            {/* STEP 3: DELIVERY & ROUTE INFO */}
            {handoverStep === 3 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 4: Destination & Receiving Facility Details</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Specify destination hub, receiving dock supervisor contact, and cargo transit condition.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Destination Facility / Hub</label>
                    <input
                      type="text"
                      value={destinationHub}
                      onChange={(e) => setDestinationHub(e.target.value)}
                      placeholder="e.g. Adilabad Central Collection Dock"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Estimated Time of Arrival (ETA)</label>
                    <input
                      type="datetime-local"
                      value={etaTimestamp}
                      onChange={(e) => setEtaTimestamp(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Receiving Dock Supervisor</label>
                    <input
                      type="text"
                      value={receivingContact}
                      onChange={(e) => setReceivingContact(e.target.value)}
                      placeholder="e.g. Suresh Verma"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Cargo Transit Condition</label>
                    <select
                      value={cargoCondition}
                      onChange={(e) => setCargoCondition(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                    >
                      <option value="SEALED_INTACT">Sealed & Intact (Standard)</option>
                      <option value="TARPAULIN_SECURED">Tarpaulin Weather-Secured</option>
                      <option value="TEMP_CONTROLLED">Refrigerated / Cold-Chain Verified</option>
                      <option value="INSPECTION_SEALED">Checked at Regional Weighpost</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 4: REVIEW & SIGN */}
            {handoverStep === 4 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 5: Review & Digitally Sign Custody Attestation</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Review logistics parameters before signing. An immutable business event will be recorded.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>SHIPMENT CODE</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{wizardShipment.shipment_code}</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>DRIVER & VEHICLE</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{driverName} ({vehicleReg})</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>ODOMETER & SEAL</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{odometerKm} km • {sealNumber}</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>DESTINATION HUB</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155', marginTop: '2px' }}>{destinationHub}</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>CONDITION & CONTACT</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155', marginTop: '2px' }}>{cargoCondition} • {receivingContact}</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>EVIDENCE ATTACHMENT</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: handoverEvidence.file ? '#2D6A4F' : '#64748B', marginTop: '2px' }}>
                      {handoverEvidence.file ? `✓ ${handoverEvidence.file.name}` : 'No photo attached (Optional)'}
                    </div>
                  </div>
                </div>

                <div style={{ padding: '12px', backgroundColor: '#EDFDF2', borderRadius: '6px', border: '1px solid #B7E4C7', fontSize: '12px', color: '#1B4332', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={18} color="#2D6A4F" />
                  <span>
                    Will confirm pickup and record <strong>SHIPMENT_DELIVERY_CONFIRMED</strong> on `/api/v1/events/record` — delivering cargo straight to {destinationHub} for Collection Centre intake.
                  </span>
                </div>
              </div>
            )}
          </MultiStepForm>
        </Card>
      )}

      {/* TAB 3: LOG WAYPOINT CHECKPOINT */}
      {activeTab === 'CHECKPOINT' && (
        <Card title="Log Highway Transit Waypoint & Ambient Telemetry">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
              Submit waypoints during transit to record verified geographic progression and ambient transport temperature/humidity.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Target Shipment</label>
                <select
                  value={selectedShipment?.id}
                  onChange={(e) => {
                    const found = shipments.find((s) => s.id === e.target.value);
                    if (found) setSelectedShipment(found);
                  }}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                >
                  {shipments.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.shipment_code} — {s.driver_name} ({s.origin_name} → {s.destination_name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Waypoint Location Name</label>
                <input
                  type="text"
                  value={checkpointLocation}
                  onChange={(e) => setCheckpointLocation(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Transit Status / Condition</label>
                <select
                  value={checkpointCondition}
                  onChange={(e) => setCheckpointCondition(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                >
                  <option value="NORMAL_IN_TRANSIT">Normal In-Transit (On Schedule)</option>
                  <option value="WEATHER_DELAY">Inclement Weather Delay (Rain/Fog)</option>
                  <option value="TOLL_CHECKPOST">Toll Plaza Certified Check</option>
                  <option value="REST_STOP">Driver Mandatory Rest Stop</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>GPS Latitude</label>
                <input
                  type="text"
                  value={checkpointLat}
                  onChange={(e) => setCheckpointLat(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>GPS Longitude</label>
                <input
                  type="text"
                  value={checkpointLon}
                  onChange={(e) => setCheckpointLon(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Ambient Temperature (°C)</label>
                <input
                  type="number"
                  step="0.1"
                  value={tempCelsius}
                  onChange={(e) => setTempCelsius(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Relative Humidity (%)</label>
                <input
                  type="number"
                  step="1"
                  value={humidityPct}
                  onChange={(e) => setHumidityPct(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #E2E8F0', paddingTop: '16px' }}>
              <button
                type="button"
                disabled={checkpointSubmitting}
                onClick={handleRecordCheckpoint}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 22px',
                  borderRadius: '6px',
                  backgroundColor: '#1B4332',
                  color: '#FFFFFF',
                  border: 'none',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: checkpointSubmitting ? 'wait' : 'pointer',
                }}
              >
                {checkpointSubmitting ? <RefreshCw size={16} className="animate-spin" /> : <Navigation size={16} />}
                <span>Log Checkpoint Event</span>
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* TAB 4: TRANSIT INCIDENT REPORTING */}
      {activeTab === 'INCIDENT' && (
        <Card title="Report Transit Incident or Security Alert">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ padding: '14px', borderRadius: '8px', backgroundColor: '#FEF3F2', border: '1px solid #FECDCA', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={20} color="#D92D20" />
              <div style={{ fontSize: '13px', color: '#7A271A' }}>
                Incident reports immediately notify the Evidence Integrity Officer and trigger a cryptographic security review.
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Affected Shipment</label>
                <select
                  value={selectedShipment?.id}
                  onChange={(e) => {
                    const found = shipments.find((s) => s.id === e.target.value);
                    if (found) setSelectedShipment(found);
                  }}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                >
                  {shipments.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.shipment_code} ({s.vehicle_reg})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Incident Category</label>
                <select
                  value={incidentType}
                  onChange={(e) => setIncidentType(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                >
                  <option value="SEAL_TAMPER_SUSPICION">Seal Tampering / Broken Container Seal</option>
                  <option value="MECHANICAL_BREAKDOWN">Vehicle Mechanical Breakdown / Towing</option>
                  <option value="ROUTE_DEVIATION_ALERT">Route Deviation / Roadblock Diversion</option>
                  <option value="CARGO_DAMAGE_ACCIDENT">Cargo Damage / Packaging Breach</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Incident Severity</label>
                <select
                  value={incidentSeverity}
                  onChange={(e) => setIncidentSeverity(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                >
                  <option value="CRITICAL">Critical (Immediate Security Hold)</option>
                  <option value="HIGH">High (Evidence Challenge Required)</option>
                  <option value="MODERATE">Moderate (Transit Delay Only)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Estimated Delay (Hours)</label>
                <input
                  type="number"
                  step="0.5"
                  value={delayHours}
                  onChange={(e) => setDelayHours(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Detailed Incident Notes</label>
                <textarea
                  rows={3}
                  value={incidentNotes}
                  onChange={(e) => setIncidentNotes(e.target.value)}
                  placeholder="Describe the incident circumstances, location, and immediate remedial actions taken..."
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #E2E8F0', paddingTop: '16px' }}>
              <button
                type="button"
                disabled={incidentSubmitting}
                onClick={handleReportIncident}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 22px',
                  borderRadius: '6px',
                  backgroundColor: '#B42318',
                  color: '#FFFFFF',
                  border: 'none',
                  fontSize: '13px',
                  fontWeight: 700,
                  cursor: incidentSubmitting ? 'wait' : 'pointer',
                }}
              >
                {incidentSubmitting ? <RefreshCw size={16} className="animate-spin" /> : <AlertOctagon size={16} />}
                <span>Transmit Incident to Security Queue</span>
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* TAB 5: DELIVERY HISTORY */}
      {activeTab === 'HISTORY' && (
        <Card title="Transporter Delivery History & Completed Consignments">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 12px' }}>Shipment</th>
                  <th style={{ padding: '10px 12px' }}>Driver / Vehicle</th>
                  <th style={{ padding: '10px 12px' }}>Origin → Destination</th>
                  <th style={{ padding: '10px 12px' }}>Delivered Produce</th>
                  <th style={{ padding: '10px 12px' }}>Delivered Date</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {shipments
                  .filter((s) => s.stage === 'DELIVERED')
                  .map((s) => (
                    <tr key={s.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#1B4332' }}>{s.shipment_code}</td>
                      <td style={{ padding: '12px' }}>{s.driver_name} ({s.vehicle_reg})</td>
                      <td style={{ padding: '12px' }}>{s.origin_name} → {s.destination_name}</td>
                      <td style={{ padding: '12px' }}>
                        {s.items?.map((it: any) => `${it.declared_quantity} ${it.unit} ${it.crop_type}`).join(', ')}
                      </td>
                      <td style={{ padding: '12px', color: '#64748B' }}>
                        {s.delivery_timestamp ? new Date(s.delivery_timestamp).toLocaleDateString() : 'Confirmed'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <Badge variant="emerald">DELIVERY VERIFIED</Badge>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TIMELINE MODAL */}
      {timelineBatchCode && (
        <Modal
          isOpen={!!timelineBatchCode}
          onClose={() => setTimelineBatchCode(null)}
          title={`Shipment Provenance Trail: ${timelineBatchCode}`}
          size="large"
        >
          <BatchTimeline batchId={timelineBatchCode} />
        </Modal>
      )}
    </div>
  );
};
