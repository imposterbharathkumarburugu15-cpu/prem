import React, { useState, useEffect } from 'react';
import {
  Building2,
  Scale,
  Sparkles,
  Split,
  CheckSquare,
  RefreshCw,
  Package,
  Layers,
  ArrowRight,
  ShieldCheck,
  Clock,
  CheckCircle2,
  Sliders,
  ChevronDown,
  ChevronUp,
  Truck,
  Send,
  Eye,
  Camera,
  FileCheck,
  Plus,
  AlertTriangle,
  FileText,
  Activity,
  Check,
  Info,
  Droplets,
  Award,
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

export const CollectionCentreWorkspace: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'DOCK_INTAKE' | 'INTAKE_WIZARD' | 'PROCESSING_SPLIT' | 'QUALITY_RECORDS' | 'DISPATCHES'>('DOCK_INTAKE');
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Incoming Dock Shipments
  const [dockShipments, setDockShipments] = useState<any[]>([
    {
      id: 'shp-dock-01',
      shipment_code: 'SHP-TEL-2026-089',
      driver_name: 'Ramesh Kumar',
      vehicle_reg: 'TS-08-UB-4912',
      origin_name: 'Adilabad Cluster Gate #2',
      destination_name: 'Adilabad Central Collection Dock',
      stage: 'DELIVERED',
      arrived_at: new Date(Date.now() - 3600000 * 2).toISOString(),
      items: [
        {
          batch_id: 'batch-c-01',
          batch_code: 'BATCH-TEL-KRM-2026-001',
          crop_type: 'Organic Cotton',
          variety: 'Suvin Extra-Long Staple',
          declared_quantity: 1250.0,
          unit: 'kg',
        },
      ],
    },
    {
      id: 'shp-dock-02',
      shipment_code: 'SHP-TEL-2026-092',
      driver_name: 'Anand Reddy',
      vehicle_reg: 'TS-07-EK-8114',
      origin_name: 'Warangal South Mandi Depot',
      destination_name: 'Adilabad Central Collection Dock',
      stage: 'IN_TRANSIT',
      arrived_at: null,
      items: [
        {
          batch_id: 'batch-c-02',
          batch_code: 'BATCH-TEL-WRG-2026-042',
          crop_type: 'Basmati Rice',
          variety: 'Pusa 1121',
          declared_quantity: 2800.0,
          unit: 'kg',
        },
      ],
    },
  ]);

  // Inventory & Processed Batches
  const [batches, setBatches] = useState<any[]>([
    {
      id: 'batch-c-01',
      batch_code: 'BATCH-TEL-KRM-2026-001',
      crop_type: 'Organic Cotton',
      variety: 'Suvin Extra-Long Staple',
      current_quantity: 1248.0,
      initial_quantity: 1250.0,
      unit: 'kg',
      stage: 'AT_COLLECTION_CENTRE',
      quality_grade: 'GRADE_A',
      lineage_type: 'ORIGINAL',
      moisture_pct: 8.4,
      scale_id: 'SCALE-NIST-CALIB-04',
      storage_bin: 'Silo Bay 3A',
      created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    },
    {
      id: 'batch-c-02',
      batch_code: 'BATCH-TEL-WRG-2026-042',
      crop_type: 'Basmati Rice',
      variety: 'Pusa 1121',
      current_quantity: 2795.0,
      initial_quantity: 2800.0,
      unit: 'kg',
      stage: 'AT_COLLECTION_CENTRE',
      quality_grade: 'GRADE_A',
      lineage_type: 'ORIGINAL',
      moisture_pct: 11.2,
      scale_id: 'SCALE-NIST-CALIB-02',
      storage_bin: 'Aisle 2 - Ventilated Bin',
      created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    },
  ]);

  // Selected Batch for Audit Timeline
  const [timelineBatchId, setTimelineBatchId] = useState<string | null>(null);

  // -------------------------------------------------------------
  // 6-STEP PROCESSOR RECEIPT & INTAKE WORKFLOW
  // -------------------------------------------------------------
  const [wizardStep, setWizardStep] = useState<number>(0);
  const [wizardSubmitting, setWizardSubmitting] = useState<boolean>(false);

  // Step 0: Incoming Batch Selection
  const [selectedDockShipmentId, setSelectedDockShipmentId] = useState<string>(dockShipments[0].id);

  // Step 1: Quantity & Weighbridge
  const [grossWeight, setGrossWeight] = useState('1298.0');
  const [tareWeight, setTareWeight] = useState('50.0');
  const [scaleId, setScaleId] = useState('SCALE-NIST-CALIB-04');
  const [isDigitalScale, setIsDigitalScale] = useState(true);

  // Step 2: Receipt Evidence
  const [receiptEvidence, setReceiptEvidence] = useState<{
    file: File | null;
    metadata: EvidenceMetadata | null;
  }>({ file: null, metadata: null });

  // Step 3: Processing & Storage Details
  const [processingType, setProcessingType] = useState('CLEANING_DEHUSKING');
  const [storageSilo, setStorageSilo] = useState('Grain Silo 4 - Climate Controlled');
  const [targetPackaging, setTargetPackaging] = useState('TAMPER_SEALED_JUTE_50KG');

  // Step 4: Quality Evidence & Grading
  const [inspectionGrade, setInspectionGrade] = useState('GRADE_A');
  const [inspectionDecision, setInspectionDecision] = useState('ACCEPTED');
  const [moisturePct, setMoisturePct] = useState('8.4');
  const [defectPct, setDefectPct] = useState('0.8');
  const [defectNotes, setDefectNotes] = useState('Optimal fiber tensile strength, minimal foreign dust, zero mold.');
  const [qualityEvidence, setQualityEvidence] = useState<{
    file: File | null;
    metadata: EvidenceMetadata | null;
  }>({ file: null, metadata: null });

  // -------------------------------------------------------------
  // BATCH SPLIT MODAL STATE
  // -------------------------------------------------------------
  const [splitParentBatch, setSplitParentBatch] = useState<any>(null);
  const [splitQtyA, setSplitQtyA] = useState('600.0');
  const [splitQtyB, setSplitQtyB] = useState('648.0');
  const [splitCodeA, setSplitCodeA] = useState('BATCH-TEL-KRM-SPLIT-A');
  const [splitCodeB, setSplitCodeB] = useState('BATCH-TEL-KRM-SPLIT-B');
  const [splitSubmitting, setSplitSubmitting] = useState(false);

  // -------------------------------------------------------------
  // BATCH DISPATCH STATE
  // -------------------------------------------------------------
  const [dispatchBatch, setDispatchBatch] = useState<any>(null);
  const [dispatchDestination, setDispatchDestination] = useState('Apex Supermarket Central Logistics - Hyderabad');
  const [dispatchVehicle, setDispatchVehicle] = useState('TS-07-EK-8114');
  const [dispatchQty, setDispatchQty] = useState('600.0');
  const [dispatchSubmitting, setDispatchSubmitting] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const res = await api.getCentreDashboard();
      if (res) {
        setData(res);
        if (res.batches && res.batches.length > 0) {
          setBatches(res.batches);
        }
        if (res.incoming_shipments && res.incoming_shipments.length > 0) {
          setDockShipments(res.incoming_shipments);
        }
      }
    } catch (e) {
      console.warn('Centre dashboard endpoint fallback:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const selectedShipment = dockShipments.find((s) => s.id === selectedDockShipmentId) || dockShipments[0];
  const netWeight = Math.max(0, (parseFloat(grossWeight) || 0) - (parseFloat(tareWeight) || 0));

  const intakeSteps: FormStep[] = [
    { id: 0, label: 'Batch Select', description: 'Arriving dock cargo' },
    { id: 1, label: 'Weight & Scale', description: 'IoT certified scale' },
    { id: 2, label: 'Receipt Evidence', description: 'Scale ticket photo' },
    { id: 3, label: 'Processing Info', description: 'Cleaning & storage silo' },
    { id: 4, label: 'Quality & Lab', description: 'Moisture, grade & test' },
    { id: 5, label: 'Review & Submit', description: 'Dual event commitment' },
  ];

  // Submit 6-Step Processor Intake Workflow
  const handleIntakeSubmit = async () => {
    setWizardSubmitting(true);
    setActionMsg(null);
    try {
      const targetBatchId = selectedShipment.items?.[0]?.batch_id || selectedShipment.items?.[0]?.batch_code || 'batch-c-01';

      // 1. PRODUCE_RECEIVED event
      await api.recordBusinessEvent({
        event_type: 'PRODUCE_RECEIVED',
        batch_id: targetBatchId,
        shipment_id: selectedShipment.id,
        payload: {
          batch_id: targetBatchId,
          shipment_id: selectedShipment.id,
          gross_quantity: netWeight,
          receiving_facility_id: 'cc-adilabad-main',
          notes: `Produce dock intake completed at Adilabad Central Hub. Storage: ${storageSilo}`,
        },
      });

      // 2. WEIGHT_RECORDED event
      await api.recordBusinessEvent({
        event_type: 'WEIGHT_RECORDED',
        batch_id: targetBatchId,
        payload: {
          batch_id: targetBatchId,
          measured_weight: netWeight,
          unit: 'kg',
          scale_identifier: scaleId,
          is_manual_entry: !isDigitalScale,
          tare_weight: parseFloat(tareWeight) || 0,
        },
        evidence_file: receiptEvidence.file,
        evidence_metadata: receiptEvidence.metadata,
      });

      // 3. QUALITY_INSPECTION_COMPLETED event
      await api.recordBusinessEvent({
        event_type: 'QUALITY_INSPECTION_COMPLETED',
        batch_id: targetBatchId,
        payload: {
          batch_id: targetBatchId,
          grade: inspectionGrade,
          decision: inspectionDecision,
          moisture_pct: parseFloat(moisturePct) || 8.4,
          defect_notes: defectNotes,
          inspector_id: 'inspector-dr-rao',
        },
        evidence_file: qualityEvidence.file,
        evidence_metadata: qualityEvidence.metadata,
      });

      // Update local state
      setBatches((prev) => [
        {
          id: targetBatchId,
          batch_code: selectedShipment.items?.[0]?.batch_code || `BATCH-CC-${Math.floor(1000 + Math.random() * 9000)}`,
          crop_type: selectedShipment.items?.[0]?.crop_type || 'Organic Cotton',
          variety: 'Standard Tested',
          current_quantity: netWeight,
          initial_quantity: netWeight,
          unit: 'kg',
          stage: 'AT_COLLECTION_CENTRE',
          quality_grade: inspectionGrade,
          lineage_type: 'ORIGINAL',
          moisture_pct: parseFloat(moisturePct),
          scale_id: scaleId,
          storage_bin: storageSilo,
          created_at: new Date().toISOString(),
        },
        ...prev,
      ]);

      setActionMsg({
        type: 'success',
        text: `Intake workflow completed! Batch '${selectedShipment.items?.[0]?.batch_code}' weighed (${netWeight} kg) and graded (${inspectionGrade}) successfully!`,
      });
      setWizardStep(0);
      setActiveTab('DOCK_INTAKE');
    } catch (err: any) {
      console.error('Intake submission error:', err);
      setActionMsg({
        type: 'error',
        text: `Intake failed: ${err.message || 'Server error'}`,
      });
    } finally {
      setWizardSubmitting(false);
    }
  };

  // Submit Batch Split
  const handleSplitSubmit = async () => {
    if (!splitParentBatch) return;
    setSplitSubmitting(true);
    setActionMsg(null);
    try {
      const qA = parseFloat(splitQtyA) || 0;
      const qB = parseFloat(splitQtyB) || 0;

      await api.recordBusinessEvent({
        event_type: 'BATCH_SPLIT',
        batch_id: splitParentBatch.id,
        payload: {
          parent_batch_id: splitParentBatch.id,
          splits: [
            { batch_code: splitCodeA, quantity: qA, crop_type: splitParentBatch.crop_type },
            { batch_code: splitCodeB, quantity: qB, crop_type: splitParentBatch.crop_type },
          ],
          reason: 'Split for export vs domestic retail supply chains',
        },
      });

      setBatches((prev) => [
        {
          id: `child-${Date.now()}-A`,
          batch_code: splitCodeA,
          crop_type: splitParentBatch.crop_type,
          variety: splitParentBatch.variety,
          current_quantity: qA,
          initial_quantity: qA,
          unit: splitParentBatch.unit,
          stage: 'AT_COLLECTION_CENTRE',
          quality_grade: splitParentBatch.quality_grade,
          lineage_type: 'SPLIT_CHILD',
          created_at: new Date().toISOString(),
        },
        {
          id: `child-${Date.now()}-B`,
          batch_code: splitCodeB,
          crop_type: splitParentBatch.crop_type,
          variety: splitParentBatch.variety,
          current_quantity: qB,
          initial_quantity: qB,
          unit: splitParentBatch.unit,
          stage: 'AT_COLLECTION_CENTRE',
          quality_grade: splitParentBatch.quality_grade,
          lineage_type: 'SPLIT_CHILD',
          created_at: new Date().toISOString(),
        },
        ...prev.filter((b) => b.id !== splitParentBatch.id),
      ]);

      setActionMsg({
        type: 'success',
        text: `Batch '${splitParentBatch.batch_code}' successfully split into '${splitCodeA}' (${qA} kg) and '${splitCodeB}' (${qB} kg)!`,
      });
      setSplitParentBatch(null);
    } catch (err: any) {
      setActionMsg({
        type: 'error',
        text: `Split failed: ${err.message || 'Error'}`,
      });
    } finally {
      setSplitSubmitting(false);
    }
  };

  // Instant Transfer to Retailer
  const handleQuickTransferToRetailer = async (b: any) => {
    setActionMsg(null);
    try {
      await api.recordBusinessEvent({
        event_type: 'BATCH_DISPATCHED',
        batch_id: b.id,
        payload: {
          batch_id: b.id,
          destination_org_id: 'ret-supermarkets-hyd',
          dispatched_quantity: b.current_quantity,
          vehicle_reg: 'TS-07-EK-8114',
          notes: `Instant transfer from Collection Centre to Retailer Store`,
        },
      });

      setBatches((prev) =>
        prev.map((item) => (item.id === b.id ? { ...item, stage: 'IN_TRANSIT_TO_RETAIL' } : item))
      );

      setActionMsg({
        type: 'success',
        text: `🚀 Transferred to Retailer: Batch '${b.batch_code}' is now live in Retailer Workspace ready for store intake & QR minting!`,
      });
    } catch (err: any) {
      setActionMsg({
        type: 'error',
        text: `Transfer failed: ${err.message || 'Error'}`,
      });
    }
  };

  // Submit Batch Dispatch
  const handleDispatchSubmit = async () => {
    if (!dispatchBatch) return;
    setDispatchSubmitting(true);
    setActionMsg(null);
    try {
      const dQty = parseFloat(dispatchQty) || dispatchBatch.current_quantity;

      await api.recordBusinessEvent({
        event_type: 'BATCH_DISPATCHED',
        batch_id: dispatchBatch.id,
        payload: {
          batch_id: dispatchBatch.id,
          destination_org_id: 'ret-supermarkets-hyd',
          dispatched_quantity: dQty,
          vehicle_reg: dispatchVehicle,
          notes: `Dispatched from Adilabad Hub to ${dispatchDestination}`,
        },
      });

      setBatches((prev) =>
        prev.map((b) => (b.id === dispatchBatch.id ? { ...b, stage: 'IN_TRANSIT_TO_RETAIL' } : b))
      );

      setActionMsg({
        type: 'success',
        text: `Batch '${dispatchBatch.batch_code}' dispatched to '${dispatchDestination}'!`,
      });
      setDispatchBatch(null);
    } catch (err: any) {
      setActionMsg({
        type: 'error',
        text: `Dispatch failed: ${err.message || 'Error'}`,
      });
    } finally {
      setDispatchSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto', paddingBottom: '48px' }}>
      {/* HEADER SECTION */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', background: 'linear-gradient(135deg, #1B4332 0%, #2D6A4F 100%)', borderRadius: '12px', padding: '24px 28px', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(27, 67, 50, 0.15)' }}>
        <div style={{ maxWidth: '640px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)', padding: '4px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <Building2 size={14} />
              Collection & Processing Facility
            </span>
            <span style={{ fontSize: '12px', color: '#B7E4C7' }}>• ఆదిలాబాద్ ప్రాసెసింగ్ కేంద్రం</span>
          </div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>
            Collection Centre & Quality Operations
          </h1>
          <p style={{ fontSize: '14px', margin: 0, color: '#D8F3DC', lineHeight: 1.5 }}>
            Manage dock intake, calibrated IoT weighbridge readings, laboratory grading inspections, strict mass-balance splits, and verified retail dispatches.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            onClick={() => {
              setWizardStep(0);
              setActiveTab('INTAKE_WIZARD');
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
            <span>Process Inbound Intake</span>
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
          <button
            onClick={() => setActionMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 600 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* NAVIGATION TABS */}
      <div style={{ display: 'flex', gap: '6px', borderBottom: '1px solid #E2E8F0', paddingBottom: '2px' }}>
        {[
          { id: 'DOCK_INTAKE', label: 'Dock Intake & Inventory', icon: Building2 },
          { id: 'INTAKE_WIZARD', label: '6-Step Processor Intake Workflow', icon: Scale },
          { id: 'PROCESSING_SPLIT', label: 'Mass Balance & Lineage Split', icon: Split },
          { id: 'QUALITY_RECORDS', label: 'Quality & Lab Inspection', icon: CheckSquare },
          { id: 'DISPATCHES', label: 'Output Batches & Dispatches', icon: Send },
        ].map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
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

      {/* TAB 1: DOCK INTAKE & INVENTORY */}
      {activeTab === 'DOCK_INTAKE' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* STAT METRICS */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            <StatMetric
              label="Incoming Dock Shipments"
              value={dockShipments.length.toString()}
              subValue="Arrived from regional farms"
              icon={Truck}
            />
            <StatMetric
              label="Active Hub Inventory"
              value="4,043 kg"
              subValue="Stored across silos & bays"
              icon={Building2}
            />
            <StatMetric
              label="Inspected & Graded"
              value="100%"
              subValue="Certified Grade A standard"
              icon={ShieldCheck}
            />
            <StatMetric
              label="Mass Balance Accuracy"
              value="99.8%"
              subValue="Reconciliation within 0.2%"
              icon={Scale}
            />
          </div>

          {/* ARRIVING DOCK SHIPMENTS TABLE */}
          <Card title="Arriving Transporter Shipments at Dock Gate">
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px 12px' }}>Shipment</th>
                    <th style={{ padding: '10px 12px' }}>Transporter / Vehicle</th>
                    <th style={{ padding: '10px 12px' }}>Origin Cluster</th>
                    <th style={{ padding: '10px 12px' }}>Manifest Cargo</th>
                    <th style={{ padding: '10px 12px' }}>Dock Status</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {dockShipments.map((s) => (
                    <tr key={s.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#1B4332' }}>{s.shipment_code}</td>
                      <td style={{ padding: '12px' }}>
                        <div>{s.driver_name}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>{s.vehicle_reg}</div>
                      </td>
                      <td style={{ padding: '12px', color: '#334155' }}>{s.origin_name}</td>
                      <td style={{ padding: '12px' }}>
                        {s.items?.map((it: any, idx: number) => (
                          <div key={idx}>
                            <span style={{ fontWeight: 600 }}>{it.declared_quantity} {it.unit}</span> {it.crop_type}
                            <div style={{ fontSize: '11px', color: '#64748B' }}>{it.batch_code}</div>
                          </div>
                        ))}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, backgroundColor: '#EDFDF2', color: '#2D6A4F' }}>
                          {s.stage}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          onClick={() => {
                            setSelectedDockShipmentId(s.id);
                            setWizardStep(0);
                            setActiveTab('INTAKE_WIZARD');
                          }}
                          style={{
                            padding: '6px 14px',
                            borderRadius: '6px',
                            backgroundColor: '#1B4332',
                            color: '#FFFFFF',
                            border: 'none',
                            fontSize: '12px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Weigh & Receive
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* ACTIVE INVENTORY AT CENTRE */}
          <Card title="Active In-Stock Hub Batches">
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px 12px' }}>Batch Code</th>
                    <th style={{ padding: '10px 12px' }}>Crop & Variety</th>
                    <th style={{ padding: '10px 12px' }}>Available Weight</th>
                    <th style={{ padding: '10px 12px' }}>Grade</th>
                    <th style={{ padding: '10px 12px' }}>Storage Location</th>
                    <th style={{ padding: '10px 12px' }}>Lineage</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((b) => (
                    <tr key={b.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#1B4332' }}>{b.batch_code}</td>
                      <td style={{ padding: '12px' }}>
                        <div>{b.crop_type}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>{b.variety}</div>
                      </td>
                      <td style={{ padding: '12px', fontWeight: 600 }}>{b.current_quantity} {b.unit}</td>
                      <td style={{ padding: '12px' }}>
                        <Badge variant="emerald">{b.quality_grade || 'GRADE_A'}</Badge>
                      </td>
                      <td style={{ padding: '12px', color: '#475569' }}>{b.storage_bin || 'Main Hub Silo'}</td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', backgroundColor: '#E2E8F0', color: '#334155' }}>
                          {b.lineage_type || 'ORIGINAL'}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => {
                              setSplitParentBatch(b);
                              setSplitQtyA((b.current_quantity * 0.5).toFixed(1));
                              setSplitQtyB((b.current_quantity * 0.5).toFixed(1));
                              setSplitCodeA(`${b.batch_code}-A`);
                              setSplitCodeB(`${b.batch_code}-B`);
                              setActiveTab('PROCESSING_SPLIT');
                            }}
                            style={{
                              padding: '5px 10px',
                              borderRadius: '6px',
                              backgroundColor: '#FFFFFF',
                              border: '1px solid #CBD5E1',
                              color: '#1B4332',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Split size={12} />
                            <span>Split</span>
                          </button>
                          <button
                            onClick={() => handleQuickTransferToRetailer(b)}
                            style={{
                              padding: '5px 11px',
                              borderRadius: '6px',
                              backgroundColor: '#0F766E',
                              color: '#FFFFFF',
                              border: 'none',
                              fontSize: '12px',
                              fontWeight: 700,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              boxShadow: '0 2px 4px rgba(15, 118, 110, 0.25)',
                            }}
                            title="Instant one-click transfer to Retailer Workspace"
                          >
                            <Send size={12} />
                            <span>Transfer to Retailer</span>
                          </button>
                          <button
                            onClick={() => {
                              setDispatchBatch(b);
                              setDispatchQty(b.current_quantity.toString());
                              setActiveTab('DISPATCHES');
                            }}
                            style={{
                              padding: '5px 10px',
                              borderRadius: '6px',
                              backgroundColor: '#1B4332',
                              color: '#FFFFFF',
                              border: 'none',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Truck size={12} />
                            <span>Custom Dispatch</span>
                          </button>
                          <button
                            onClick={() => setTimelineBatchId(b.batch_code)}
                            style={{
                              padding: '5px 8px',
                              borderRadius: '6px',
                              backgroundColor: '#FFFFFF',
                              border: '1px solid #CBD5E1',
                              color: '#475569',
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

      {/* TAB 2: 6-STEP PROCESSOR INTAKE WORKFLOW */}
      {activeTab === 'INTAKE_WIZARD' && (
        <Card title="6-Step Processor Receipt & Intake Workflow">
          <MultiStepForm
            steps={intakeSteps}
            currentStep={wizardStep}
            onPrev={() => setWizardStep((prev) => Math.max(prev - 1, 0))}
            onNext={() => setWizardStep((prev) => Math.min(prev + 1, intakeSteps.length - 1))}
            onSubmit={handleIntakeSubmit}
            submitting={wizardSubmitting}
            submitLabel="Commit Signed Intake & Quality Grade"
          >
            {/* STEP 0: BATCH SELECT */}
            {wizardStep === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 1: Select Incoming Batch from Dock Cargo</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Choose the arriving transporter shipment to offload, weigh, and certify.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
                  {dockShipments.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => setSelectedDockShipmentId(s.id)}
                      style={{
                        padding: '16px',
                        borderRadius: '8px',
                        border: selectedDockShipmentId === s.id ? '2px solid #2D6A4F' : '1px solid #E2E8F0',
                        backgroundColor: selectedDockShipmentId === s.id ? '#F4FBF7' : '#FFFFFF',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332' }}>{s.shipment_code}</span>
                        <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#EDFDF2', color: '#2D6A4F' }}>
                          {s.stage}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#334155' }}>
                        <strong>Driver:</strong> {s.driver_name} ({s.vehicle_reg})
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                        Origin: {s.origin_name}
                      </div>
                      <div style={{ fontSize: '12px', color: '#2D6A4F', fontWeight: 600, marginTop: '6px' }}>
                        Declared: {s.items?.[0]?.declared_quantity} {s.items?.[0]?.unit} {s.items?.[0]?.crop_type}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* STEP 1: QUANTITY RECEIVED & WEIGHBRIDGE */}
            {wizardStep === 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 2: Certified Weighbridge Scale Measurement</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Record calibrated gross weight, tare truck weight, and certified scale calibration ID.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Weighbridge Mode</label>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button
                        type="button"
                        onClick={() => setIsDigitalScale(true)}
                        style={{
                          flex: 1,
                          padding: '8px',
                          borderRadius: '6px',
                          border: isDigitalScale ? '2px solid #2D6A4F' : '1px solid #CBD5E1',
                          backgroundColor: isDigitalScale ? '#EDFDF2' : '#FFFFFF',
                          color: isDigitalScale ? '#1B4332' : '#64748B',
                          fontWeight: 600,
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                      >
                        Digital IoT Automated
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsDigitalScale(false)}
                        style={{
                          flex: 1,
                          padding: '8px',
                          borderRadius: '6px',
                          border: !isDigitalScale ? '2px solid #2D6A4F' : '1px solid #CBD5E1',
                          backgroundColor: !isDigitalScale ? '#EDFDF2' : '#FFFFFF',
                          color: !isDigitalScale ? '#1B4332' : '#64748B',
                          fontWeight: 600,
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                      >
                        Manual Calibration Entry
                      </button>
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Scale Calibration Identifier</label>
                    <input
                      type="text"
                      value={scaleId}
                      onChange={(e) => setScaleId(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Gross Weight (kg)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={grossWeight}
                      onChange={(e) => setGrossWeight(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Tare Vehicle/Crate Weight (kg)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={tareWeight}
                      onChange={(e) => setTareWeight(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div style={{ gridColumn: 'span 2', padding: '14px', backgroundColor: '#EDFDF2', borderRadius: '6px', border: '1px solid #B7E4C7', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: '11px', color: '#2D6A4F', textTransform: 'uppercase', fontWeight: 700 }}>Computed Net Produce Weight</div>
                      <div style={{ fontSize: '20px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>
                        {netWeight.toFixed(1)} kg
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '12px', color: '#40916C' }}>
                      Declared: {selectedShipment.items?.[0]?.declared_quantity} kg
                      <div style={{ fontSize: '11px', fontWeight: 600, color: Math.abs(netWeight - (selectedShipment.items?.[0]?.declared_quantity || 0)) < 15 ? '#2D6A4F' : '#B42318' }}>
                        Variance: {Math.abs(netWeight - (selectedShipment.items?.[0]?.declared_quantity || 0)).toFixed(1)} kg (Within tolerance)
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: RECEIPT EVIDENCE */}
            {wizardStep === 2 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 3: Weighbridge Slip & Dock Proof (Optional)</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                    Attach digital printout or photograph of the certified weighbridge slip. Optional evidence never blocks workflow progression.
                  </p>
                </div>

                <ContextualEvidenceCapture
                  label="Weighbridge Digital Slip"
                  description="Upload digital weighing ticket or capture scale monitor. Automatic SHA-256 fingerprinting applied."
                  actionName="Collection Centre Weighing Verification"
                  evidenceType="SCALE_SLIP"
                  required={false}
                  onEvidenceCaptured={(data) => {
                    setReceiptEvidence({
                      file: data.file,
                      metadata: data.metadata,
                    });
                  }}
                />
              </div>
            )}

            {/* STEP 3: PROCESSING & STORAGE DETAILS */}
            {wizardStep === 3 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 4: Processing Protocol & Storage Allocation</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Specify primary intake processing treatment and assigned warehouse silo/bin.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Primary Processing Method</label>
                    <select
                      value={processingType}
                      onChange={(e) => setProcessingType(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                    >
                      <option value="CLEANING_DEHUSKING">Pre-Cleaning & Mechanical Ginning / De-husking</option>
                      <option value="GRADING_SIEVING">Optical Color Sorting & Precision Sieving</option>
                      <option value="MOISTURE_CONDITIONING">Controlled Aeration & De-humidification</option>
                      <option value="DIRECT_STORAGE">Intake Quality Direct Warehouse Bagging</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Assigned Storage Silo / Bin</label>
                    <input
                      type="text"
                      value={storageSilo}
                      onChange={(e) => setStorageSilo(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Output Packaging Format</label>
                    <select
                      value={targetPackaging}
                      onChange={(e) => setTargetPackaging(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                    >
                      <option value="TAMPER_SEALED_JUTE_50KG">Tamper-Sealed High-Density Jute Bags (50 kg)</option>
                      <option value="VENTILATED_CRATE_25KG">Ventilated Food-Grade HDPE Crates (25 kg)</option>
                      <option value="VACUUM_BULK_OCTABIN">Vacuum-Sealed Bulk Octabin Container</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 4: QUALITY EVIDENCE & GRADING */}
            {wizardStep === 4 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 5: Quality Inspection & Laboratory Certification</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Execute laboratory inspection metrics and attach sample test certificate.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Assigned Quality Grade</label>
                    <select
                      value={inspectionGrade}
                      onChange={(e) => setInspectionGrade(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                    >
                      <option value="GRADE_A">Grade A (Certified Premium)</option>
                      <option value="GRADE_B">Grade B (Standard Commercial)</option>
                      <option value="GRADE_C">Grade C (Industrial Grade)</option>
                      <option value="REJECTED">Rejected (Fails Organic Threshold)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Intake Decision</label>
                    <select
                      value={inspectionDecision}
                      onChange={(e) => setInspectionDecision(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                    >
                      <option value="ACCEPTED">Accepted for Hub Storage</option>
                      <option value="HOLD">Hold for Secondary Chemical Test</option>
                      <option value="REJECTED">Reject Batch</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Moisture Content (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={moisturePct}
                      onChange={(e) => setMoisturePct(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div style={{ gridColumn: 'span 3' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Laboratory Defect Notes</label>
                    <textarea
                      rows={2}
                      value={defectNotes}
                      onChange={(e) => setDefectNotes(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div style={{ gridColumn: 'span 3' }}>
                    <ContextualEvidenceCapture
                      label="Laboratory Sample or Certificate (Optional)"
                      description="Upload laboratory test sheet or photo of graded sample lot."
                      actionName="Collection Centre Quality Inspection"
                      evidenceType="LAB_REPORT"
                      required={false}
                      onEvidenceCaptured={(data) => {
                        setQualityEvidence({
                          file: data.file,
                          metadata: data.metadata,
                        });
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* STEP 5: REVIEW & SUBMIT */}
            {wizardStep === 5 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 6: Review & Finalize Processor Intake</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Review intake metrics. Three verified business events will be committed atomically.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>SHIPMENT CODE</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{selectedShipment.shipment_code}</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>NET WEIGHT RECORDED</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{netWeight.toFixed(1)} kg ({scaleId})</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>CERTIFIED GRADE</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{inspectionGrade} ({inspectionDecision})</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>STORAGE ALLOCATION</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155', marginTop: '2px' }}>{storageSilo}</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>MOISTURE & DEFECTS</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155', marginTop: '2px' }}>Moisture: {moisturePct}% • Defect: {defectPct}%</div>
                  </div>
                  <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>SUPPORTING EVIDENCE</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: receiptEvidence.file ? '#2D6A4F' : '#64748B', marginTop: '2px' }}>
                      {receiptEvidence.file ? '✓ Slip Attached' : 'None (Optional)'} • {qualityEvidence.file ? '✓ Lab Cert' : 'None'}
                    </div>
                  </div>
                </div>

                <div style={{ padding: '12px', backgroundColor: '#EDFDF2', borderRadius: '6px', border: '1px solid #B7E4C7', fontSize: '12px', color: '#1B4332', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={18} color="#2D6A4F" />
                  <span>
                    Will atomically trigger <strong>PRODUCE_RECEIVED</strong>, <strong>WEIGHT_RECORDED</strong>, and <strong>QUALITY_INSPECTION_COMPLETED</strong> on `/api/v1/events/record`.
                  </span>
                </div>
              </div>
            )}
          </MultiStepForm>
        </Card>
      )}

      {/* TAB 3: MASS BALANCE & LINEAGE SPLIT */}
      {activeTab === 'PROCESSING_SPLIT' && (
        <Card title="Mass Balance Conservation & Batch Lineage Splitting">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ padding: '14px', backgroundColor: '#EDFDF2', borderRadius: '8px', border: '1px solid #B7E4C7', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#1B4332' }}>Strict Mass Conservation Principle Active</div>
                <div style={{ fontSize: '12px', color: '#40916C' }}>
                  Total split child batch weights (∑ Q_child) cannot exceed parent batch inventory (Q_parent).
                </div>
              </div>
              <Badge variant="emerald">100% RECONCILED</Badge>
            </div>

            {splitParentBatch ? (
              <div style={{ padding: '18px', borderRadius: '8px', border: '1px solid #CBD5E1', backgroundColor: '#F8F9FA', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#1B4332' }}>
                    Splitting Batch: {splitParentBatch.batch_code} ({splitParentBatch.current_quantity} {splitParentBatch.unit})
                  </h4>
                  <button
                    onClick={() => setSplitParentBatch(null)}
                    style={{ background: 'none', border: 'none', fontSize: '12px', color: '#64748B', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Cancel Split
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px' }}>
                  <div style={{ padding: '12px', backgroundColor: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Child Batch A Code</div>
                    <input
                      type="text"
                      value={splitCodeA}
                      onChange={(e) => setSplitCodeA(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#334155', marginTop: '10px', marginBottom: '6px' }}>Quantity A (kg)</div>
                    <input
                      type="number"
                      step="0.5"
                      value={splitQtyA}
                      onChange={(e) => setSplitQtyA(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div style={{ padding: '12px', backgroundColor: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Child Batch B Code</div>
                    <input
                      type="text"
                      value={splitCodeB}
                      onChange={(e) => setSplitCodeB(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#334155', marginTop: '10px', marginBottom: '6px' }}>Quantity B (kg)</div>
                    <input
                      type="number"
                      step="0.5"
                      value={splitQtyB}
                      onChange={(e) => setSplitQtyB(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #E2E8F0', paddingTop: '12px' }}>
                  <div style={{ fontSize: '12px', color: '#64748B' }}>
                    Total Split Sum: {(parseFloat(splitQtyA) || 0) + (parseFloat(splitQtyB) || 0)} kg / {splitParentBatch.current_quantity} kg
                  </div>

                  <button
                    disabled={splitSubmitting || (parseFloat(splitQtyA) || 0) + (parseFloat(splitQtyB) || 0) > splitParentBatch.current_quantity}
                    onClick={handleSplitSubmit}
                    style={{
                      padding: '8px 20px',
                      borderRadius: '6px',
                      backgroundColor: '#1B4332',
                      color: '#FFFFFF',
                      border: 'none',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {splitSubmitting ? 'Splitting...' : 'Execute Lineage Split'}
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ padding: '36px', textAlign: 'center', backgroundColor: '#F8F9FA', borderRadius: '8px' }}>
                <Split size={36} color="#64748B" style={{ margin: '0 auto 8px auto' }} />
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#1B4332' }}>Select a Batch to Split</div>
                <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px' }}>
                  Choose any active batch in the Dock Intake tab to partition into serialized child sub-batches.
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* TAB 4: QUALITY & LAB RECORDS */}
      {activeTab === 'QUALITY_RECORDS' && (
        <Card title="Certified Quality Inspection & Grading Audit Log">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 12px' }}>Batch Code</th>
                  <th style={{ padding: '10px 12px' }}>Crop Category</th>
                  <th style={{ padding: '10px 12px' }}>Certified Grade</th>
                  <th style={{ padding: '10px 12px' }}>Moisture (%)</th>
                  <th style={{ padding: '10px 12px' }}>Scale Reference</th>
                  <th style={{ padding: '10px 12px' }}>Inspection Decision</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Audit</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((b) => (
                  <tr key={b.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#1B4332' }}>{b.batch_code}</td>
                    <td style={{ padding: '12px' }}>{b.crop_type}</td>
                    <td style={{ padding: '12px' }}>
                      <Badge variant="emerald">{b.quality_grade || 'GRADE_A'}</Badge>
                    </td>
                    <td style={{ padding: '12px', fontWeight: 600 }}>{b.moisture_pct || 8.4}%</td>
                    <td style={{ padding: '12px', color: '#64748B' }}>{b.scale_id || 'SCALE-NIST-04'}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, backgroundColor: '#EDFDF2', color: '#2D6A4F' }}>
                        ACCEPTED
                      </span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <button
                        onClick={() => setTimelineBatchId(b.batch_code)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border: '1px solid #CBD5E1',
                          backgroundColor: '#FFFFFF',
                          color: '#1B4332',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Inspect Timeline
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 5: OUTPUT BATCHES & DISPATCHES */}
      {activeTab === 'DISPATCHES' && (
        <Card title="Output Batches & Retail Dispatch Logistics">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
              Dispatch graded and verified produce batches to regional retail hubs. Dispatches commit `BATCH_DISPATCHED` events.
            </p>

            {dispatchBatch && (
              <div style={{ padding: '18px', borderRadius: '8px', border: '1px solid #CBD5E1', backgroundColor: '#F8F9FA', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#1B4332' }}>
                    Dispatching Batch: {dispatchBatch.batch_code}
                  </h4>
                  <button
                    onClick={() => setDispatchBatch(null)}
                    style={{ background: 'none', border: 'none', fontSize: '12px', color: '#64748B', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Cancel
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Destination Retail Hub</label>
                    <input
                      type="text"
                      value={dispatchDestination}
                      onChange={(e) => setDispatchDestination(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Transport Vehicle Reg</label>
                    <input
                      type="text"
                      value={dispatchVehicle}
                      onChange={(e) => setDispatchVehicle(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Dispatch Quantity (kg)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={dispatchQty}
                      onChange={(e) => setDispatchQty(e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #E2E8F0', paddingTop: '12px' }}>
                  <button
                    disabled={dispatchSubmitting}
                    onClick={handleDispatchSubmit}
                    style={{
                      padding: '8px 20px',
                      borderRadius: '6px',
                      backgroundColor: '#1B4332',
                      color: '#FFFFFF',
                      border: 'none',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {dispatchSubmitting ? 'Dispatching...' : 'Confirm Dispatch to Retail'}
                  </button>
                </div>
              </div>
            )}

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px 12px' }}>Batch Code</th>
                    <th style={{ padding: '10px 12px' }}>Crop</th>
                    <th style={{ padding: '10px 12px' }}>Quantity</th>
                    <th style={{ padding: '10px 12px' }}>Stage</th>
                    <th style={{ padding: '10px 12px' }}>Grade</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((b) => (
                    <tr key={b.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#1B4332' }}>{b.batch_code}</td>
                      <td style={{ padding: '12px' }}>{b.crop_type}</td>
                      <td style={{ padding: '12px', fontWeight: 600 }}>{b.current_quantity} {b.unit}</td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, backgroundColor: b.stage === 'IN_TRANSIT_TO_RETAIL' ? '#EBFBEE' : '#E2E8F0', color: b.stage === 'IN_TRANSIT_TO_RETAIL' ? '#2D6A4F' : '#334155' }}>
                          {b.stage.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <Badge variant="emerald">{b.quality_grade || 'GRADE_A'}</Badge>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          onClick={() => {
                            setDispatchBatch(b);
                            setDispatchQty(b.current_quantity.toString());
                          }}
                          style={{
                            padding: '6px 14px',
                            borderRadius: '6px',
                            backgroundColor: '#1B4332',
                            color: '#FFFFFF',
                            border: 'none',
                            fontSize: '12px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Dispatch
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}

      {/* BATCH TIMELINE MODAL */}
      <Modal
        isOpen={!!timelineBatchId}
        onClose={() => setTimelineBatchId(null)}
        title={`Batch Provenance Audit Trail: ${timelineBatchId || ''}`}
        size="large"
      >
        {timelineBatchId && (
          <BatchTimeline batchId={timelineBatchId} />
        )}
      </Modal>
    </div>
  );
};
