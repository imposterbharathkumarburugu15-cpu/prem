import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Store,
  QrCode,
  PackageCheck,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Clock,
  Layers,
  ArrowRight,
  Boxes,
  Truck,
  Printer,
  Download,
  FileText,
  AlertTriangle,
  Info,
  Check,
  Sliders,
  Eye,
  Tag,
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
import { PrintableLabelSheet } from '../components/common/PrintableLabelSheet';
import { BatchTimeline } from '../components/common/BatchTimeline';

export const RetailerWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Active view tab: 'INVENTORY' | 'RECEIPT_WORKFLOW' | 'QR_STUDIO'
  const [activeTab, setActiveTab] = useState<'INVENTORY' | 'RECEIPT_WORKFLOW' | 'QR_STUDIO'>('INVENTORY');

  // Selected items
  const [selectedBatch, setSelectedBatch] = useState<any>(null);
  const [timelineBatchId, setTimelineBatchId] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // 5-STEP RETAILER RECEIPT WORKFLOW STATE
  // ---------------------------------------------------------------------------
  const [workflowStep, setWorkflowStep] = useState(0);
  const [submittingWorkflow, setSubmittingWorkflow] = useState(false);

  // Step 1: Incoming batch selection
  const [receiptBatchId, setReceiptBatchId] = useState('');

  // Step 2: Inventory & Reception info
  const [manifestWeight, setManifestWeight] = useState('200.0');
  const [actualWeight, setActualWeight] = useState('200.0');
  const [receiverName, setReceiverName] = useState('Pooja Sharma (Store Manager)');
  const [shelfLocation, setShelfLocation] = useState('Aisle 4, Shelf Bay B');
  const [targetUnits, setTargetUnits] = useState('400');
  const [unitPriceInr, setUnitPriceInr] = useState('120.0');

  // Step 3: Receipt evidence (optional)
  const [receiptEvidence, setReceiptEvidence] = useState<{
    file: File | null;
    metadata: EvidenceMetadata | null;
  }>({ file: null, metadata: null });

  // Step 4: Verification check
  const [tamperSealStatus, setTamperSealStatus] = useState('VERIFIED_INTACT');
  const [containerCondition, setContainerCondition] = useState('CLEAN_UNCOMPROMISED');
  const [sealTagNumber, setSealTagNumber] = useState('SEAL-TX-8821');
  const [coldChainStatus, setColdChainStatus] = useState('OPTIMAL');
  const [inspectionNotes, setInspectionNotes] = useState('All tamper seals checked authentic. Produce color and quality certified.');

  // ---------------------------------------------------------------------------
  // DEDICATED QR GENERATION WORKSPACE STATE (Section 21.6)
  // ---------------------------------------------------------------------------
  const [qrBatchId, setQrBatchId] = useState('');
  const [qrSku, setQrSku] = useState('SKU-PRM-COTTON-500G');
  const [qrUnitWeight, setQrUnitWeight] = useState('0.5');
  const [qrQuantity, setQrQuantity] = useState(24);
  const [qrLabelSize, setQrLabelSize] = useState<'2x1' | '3x2' | '4x3'>('3x2');
  const [qrScanTarget, setQrScanTarget] = useState<'png' | 'verify'>('verify');
  const [mintingQr, setMintingQr] = useState(false);
  const [generatedQrResult, setGeneratedQrResult] = useState<any>(null);
  const [showPrintSheet, setShowPrintSheet] = useState(false);

  // QR Minting History
  const [qrHistory, setQrHistory] = useState<Array<{
    id: string;
    batchCode: string;
    sku: string;
    quantity: number;
    labelSize: string;
    token: string;
    timestamp: string;
  }>>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.getRetailerDashboard();
      setData(res);
      if (res.available_batches && res.available_batches.length > 0) {
        if (!selectedBatch) setSelectedBatch(res.available_batches[0]);
        if (!receiptBatchId) setReceiptBatchId(res.available_batches[0].id);
        if (!qrBatchId) setQrBatchId(res.available_batches[0].id);
      }
      if (res.inventory && res.inventory.length > 0) {
        const minted = res.inventory
          .filter((inv: any) => inv.opaque_qr_token)
          .map((inv: any) => ({
            id: inv.id,
            batchCode: inv.batch_code,
            sku: inv.sku || `SKU-PRM-${inv.crop_type}-500G`,
            quantity: 24,
            labelSize: '3x2',
            token: inv.opaque_qr_token,
            timestamp: inv.created_at ? new Date(inv.created_at).toLocaleString() : new Date().toLocaleString(),
          }));
        if (minted.length > 0) {
          setQrHistory(minted);
        }
      }
    } catch (err: any) {
      console.error('Failed to load retailer dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const availableBatches: any[] = data?.available_batches || [];
  const inventory: any[] = data?.inventory || [];

  // ---------------------------------------------------------------------------
  // 5-STEP RETAILER RECEIPT WORKFLOW HANDLER
  // ---------------------------------------------------------------------------
  const receiptSteps: FormStep[] = [
    { id: 0, label: 'Incoming Batch', description: 'Select arrival' },
    { id: 1, label: 'Inventory Info', description: 'Weights & Bay' },
    { id: 2, label: 'Receipt Evidence', description: 'Optional slip' },
    { id: 3, label: 'Verification Check', description: 'Tamper seals' },
    { id: 4, label: 'Confirm & Commit', description: 'Sign & Ledger' },
  ];

  const handleExecuteReceiptWorkflow = async () => {
    setSubmittingWorkflow(true);
    try {
      const activeLot = availableBatches.find((b) => b.id === receiptBatchId) || availableBatches[0];
      const payload = {
        batch_id: activeLot.id,
        batch_code: activeLot.batch_code,
        ordered_quantity: parseFloat(actualWeight) || 200,
        manifest_weight_kg: parseFloat(manifestWeight) || 200,
        receiver_name: receiverName,
        shelf_location: shelfLocation,
        units_allocated: parseInt(targetUnits, 10) || 400,
        unit_price_inr: parseFloat(unitPriceInr) || 120,
        tamper_seal_status: tamperSealStatus,
        container_condition: containerCondition,
        seal_tag_number: sealTagNumber,
        notes: inspectionNotes,
        received_at: new Date().toISOString(),
      };

      // 1. Record Procurement
      await api.createProcurementOrder(payload);

      // 2. Business Event: RETAIL_RECEIPT_CONFIRMED
      await api.recordBusinessEvent({
        event_type: 'RETAIL_RECEIPT_CONFIRMED',
        entity_type: 'BATCH',
        entity_id: activeLot.id,
        batch_id: activeLot.id,
        payload,
        evidence_file: receiptEvidence.file,
        evidence_metadata: receiptEvidence.metadata,
        notes: `Retail produce receipt confirmed. ${payload.units_allocated} units placed at ${shelfLocation}.`,
      });

      // 3. Business Event: PACKAGING_VERIFIED
      await api.recordBusinessEvent({
        event_type: 'PACKAGING_VERIFIED',
        entity_type: 'BATCH',
        entity_id: activeLot.id,
        batch_id: activeLot.id,
        payload: {
          tamper_seal_status: tamperSealStatus,
          seal_tag_number: sealTagNumber,
          container_condition: containerCondition,
          cold_chain_status: coldChainStatus,
        },
        notes: `Packaging verified: Seal ${tamperSealStatus}, Container ${containerCondition}.`,
      });

      setActionMsg({
        type: 'success',
        text: `Batch ${activeLot.batch_code} successfully verified and received into retail inventory.`,
      });
      setWorkflowStep(0);
      setActiveTab('INVENTORY');
      await fetchData();
    } catch (err: any) {
      setActionMsg({ type: 'error', text: `Receipt workflow failed: ${err.message}` });
    } finally {
      setSubmittingWorkflow(false);
    }
  };

  // ---------------------------------------------------------------------------
  // DEDICATED QR GENERATION WORKSPACE (Section 21.6)
  // ---------------------------------------------------------------------------
  const currentQrBatch = availableBatches.find((b) => b.id === qrBatchId) || availableBatches[0];
  const isQrBatchEligible = currentQrBatch ? currentQrBatch.eligible_for_qr !== false : true;

  const handleMintProvenanceQr = async () => {
    if (!currentQrBatch || !isQrBatchEligible) return;
    setMintingQr(true);
    try {
      const res = await api.generateRetailerQr({
        batch_id: currentQrBatch.id,
        package_sku: qrSku,
        package_weight_kg: parseFloat(qrUnitWeight) || 0.5,
      });

      // Record business event
      await api.recordBusinessEvent({
        event_type: 'QR_GENERATED',
        entity_type: 'BATCH',
        entity_id: currentQrBatch.id,
        batch_id: currentQrBatch.id,
        payload: {
          sku: qrSku,
          package_weight_kg: parseFloat(qrUnitWeight) || 0.5,
          quantity: qrQuantity,
          label_size: qrLabelSize,
          qr_token: res.opaque_qr_token,
        },
        notes: `Minted ${qrQuantity} consumer provenance QR stickers for SKU ${qrSku}.`,
      });

      setGeneratedQrResult(res);

      // Add to local generation history
      const newHistoryItem = {
        id: 'qr-hist-' + Date.now(),
        batchCode: currentQrBatch.batch_code || currentQrBatch.id,
        sku: qrSku,
        quantity: qrQuantity,
        labelSize: qrLabelSize,
        token: res.opaque_qr_token,
        timestamp: new Date().toLocaleString(),
      };
      setQrHistory((prev) => [newHistoryItem, ...prev]);

      setActionMsg({
        type: 'success',
        text: `Minted QR label set (${qrQuantity} labels, size ${qrLabelSize}) for ${qrSku}.`,
      });
    } catch (err: any) {
      setActionMsg({ type: 'error', text: `Failed to mint QR provenance: ${err.message}` });
    } finally {
      setMintingQr(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* WORKSPACE HEADER */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#111827', margin: 0 }}>
            Retailer Store Operations & Provenance Command
          </h1>
          <p style={{ fontSize: '14px', color: '#64748B', marginTop: '4px' }}>
            Receive certified produce batches, audit tamper-evident packaging, and mint consumer QR provenance labels.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('RECEIPT_WORKFLOW')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '6px',
              backgroundColor: activeTab === 'RECEIPT_WORKFLOW' ? '#1B4332' : '#FFFFFF',
              color: activeTab === 'RECEIPT_WORKFLOW' ? '#FFFFFF' : '#374151',
              border: '1px solid #D1D5DB',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <PackageCheck size={15} />
            <span>5-Step Produce Intake</span>
          </button>

          <button
            onClick={() => setActiveTab('QR_STUDIO')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              backgroundColor: activeTab === 'QR_STUDIO' ? '#1B4332' : '#1B4332',
              color: '#FFFFFF',
              border: 'none',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 1px 3px rgba(27, 67, 50, 0.25)',
            }}
          >
            <QrCode size={15} />
            <span>QR Provenance Studio</span>
          </button>

          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E5E7EB',
              borderRadius: '6px',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              color: '#374151',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ACTION FEEDBACK BANNER */}
      {actionMsg && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '6px',
            backgroundColor: actionMsg.type === 'success' ? '#EBF8EE' : '#FEF2F2',
            border: `1px solid ${actionMsg.type === 'success' ? '#D8F3DC' : '#FECACA'}`,
            color: actionMsg.type === 'success' ? '#1B4332' : '#B91C1C',
            fontSize: '13px',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{actionMsg.text}</span>
          <button
            onClick={() => setActionMsg(null)}
            style={{ color: 'inherit', fontWeight: 700, padding: '2px 8px', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}

      {/* DASHBOARD KPI CARDS */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
        }}
      >
        <StatMetric
          label="Incoming Dispatched Lots"
          value={availableBatches.length}
          subValue="Awaiting store intake"
          icon={Truck}
          variant="warning"
        />
        <StatMetric
          label="Store Active SKUs"
          value={inventory.length}
          subValue="Available on retail shelf"
          icon={Boxes}
          variant="navy"
        />
        <StatMetric
          label="Verified Lots on Ledger"
          value={availableBatches.filter((b) => b.status === 'VERIFIED').length}
          subValue="100% tamper verified"
          icon={ShieldCheck}
          variant="emerald"
        />
        <StatMetric
          label="Consumer QRs Minted"
          value={qrHistory.reduce((acc, curr) => acc + curr.quantity, 0)}
          subValue="Cryptographically anchored"
          icon={QrCode}
          variant="info"
        />
      </div>

      {/* TABS NAVIGATION */}
      <div style={{ display: 'flex', borderBottom: '1px solid #E5E7EB', gap: '8px' }}>
        {[
          { id: 'INVENTORY', label: 'Inventory & Incoming Lots', icon: Boxes },
          { id: 'RECEIPT_WORKFLOW', label: '5-Step Retailer Receipt', icon: PackageCheck },
          { id: 'QR_STUDIO', label: 'QR Provenance Workspace (Section 21.6)', icon: QrCode },
        ].map((tab) => {
          const TabIcon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 16px',
                fontSize: '13px',
                fontWeight: isActive ? 700 : 500,
                color: isActive ? '#1B4332' : '#64748B',
                borderBottom: isActive ? '2px solid #1B4332' : '2px solid transparent',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                marginBottom: '-1px',
              }}
            >
              <TabIcon size={15} color={isActive ? '#1B4332' : '#94A3B8'} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ======================================================================= */}
      {/* TAB 1: INVENTORY & INCOMING LOTS                                        */}
      {/* ======================================================================= */}
      {activeTab === 'INVENTORY' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* INCOMING BATCHES TABLE */}
          <Card
            title="Incoming Dispatched Batches"
            subtitle="Batches dispatched from regional hubs awaiting retail receipt verification"
            badge={<Badge variant="warning">{availableBatches.length} Available</Badge>}
            noPadding
          >
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ backgroundColor: '#F8F9FA', borderBottom: '1px solid #E5E7EB', color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
                    <th style={{ padding: '12px 16px' }}>Batch Code</th>
                    <th style={{ padding: '12px 16px' }}>Crop Commodity</th>
                    <th style={{ padding: '12px 16px' }}>Certified Grade</th>
                    <th style={{ padding: '12px 16px' }}>Manifest Quantity</th>
                    <th style={{ padding: '12px 16px' }}>Origin Cluster</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {availableBatches.map((b) => (
                    <tr key={b.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ fontWeight: 700, color: '#111827' }}>{b.batch_code || b.id}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>
                          Status: <span style={{ color: '#1B4332', fontWeight: 600 }}>{b.status}</span>
                        </div>
                      </td>

                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#111827' }}>
                        {b.crop_type}
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <Badge variant="emerald">{b.quality_grade || 'Grade A'}</Badge>
                      </td>

                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#111827' }}>
                        {b.quantity} KG
                      </td>

                      <td style={{ padding: '14px 16px', color: '#4B5563' }}>
                        {b.origin || 'Adilabad Regional Hub'}
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                          <button
                            onClick={() => setTimelineBatchId(b.id || b.batch_code)}
                            style={{
                              padding: '5px 8px',
                              borderRadius: '4px',
                              backgroundColor: '#FFFFFF',
                              border: '1px solid #CBD5E1',
                              color: '#334155',
                              fontSize: '11px',
                              fontWeight: 500,
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Layers size={11} /> Timeline
                          </button>

                          <button
                            onClick={() => {
                              setReceiptBatchId(b.id);
                              setManifestWeight(String(b.quantity || 200));
                              setActualWeight(String(b.quantity || 200));
                              setWorkflowStep(0);
                              setActiveTab('RECEIPT_WORKFLOW');
                            }}
                            style={{
                              padding: '5px 10px',
                              borderRadius: '4px',
                              backgroundColor: '#1B4332',
                              color: '#FFFFFF',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <PackageCheck size={11} /> Start Receipt
                          </button>

                          <button
                            onClick={() => {
                              setQrBatchId(b.id);
                              setActiveTab('QR_STUDIO');
                            }}
                            style={{
                              padding: '5px 10px',
                              borderRadius: '4px',
                              backgroundColor: '#FFFFFF',
                              border: '1px solid #1B4332',
                              color: '#1B4332',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <QrCode size={11} /> Mint QR
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* STORE INVENTORY TABLE */}
          <Card
            title="Store Shelf Inventory"
            subtitle="Catalog of verified produce SKUs ready for consumer purchase"
            badge={<Badge variant="navy">{inventory.length} Active SKUs</Badge>}
            noPadding
          >
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ backgroundColor: '#F8F9FA', borderBottom: '1px solid #E5E7EB', color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
                    <th style={{ padding: '12px 16px' }}>SKU Code & Batch</th>
                    <th style={{ padding: '12px 16px' }}>Store Bay Location</th>
                    <th style={{ padding: '12px 16px' }}>Units in Stock</th>
                    <th style={{ padding: '12px 16px' }}>Price / Unit</th>
                    <th style={{ padding: '12px 16px' }}>Shelf Status</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {inventory.map((inv) => (
                    <tr key={inv.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ fontWeight: 700, color: '#111827' }}>{inv.sku}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>
                          Batch: {inv.batch_code}
                        </div>
                      </td>

                      <td style={{ padding: '14px 16px', color: '#4B5563' }}>
                        {inv.storage_location}
                      </td>

                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#111827' }}>
                        {inv.units_available} Units ({inv.unit_weight_kg} KG)
                      </td>

                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#1B4332' }}>
                        ₹{inv.price_inr}
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <Badge variant="emerald">{inv.status}</Badge>
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <button
                          onClick={() => {
                            setQrBatchId(inv.batch_code);
                            setQrSku(inv.sku);
                            setActiveTab('QR_STUDIO');
                          }}
                          style={{
                            padding: '5px 10px',
                            borderRadius: '4px',
                            backgroundColor: '#1B4332',
                            color: '#FFFFFF',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <QrCode size={11} /> Generate Stickers
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 2: 5-STEP RETAILER RECEIPT WORKFLOW                                 */}
      {/* ======================================================================= */}
      {activeTab === 'RECEIPT_WORKFLOW' && (
        <Card
          title="5-Step Retailer Receipt & Inventory Intake Workflow"
          subtitle="Guided verification workflow for intake, seal authentication, and inventory placement"
        >
          <MultiStepForm
            steps={receiptSteps}
            currentStep={workflowStep}
            onStepChange={(step) => setWorkflowStep(step)}
            onNext={() => setWorkflowStep((prev) => Math.min(prev + 1, receiptSteps.length - 1))}
            onPrev={() => setWorkflowStep((prev) => Math.max(prev - 1, 0))}
            onSubmit={handleExecuteReceiptWorkflow}
            submitting={submittingWorkflow}
            submitLabel="Commit Receipt to Ledger"
            nextLabel="Continue to Next Step"
            cancelButton={
              <button
                type="button"
                onClick={() => setActiveTab('INVENTORY')}
                style={{
                  padding: '8px 14px',
                  borderRadius: '6px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #D1D5DB',
                  color: '#6B7280',
                  fontSize: '13px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
            }
          >
            {/* STEP 0: INCOMING BATCH SELECTION */}
            {workflowStep === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#111827', margin: 0 }}>
                  Step 1: Select Incoming Batch for Store Check-In
                </h4>
                <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                  Select the arrived produce shipment from the collection hub dispatch queue.
                </p>

                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '6px' }}>
                    Select Arrived Lot
                  </label>
                  <select
                    value={receiptBatchId}
                    onChange={(e) => {
                      setReceiptBatchId(e.target.value);
                      const target = availableBatches.find((b) => b.id === e.target.value);
                      if (target) {
                        setManifestWeight(String(target.quantity || 200));
                        setActualWeight(String(target.quantity || 200));
                      }
                    }}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                  >
                    {availableBatches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_code || b.id} — {b.crop_type} ({b.quantity} KG, {b.quality_grade})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Batch overview card */}
                {(() => {
                  const b = availableBatches.find((item) => item.id === receiptBatchId) || availableBatches[0];
                  return (
                    <div style={{ padding: '14px', backgroundColor: '#F8F9FA', borderRadius: '6px', border: '1px solid #E5E7EB', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', fontSize: '12px' }}>
                      <div>
                        <span style={{ color: '#64748B', display: 'block' }}>Crop Commodity</span>
                        <strong style={{ color: '#111827', fontSize: '13px' }}>{b.crop_type}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748B', display: 'block' }}>Quality Certification</span>
                        <Badge variant="emerald">{b.quality_grade || 'Grade A'}</Badge>
                      </div>
                      <div>
                        <span style={{ color: '#64748B', display: 'block' }}>Manifest Quantity</span>
                        <strong style={{ color: '#111827', fontSize: '13px' }}>{b.quantity} KG</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748B', display: 'block' }}>Provenance Lineage</span>
                        <span style={{ color: '#1B4332', fontWeight: 600 }}>Unbroken Farm-to-Hub</span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* STEP 1: INVENTORY & RECEPTION INFO */}
            {workflowStep === 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#111827', margin: 0 }}>
                  Step 2: Reception & Store Inventory Allocation
                </h4>
                <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                  Verify intake quantities against the transport manifest and designate shelf location.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Manifest Weight (KG)
                    </label>
                    <input
                      type="number"
                      value={manifestWeight}
                      onChange={(e) => setManifestWeight(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Actual Measured Weight on Dock (KG)
                    </label>
                    <input
                      type="number"
                      value={actualWeight}
                      onChange={(e) => setActualWeight(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Store Receiving Manager
                    </label>
                    <input
                      type="text"
                      value={receiverName}
                      onChange={(e) => setReceiverName(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Designated Storage Bay / Shelf
                    </label>
                    <input
                      type="text"
                      value={shelfLocation}
                      onChange={(e) => setShelfLocation(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Allocated Packaged Units
                    </label>
                    <input
                      type="number"
                      value={targetUnits}
                      onChange={(e) => setTargetUnits(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Consumer Retail Price (INR)
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      value={unitPriceInr}
                      onChange={(e) => setUnitPriceInr(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: RECEIPT EVIDENCE */}
            {workflowStep === 2 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#111827', margin: 0 }}>
                  Step 3: Receipt Supporting Evidence (Optional)
                </h4>
                <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                  Attach optional delivery invoice, signed consignment note, or intake dock photo.
                </p>

                <ContextualEvidenceCapture
                  label="Delivery Challan & Dock Intake Photo"
                  actionName="RETAIL_RECEIPT_CONFIRMED"
                  evidenceType="DOCUMENT"
                  required={false}
                  description="Optional photo of the signed physical delivery manifest or unloaded crates."
                  onEvidenceCaptured={({ file, metadata }) => {
                    setReceiptEvidence({ file, metadata });
                  }}
                />
              </div>
            )}

            {/* STEP 3: VERIFICATION CHECK */}
            {workflowStep === 3 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#111827', margin: 0 }}>
                  Step 4: Physical Security & Tamper Seal Verification
                </h4>
                <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                  Verify that security seals from transport and collection hub are intact and uncompromised.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Tamper Seal Status
                    </label>
                    <select
                      value={tamperSealStatus}
                      onChange={(e) => setTamperSealStatus(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    >
                      <option value="VERIFIED_INTACT">Verified 100% Intact & Untampered</option>
                      <option value="SEAL_REPLACED_AUTHORIZED">Authorized Replacement Seal</option>
                      <option value="SUSPECTED_TAMPER">Suspected Seal Compromise</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Security Seal Tag Number
                    </label>
                    <input
                      type="text"
                      value={sealTagNumber}
                      onChange={(e) => setSealTagNumber(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Container Condition
                    </label>
                    <select
                      value={containerCondition}
                      onChange={(e) => setContainerCondition(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    >
                      <option value="CLEAN_UNCOMPROMISED">Clean & Uncompromised</option>
                      <option value="MINOR_SCUFFS">Minor Scuffs / Outer Box Wear</option>
                      <option value="DAMAGED_CRATE">Damaged Exterior Crate</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Cold Chain Temperature Status
                    </label>
                    <select
                      value={coldChainStatus}
                      onChange={(e) => setColdChainStatus(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    >
                      <option value="OPTIMAL">Optimal (2°C - 8°C Verified)</option>
                      <option value="AMBIENT_SUITABLE">Ambient Temperature Suitable</option>
                      <option value="EXCURSION_NOTED">Temperature Excursion Noted</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                    Inspection Findings Notes
                  </label>
                  <textarea
                    rows={2}
                    value={inspectionNotes}
                    onChange={(e) => setInspectionNotes(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                  />
                </div>
              </div>
            )}

            {/* STEP 4: CONFIRM & COMMIT */}
            {workflowStep === 4 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#111827', margin: 0 }}>
                  Step 5: Review & Commit Receipt to Ledger
                </h4>
                <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                  Review all parameters before anchoring the business event to the immutable provenance ledger.
                </p>

                <div style={{ padding: '16px', backgroundColor: '#F8F9FA', borderRadius: '8px', border: '1px solid #E5E7EB', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '6px' }}>
                    <span style={{ color: '#64748B' }}>Target Batch Code:</span>
                    <strong style={{ color: '#111827' }}>{receiptBatchId}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '6px' }}>
                    <span style={{ color: '#64748B' }}>Verified Intake Weight:</span>
                    <strong style={{ color: '#1B4332' }}>{actualWeight} KG</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '6px' }}>
                    <span style={{ color: '#64748B' }}>Inventory Placement:</span>
                    <span style={{ color: '#111827' }}>{shelfLocation} ({targetUnits} units @ ₹{unitPriceInr})</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '6px' }}>
                    <span style={{ color: '#64748B' }}>Tamper Security Seal:</span>
                    <span style={{ color: '#1B4332', fontWeight: 600 }}>{tamperSealStatus} ({sealTagNumber})</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748B' }}>Cryptographic Proof:</span>
                    <span style={{ fontFamily: 'monospace', color: '#1B4332' }}>SHA-256 Verified Envelope</span>
                  </div>
                </div>
              </div>
            )}
          </MultiStepForm>
        </Card>
      )}

      {/* ======================================================================= */}
      {/* TAB 3: DEDICATED QR GENERATION WORKSPACE (Section 21.6)                  */}
      {/* ======================================================================= */}
      {activeTab === 'QR_STUDIO' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Card
            title="Dedicated QR Provenance Studio"
            subtitle="Mint cryptographically signed consumer QR label stickers linking directly to tamper-evident public proofs"
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
              {/* LEFT: CONFIGURATION CONTROLS */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* 1. Eligible Batch Selector */}
                <div>
                  <label style={{ fontSize: '13px', fontWeight: 700, color: '#111827', display: 'block', marginBottom: '6px' }}>
                    1. Select Verified Produce Batch
                  </label>
                  <select
                    value={qrBatchId}
                    onChange={(e) => setQrBatchId(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                  >
                    {availableBatches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_code || b.id} — {b.crop_type} ({b.status})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Ineligibility Warning if applicable */}
                {!isQrBatchEligible && currentQrBatch?.ineligible_reason && (
                  <div
                    style={{
                      padding: '12px 14px',
                      backgroundColor: '#FFFBEB',
                      borderRadius: '6px',
                      border: '1px solid #FDE68A',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px',
                    }}
                  >
                    <AlertTriangle size={16} color="#B45309" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <strong style={{ fontSize: '13px', color: '#92400E', display: 'block' }}>
                        Batch Ineligible for QR Provenance Minting
                      </strong>
                      <span style={{ fontSize: '12px', color: '#B45309', marginTop: '2px', display: 'block' }}>
                        {currentQrBatch.ineligible_reason}
                      </span>
                    </div>
                  </div>
                )}

                {/* 2. Verification Checklist */}
                <div style={{ padding: '14px', backgroundColor: '#F8F9FA', borderRadius: '6px', border: '1px solid #E5E7EB' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#111827', display: 'block', marginBottom: '8px' }}>
                    Provenance Audit Checklist
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={14} color="#1B4332" />
                      <span style={{ color: '#111827' }}>Harvest Origin & Seed Certification Confirmed</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={14} color="#1B4332" />
                      <span style={{ color: '#111827' }}>Collection Hub Quality Lab Grade A Certified</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={14} color="#1B4332" />
                      <span style={{ color: '#111827' }}>Retail Packaging & Tamper Seals Authenticated</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={14} color="#1B4332" />
                      <span style={{ color: '#111827' }}>Mass-Balance Calculations Verified (Zero Discrepancy)</span>
                    </div>
                  </div>
                </div>

                {/* 3. SKU & Unit Weight */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Package SKU Identifier
                    </label>
                    <input
                      type="text"
                      value={qrSku}
                      onChange={(e) => setQrSku(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Package Unit Net Weight
                    </label>
                    <input
                      type="text"
                      value={qrUnitWeight}
                      onChange={(e) => setQrUnitWeight(e.target.value)}
                      placeholder="e.g. 0.5 KG"
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    />
                  </div>
                </div>

                {/* 4. Package Quantity & Label Size */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Package Sticker Quantity
                    </label>
                    <select
                      value={qrQuantity}
                      onChange={(e) => setQrQuantity(parseInt(e.target.value, 10))}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                    >
                      <option value={12}>12 Sticker Labels</option>
                      <option value={24}>24 Sticker Labels</option>
                      <option value={48}>48 Sticker Labels</option>
                      <option value={96}>96 Sticker Labels</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
                      Label Adhesive Size
                    </label>
                    <div style={{ display: 'flex', border: '1px solid #D1D5DB', borderRadius: '6px', overflow: 'hidden' }}>
                      {(['2x1', '3x2', '4x3'] as const).map((sz) => (
                        <button
                          key={sz}
                          type="button"
                          onClick={() => setQrLabelSize(sz)}
                          style={{
                            flex: 1,
                            padding: '8px 4px',
                            fontSize: '12px',
                            fontWeight: qrLabelSize === sz ? 700 : 500,
                            backgroundColor: qrLabelSize === sz ? '#1B4332' : '#FFFFFF',
                            color: qrLabelSize === sz ? '#FFFFFF' : '#4B5563',
                            border: 'none',
                            cursor: 'pointer',
                          }}
                        >
                          {sz}"
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Minting Trigger */}
                <button
                  type="button"
                  onClick={handleMintProvenanceQr}
                  disabled={mintingQr || !isQrBatchEligible}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '12px 20px',
                    borderRadius: '8px',
                    backgroundColor: isQrBatchEligible ? '#1B4332' : '#9CA3AF',
                    color: '#FFFFFF',
                    fontSize: '14px',
                    fontWeight: 700,
                    cursor: isQrBatchEligible && !mintingQr ? 'pointer' : 'not-allowed',
                    border: 'none',
                    boxShadow: isQrBatchEligible ? '0 2px 4px rgba(27, 67, 50, 0.25)' : 'none',
                    marginTop: '8px',
                  }}
                >
                  <QrCode size={16} />
                  <span>{mintingQr ? 'Minting Cryptographic Tokens...' : `Mint ${qrQuantity} Provenance QR Labels`}</span>
                </button>
              </div>

              {/* RIGHT: DYNAMIC QR PREVIEW & PRINT SHEET */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div
                  style={{
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    backgroundColor: '#F8F9FA',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    textAlign: 'center',
                  }}
                >
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
                    Label Sticker Real-Time Preview ({qrLabelSize}")
                  </span>

                  {/* Single Label Card Preview */}
                  <div
                    style={{
                      width: '280px',
                      backgroundColor: '#FFFFFF',
                      border: '2px dashed #1B4332',
                      borderRadius: '8px',
                      padding: '14px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                      textAlign: 'left',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '6px', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <ShieldCheck size={14} color="#1B4332" />
                        <span style={{ fontSize: '11px', fontWeight: 800, color: '#1B4332' }}>PRAMAN PROVENANCE</span>
                      </div>
                      <span style={{ fontSize: '9px', fontFamily: 'monospace', color: '#64748B' }}>PKG-001</span>
                    </div>

                    {/* Active QR Token */}
                    {(() => {
                      const activeToken = generatedQrResult?.opaque_qr_token || qrHistory[0]?.token || inventory.find((i) => i.opaque_qr_token)?.opaque_qr_token || 'prm_3152005f74824af1b6b4715603f8b302';
                      return (
                        <>
                          <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
                            <div
                              style={{
                                width: '100px',
                                height: '100px',
                                backgroundColor: '#FFFFFF',
                                border: '2px solid #1B4332',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                                padding: '4px',
                                boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
                              }}
                            >
                              <img
                                key={`${activeToken}-${qrScanTarget}`}
                                src={`/api/v1/platform/retailer/qr-image/${activeToken}?target=${qrScanTarget}`}
                                alt="PRAMAN Scannable QR"
                                style={{ width: '92px', height: '92px', objectFit: 'contain' }}
                              />
                            </div>

                            <div style={{ flex: 1, minWidth: 0, fontSize: '12px' }}>
                              <div style={{ fontWeight: 800, color: '#111827', fontSize: '13px' }}>
                                {currentQrBatch?.crop_type || 'Organic Shankar-6 Cotton'}
                              </div>
                              <div style={{ color: '#4B5563', fontSize: '11px', marginTop: '2px' }}>
                                <strong>Batch:</strong> {currentQrBatch?.batch_code || 'BATCH-2026-001'}
                              </div>
                              <div style={{ color: '#4B5563', fontSize: '11px' }}>
                                <strong>Origin:</strong> Adilabad Organic Cluster
                              </div>
                              <div style={{ color: '#1B4332', fontWeight: 700, fontSize: '11px', marginTop: '2px' }}>
                                Net Wt: {qrUnitWeight} KG  |  {qrSku}
                              </div>
                              <div style={{ color: '#0369A1', fontSize: '10px', fontFamily: 'monospace', marginTop: '2px' }}>
                                Token: {activeToken.slice(0, 18)}...
                              </div>
                            </div>
                          </div>

                          {/* Scan with phone callout */}
                          <div
                            style={{
                              marginTop: '12px',
                              padding: '10px 12px',
                              backgroundColor: '#EBFBEE',
                              borderRadius: '6px',
                              border: '1px solid #B7EB8F',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px',
                              fontSize: '11px',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#1B4332', fontWeight: 700 }}>
                              <CheckCircle2 size={14} color="#1B4332" />
                              <span>Live Mobile Camera Scannable</span>
                            </div>
                            <span style={{ color: '#2D6A4F' }}>
                              Point your phone camera or QR scanner directly at this code. It delivers certified provenance data {qrScanTarget === 'png' ? 'in PNG format' : 'on the web portal'}!
                            </span>

                            {/* Scan Target Toggle */}
                            <div style={{ display: 'flex', gap: '12px', marginTop: '4px', paddingTop: '6px', borderTop: '1px solid #D3F9D8' }}>
                              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontWeight: 600, color: '#1B4332' }}>
                                <input
                                  type="radio"
                                  name="qrScanTarget"
                                  checked={qrScanTarget === 'png'}
                                  onChange={() => setQrScanTarget('png')}
                                />
                                Direct PNG Image
                              </label>
                              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontWeight: 600, color: '#1B4332' }}>
                                <input
                                  type="radio"
                                  name="qrScanTarget"
                                  checked={qrScanTarget === 'verify'}
                                  onChange={() => setQrScanTarget('verify')}
                                />
                                Web Portal
                              </label>
                            </div>
                          </div>

                          <div style={{ marginTop: '8px', paddingTop: '4px', borderTop: '1px solid #F3F4F6', display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#6B7280' }}>
                            <span>Scan to Verify</span>
                            <span style={{ color: '#1B4332', fontWeight: 700 }}>100% Tamper-Evident</span>
                          </div>
                        </>
                      );
                    })()}
                  </div>

                  {/* Actions after minting or direct sheet view */}
                  {(() => {
                    const activeToken =
                      generatedQrResult?.opaque_qr_token || qrHistory[0]?.token || inventory.find((i) => i.opaque_qr_token)?.opaque_qr_token || 'prm_3152005f74824af1b6b4715603f8b302';
                    return (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '16px', justifyContent: 'center' }}>
                        <a
                          href={`/api/v1/platform/retailer/certificate-image/${activeToken}`}
                          download={`praman-certificate-${activeToken}.png`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 14px',
                            borderRadius: '6px',
                            backgroundColor: '#1B4332',
                            color: '#FFFFFF',
                            fontSize: '12px',
                            fontWeight: 700,
                            textDecoration: 'none',
                          }}
                        >
                          <Download size={14} />
                          <span>Download Certificate (PNG)</span>
                        </a>

                        <a
                          href={`/api/v1/platform/retailer/qr-image/${activeToken}?target=${qrScanTarget}`}
                          download={`praman-qr-${activeToken}.png`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 14px',
                            borderRadius: '6px',
                            backgroundColor: '#0369A1',
                            color: '#FFFFFF',
                            fontSize: '12px',
                            fontWeight: 700,
                            textDecoration: 'none',
                          }}
                        >
                          <QrCode size={14} />
                          <span>Download QR Code (PNG)</span>
                        </a>

                        <button
                          type="button"
                          onClick={() => setShowPrintSheet(true)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 14px',
                            borderRadius: '6px',
                            backgroundColor: '#FFFFFF',
                            border: '1px solid #1B4332',
                            color: '#1B4332',
                            fontSize: '12px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <Printer size={14} />
                          <span>Print Label Sheet</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            window.open(`/verify/${activeToken}`, '_blank');
                          }}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 14px',
                            borderRadius: '6px',
                            backgroundColor: '#F8F9FA',
                            border: '1px solid #D1D5DB',
                            color: '#374151',
                            fontSize: '12px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <ExternalLink size={14} />
                          <span>Open Mobile View</span>
                        </button>
                      </div>
                    );
                  })()}
                </div>

                {/* Individual Serialized Package IDs Preview */}
                <div style={{ border: '1px solid #E5E7EB', borderRadius: '8px', padding: '14px', backgroundColor: '#FFFFFF' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#111827', display: 'block', marginBottom: '6px' }}>
                    Serialized Package ID Sequence ({qrQuantity} IDs)
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxHeight: '100px', overflowY: 'auto' }}>
                    {Array.from({ length: Math.min(qrQuantity, 16) }).map((_, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: '10px',
                          fontFamily: 'monospace',
                          backgroundColor: '#F8F9FA',
                          border: '1px solid #E5E7EB',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          color: '#374151',
                        }}
                      >
                        PKG-{(currentQrBatch?.batch_code || '001').slice(-3)}-{String(idx + 1).padStart(3, '0')}
                      </span>
                    ))}
                    {qrQuantity > 16 && (
                      <span style={{ fontSize: '10px', color: '#64748B', alignSelf: 'center' }}>
                        +{qrQuantity - 16} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* QR GENERATION AUDIT HISTORY */}
            <div style={{ marginTop: '24px', borderTop: '1px solid #E5E7EB', paddingTop: '20px' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#111827', marginBottom: '12px' }}>
                QR Provenance Minting Log
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#F8F9FA', borderBottom: '1px solid #E5E7EB', color: '#64748B', fontWeight: 600 }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Timestamp</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Batch Code</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>SKU</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Labels Minted</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Label Size</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Token Anchor</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {qrHistory.map((item) => (
                      <tr key={item.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                        <td style={{ padding: '10px 12px', color: '#64748B' }}>{item.timestamp}</td>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#111827' }}>{item.batchCode}</td>
                        <td style={{ padding: '10px 12px', color: '#374151' }}>{item.sku}</td>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#1B4332' }}>{item.quantity} Units</td>
                        <td style={{ padding: '10px 12px', color: '#4B5563' }}>{item.labelSize}"</td>
                        <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#64748B' }}>
                          {item.token.slice(0, 14)}...
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                          <button
                            onClick={() => setShowPrintSheet(true)}
                            style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              backgroundColor: '#FFFFFF',
                              border: '1px solid #D1D5DB',
                              fontSize: '11px',
                              cursor: 'pointer',
                            }}
                          >
                            Print Sheet
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ======================================================================= */}
      {/* MODAL: PRINTABLE LABEL SHEET PREVIEW                                    */}
      {/* ======================================================================= */}
      {showPrintSheet && (
        <Modal
          isOpen={showPrintSheet}
          onClose={() => setShowPrintSheet(false)}
          title="Printable QR Package Sticker Sheet"
          size="large"
        >
          <PrintableLabelSheet
            batchCode={currentQrBatch?.batch_code || 'BATCH-2026-001'}
            cropType={currentQrBatch?.crop_type || 'Shankar-6 Cotton'}
            qrToken={generatedQrResult?.opaque_qr_token || qrHistory[0]?.token || inventory.find((i) => i.opaque_qr_token)?.opaque_qr_token || 'prm_3152005f74824af1b6b4715603f8b302'}
            sku={qrSku}
            packageWeight={`${qrUnitWeight} KG`}
            labelSize={qrLabelSize}
            quantity={qrQuantity}
            farmOrigin={currentQrBatch?.origin || 'Green Valley FPO, Adilabad'}
            onClose={() => setShowPrintSheet(false)}
          />
        </Modal>
      )}

      {/* ======================================================================= */}
      {/* MODAL: SUPPLY CHAIN BATCH TIMELINE                                      */}
      {/* ======================================================================= */}
      {timelineBatchId && (
        <Modal
          isOpen={!!timelineBatchId}
          onClose={() => setTimelineBatchId(null)}
          title={`Chronological Provenance Timeline: ${timelineBatchId}`}
          size="large"
        >
          <BatchTimeline batchId={timelineBatchId} />
        </Modal>
      )}
    </div>
  );
};
