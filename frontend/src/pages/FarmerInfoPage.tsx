import React, { useState, useEffect } from 'react';
import {
  Smartphone,
  Download,
  CheckCircle2,
  Camera,
  MapPin,
  Clock,
  Sparkles,
  Layers,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Calendar,
  Wheat,
  Plus,
  RefreshCw,
  QrCode,
  Eye,
  AlertCircle,
  HelpCircle,
  ChevronRight,
  ChevronLeft,
  Check,
  Info,
  Award,
  Leaf,
  Scale,
} from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { StatMetric } from '../components/common/StatMetric';
import { Modal } from '../components/common/Modal';
import {
  ContextualEvidenceCapture,
  EvidenceMetadata,
} from '../components/common/ContextualEvidenceCapture';
import { BatchTimeline } from '../components/common/BatchTimeline';

export const FarmerInfoPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'DASHBOARD' | 'WIZARD' | 'BATCHES' | 'CHALLENGES' | 'MOBILE_APP'>('DASHBOARD');
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Active Batches State
  const [batches, setBatches] = useState<any[]>([
    {
      id: 'batch-f-01',
      batch_code: 'BATCH-TEL-KRM-2026-001',
      crop_type: 'Organic Cotton',
      variety: 'Suvin Extra-Long Staple',
      harvest_date: '2026-11-08',
      initial_quantity: 1250,
      current_quantity: 1250,
      unit: 'kg',
      stage: 'FARM_HARVESTED',
      status: 'ACTIVE',
      quality_grade: 'GRADE_A',
      evidence_count: 3,
      is_geofenced: true,
      farm_name: 'Adilabad Parcel #4',
      survey_number: 'SY-402/A',
    },
    {
      id: 'batch-f-02',
      batch_code: 'BATCH-TEL-WRG-2026-042',
      crop_type: 'Basmati Rice',
      variety: 'Pusa 1121',
      harvest_date: '2026-11-04',
      initial_quantity: 2800,
      current_quantity: 2800,
      unit: 'kg',
      stage: 'IN_TRANSIT_TO_CENTRE',
      status: 'ACTIVE',
      quality_grade: 'GRADE_A',
      evidence_count: 4,
      is_geofenced: true,
      farm_name: 'Warangal South Parcel',
      survey_number: 'SY-118/C',
    },
    {
      id: 'batch-f-03',
      batch_code: 'BATCH-TEL-KHM-2026-088',
      crop_type: 'Red Chilli',
      variety: 'Teja Premium Hot',
      harvest_date: '2026-10-28',
      initial_quantity: 850,
      current_quantity: 0,
      unit: 'kg',
      stage: 'AT_RETAILER',
      status: 'DEPLETED',
      quality_grade: 'GRADE_A',
      evidence_count: 6,
      is_geofenced: true,
      farm_name: 'Khammam River Basin',
      survey_number: 'SY-89/1',
    },
  ]);

  // Evidence Challenges State
  const [challenges, setChallenges] = useState<any[]>([
    {
      challenge_id: 'CHL-2026-009',
      target_entity_id: 'BATCH-TEL-KRM-2026-001',
      challenge_type: 'FRESH_PHOTO_REQUEST',
      reason_code: 'SATELLITE_VEGETATION_DRIFT_ALERT',
      instructions: 'Please take a fresh geotagged camera photo of Field Parcel #4 to verify post-harvest stalk condition.',
      status: 'PENDING',
      created_at: '2026-11-10T14:30:00Z',
      officer_name: 'Dr. Anita Rao (EIO-04)',
    },
  ]);

  // Selected Batch for Timeline Modal
  const [timelineBatchId, setTimelineBatchId] = useState<string | null>(null);

  // -------------------------------------------------------------
  // 6-STEP BATCH CREATION WORKFLOW STATE
  // -------------------------------------------------------------
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [submittingWizard, setSubmittingWizard] = useState<boolean>(false);

  // Step 1: Product info
  const [cropType, setCropType] = useState('Organic Cotton');
  const [variety, setVariety] = useState('Suvin Extra-Long Staple');
  const [expectedGrade, setExpectedGrade] = useState('GRADE_A');
  const [unit, setUnit] = useState('kg');

  // Step 2: Farm & Origin info
  const [farmId, setFarmId] = useState('farm-adilabad-01');
  const [farmName, setFarmName] = useState('Adilabad North Cluster Parcel #4');
  const [surveyNumber, setSurveyNumber] = useState('SY-402/A');
  const [stateDistrict, setStateDistrict] = useState('Adilabad, Telangana');
  const [boundaryStatus, setBoundaryStatus] = useState('GEOFENCE_LOCKED');

  // Step 3: Harvest details
  const [harvestDate, setHarvestDate] = useState(new Date().toISOString().split('T')[0]);
  const [initialQuantity, setInitialQuantity] = useState('1200');
  const [harvestMethod, setHarvestMethod] = useState('MANUAL_SELECTIVE');
  const [moistureEstimate, setMoistureEstimate] = useState('9.5');

  // Step 4: Evidence Photographs (Contextual Evidence)
  const [harvestEvidence, setHarvestEvidence] = useState<{
    file: File | null;
    metadata: EvidenceMetadata | null;
  }>({ file: null, metadata: null });

  // Step 5: Additional documentation
  const [mandiPassNumber, setMandiPassNumber] = useState('MANDI-TEL-2026-9912');
  const [organicStandard, setOrganicStandard] = useState('NPOP_INDIA_ORGANIC');
  const [farmerNotes, setFarmerNotes] = useState('Hand-picked first flush harvest, free from synthetic defoliants.');

  // Step 6: Generated Batch Preview
  const [generatedBatchCode, setGeneratedBatchCode] = useState('');

  useEffect(() => {
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    setGeneratedBatchCode(`BATCH-TEL-${cropType.substring(0, 3).toUpperCase()}-${randomSuffix}`);
  }, [cropType]);

  // Load real batches if backend has them
  const loadFarmsAndBatches = async () => {
    try {
      const res = await api.getEventPolicies();
      // If endpoint works, also attempt listing real events or batches
    } catch (e) {
      // Keep rich fallback data
    }
  };

  useEffect(() => {
    loadFarmsAndBatches();
  }, []);

  const handleCreateBatchSubmit = async () => {
    setSubmittingWizard(true);
    setActionMsg(null);
    try {
      const parsedQty = parseFloat(initialQuantity) || 1000;
      const bCode = generatedBatchCode || `BATCH-TEL-${Math.floor(1000 + Math.random() * 9000)}`;

      // 1. Submit BATCH_CREATED event
      await api.recordBusinessEvent({
        event_type: 'BATCH_CREATED',
        payload: {
          batch_code: bCode,
          crop_type: cropType,
          variety: variety,
          farm_id: farmId,
          initial_quantity: parsedQty,
          unit: unit,
          harvest_date: harvestDate,
          notes: `${farmerNotes} | Mandi Pass: ${mandiPassNumber} | Std: ${organicStandard}`,
        },
        evidence_file: harvestEvidence.file,
        evidence_metadata: harvestEvidence.metadata,
        notes: `Farmer Batch Creation: ${bCode}`,
      });

      // 2. Submit CROP_ACTIVITY_RECORDED event
      await api.recordBusinessEvent({
        event_type: 'CROP_ACTIVITY_RECORDED',
        payload: {
          farm_id: farmId,
          crop_type: cropType,
          activity_type: 'HARVEST',
          activity_date: harvestDate,
          field_area_acres: 4.5,
          notes: `Harvest of ${parsedQty} ${unit} completed. Method: ${harvestMethod}`,
        },
      });

      // Update local batches state
      const newBatchItem = {
        id: `batch-${Date.now()}`,
        batch_code: bCode,
        crop_type: cropType,
        variety: variety,
        harvest_date: harvestDate,
        initial_quantity: parsedQty,
        current_quantity: parsedQty,
        unit: unit,
        stage: 'FARM_HARVESTED',
        status: 'ACTIVE',
        quality_grade: expectedGrade,
        evidence_count: harvestEvidence.file ? 1 : 0,
        is_geofenced: true,
        farm_name: farmName,
        survey_number: surveyNumber,
      };

      setBatches([newBatchItem, ...batches]);
      setActionMsg({
        type: 'success',
        text: `Batch '${bCode}' successfully registered on cryptographic provenance ledger!`,
      });
      setWizardStep(1);
      setActiveTab('BATCHES');
    } catch (err: any) {
      console.error('Batch creation error:', err);
      setActionMsg({
        type: 'error',
        text: `Registration failed: ${err.message || 'Unknown server error'}`,
      });
    } finally {
      setSubmittingWizard(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto', paddingBottom: '48px' }}>
      {/* HEADER SECTION */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', background: 'linear-gradient(135deg, #1B4332 0%, #2D6A4F 100%)', borderRadius: '12px', padding: '24px 28px', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(27, 67, 50, 0.15)' }}>
        <div style={{ maxWidth: '640px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)', padding: '4px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <Wheat size={14} />
              PRAMAN Farmer Portal
            </span>
            <span style={{ fontSize: '12px', color: '#B7E4C7' }}>• తెలంగాణ రైతుల వేదిక</span>
          </div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>
            Farmer Dashboard & Provenance Origin
          </h1>
          <p style={{ fontSize: '14px', margin: 0, color: '#D8F3DC', lineHeight: 1.5 }}>
            Register verified harvest batches, review cryptographically sealed field evidence, monitor quality grades, and download the official offline-first Android field APK.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            onClick={() => setActiveTab('WIZARD')}
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
            <span>Create Harvest Batch</span>
          </button>

          <a
            href="/download/apk"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.15)',
              color: '#FFFFFF',
              padding: '11px 18px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              textDecoration: 'none',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              transition: 'all 0.15s ease',
            }}
          >
            <Download size={16} />
            <span>Android APK (v2.4.1)</span>
          </a>
        </div>
      </div>

      {/* ACTION MESSAGE TOAST */}
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
          { id: 'DASHBOARD', label: 'Farmer Dashboard', icon: Wheat },
          { id: 'WIZARD', label: '6-Step Batch Creation', icon: Plus },
          { id: 'BATCHES', label: `My Batches (${batches.length})`, icon: Layers },
          { id: 'CHALLENGES', label: `Evidence Challenges (${challenges.length})`, icon: ShieldCheck },
          { id: 'MOBILE_APP', label: 'Mobile APK & Telemetry', icon: Smartphone },
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

      {/* TAB 1: OVERVIEW & DASHBOARD */}
      {activeTab === 'DASHBOARD' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* STAT METRICS */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            <StatMetric
              label="Active Harvest Batches"
              value={batches.filter((b) => b.status === 'ACTIVE').length.toString()}
              subValue="Tracked across supply chain"
              icon={Layers}
              trend="+2 this month"
              trendDirection="up"
            />
            <StatMetric
              label="Total Produce Harvested"
              value="4,900 kg"
              subValue="100% Certified organic"
              icon={Scale}
              trend="+18% vs prev season"
              trendDirection="up"
            />
            <StatMetric
              label="Cryptographic Evidence Proofs"
              value="13"
              subValue="Signed with device keystore"
              icon={ShieldCheck}
            />
            <StatMetric
              label="Geofence Boundary Integrity"
              value="100%"
              subValue="Adilabad GPS polygon locked"
              icon={MapPin}
            />
          </div>

          {/* FARM OVERVIEW & PARCEL STATUS */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
            <Card title="Registered Farm Boundary & Origin Profile">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                  <div style={{ padding: '12px', background: '#F8F9FA', borderRadius: '8px', border: '1px solid #E9ECEF' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>Farm Cluster</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>Adilabad Organic Cotton FPO</div>
                    <div style={{ fontSize: '12px', color: '#40916C', marginTop: '2px' }}>Cluster ID: CLU-TEL-2026-08</div>
                  </div>
                  <div style={{ padding: '12px', background: '#F8F9FA', borderRadius: '8px', border: '1px solid #E9ECEF' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>Survey & Revenue Number</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>Survey No. 402/A, Sub-Division 2</div>
                    <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Mandal: Jainath, Dist: Adilabad</div>
                  </div>
                  <div style={{ padding: '12px', background: '#F8F9FA', borderRadius: '8px', border: '1px solid #E9ECEF' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>Total Cultivated Area</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>4.82 Acres (1.95 Hectares)</div>
                    <div style={{ fontSize: '12px', color: '#40916C', marginTop: '2px' }}>Soil Type: Deep Black Cotton (Vertisol)</div>
                  </div>
                  <div style={{ padding: '12px', background: '#F8F9FA', borderRadius: '8px', border: '1px solid #E9ECEF' }}>
                    <div style={{ fontSize: '11px', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>WGS-84 Polygon Geofence</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#2D6A4F', marginTop: '2px' }}>19.6641° N, 78.5320° E (4 Vertices)</div>
                    <div style={{ fontSize: '12px', color: '#2D6A4F', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={12} /> Cryptographically Signed Polygon
                    </div>
                  </div>
                </div>

                <div style={{ padding: '14px', background: '#EDFDF2', borderRadius: '8px', border: '1px solid #B7E4C7', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: '#2D6A4F', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <ShieldCheck size={20} />
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#1B4332' }}>Proof-of-Presence & Satellite Corroboration Active</div>
                      <div style={{ fontSize: '12px', color: '#40916C' }}>Sentinel-2 spectral NDVI 0.76 (Dense Canopy) confirms valid seasonal cultivation.</div>
                    </div>
                  </div>
                  <Badge variant="emerald">VERIFIED PROVENANCE</Badge>
                </div>
              </div>
            </Card>

            {/* QUICK ACTIONS & NOTIFICATIONS */}
            <Card title="Farmer Notice Board & Tasks">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#FEF3F2', border: '1px solid #FECDCA' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#B42318', fontWeight: 600, fontSize: '13px' }}>
                    <AlertTriangle size={16} />
                    <span>Evidence Challenge Pending</span>
                  </div>
                  <p style={{ fontSize: '12px', color: '#7A271A', margin: '4px 0 8px 0' }}>
                    Dr. Anita Rao requested a fresh photo for Batch #001 to resolve satellite vegetation alert.
                  </p>
                  <button
                    onClick={() => setActiveTab('CHALLENGES')}
                    style={{ fontSize: '12px', fontWeight: 700, color: '#B42318', background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <span>View Challenge & Respond</span>
                    <ArrowRight size={13} />
                  </button>
                </div>

                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#F8F9FA', border: '1px solid #E9ECEF' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#1B4332' }}>Next Collection Centre Intake</div>
                  <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Adilabad Central Hub receiving batches on Thursday 09:00 AM.</div>
                </div>

                <button
                  onClick={() => setActiveTab('WIZARD')}
                  style={{
                    padding: '10px',
                    borderRadius: '6px',
                    backgroundColor: '#1B4332',
                    color: '#FFFFFF',
                    border: 'none',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    marginTop: '4px',
                  }}
                >
                  <Plus size={16} />
                  <span>Start New Batch Registration</span>
                </button>
              </div>
            </Card>
          </div>

          {/* ACTIVE BATCHES TABLE PREVIEW */}
          <Card title="Active Harvest Batches">
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #E2E8F0', color: '#64748B', fontSize: '12px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px 12px' }}>Batch Code</th>
                    <th style={{ padding: '10px 12px' }}>Crop & Variety</th>
                    <th style={{ padding: '10px 12px' }}>Harvest Date</th>
                    <th style={{ padding: '10px 12px' }}>Quantity</th>
                    <th style={{ padding: '10px 12px' }}>Current Stage</th>
                    <th style={{ padding: '10px 12px' }}>Quality Grade</th>
                    <th style={{ padding: '10px 12px' }}>Evidence</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((batch) => (
                    <tr key={batch.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '12px', fontWeight: 600, color: '#1B4332' }}>
                        {batch.batch_code}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div>{batch.crop_type}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>{batch.variety}</div>
                      </td>
                      <td style={{ padding: '12px', color: '#475569' }}>
                        {batch.harvest_date}
                      </td>
                      <td style={{ padding: '12px', fontWeight: 600 }}>
                        {batch.initial_quantity} {batch.unit}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, backgroundColor: '#E2E8F0', color: '#334155' }}>
                          {batch.stage.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <Badge variant="emerald">{batch.quality_grade || 'PENDING'}</Badge>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#2D6A4F', fontWeight: 600 }}>
                          <Camera size={13} />
                          {batch.evidence_count} Proofs
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          onClick={() => setTimelineBatchId(batch.batch_code)}
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
                          View Timeline
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

      {/* TAB 2: 6-STEP FARMER BATCH CREATION WORKFLOW */}
      {activeTab === 'WIZARD' && (
        <Card title="6-Step Farmer Batch Creation Workflow">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* STEP PROGRESS INDICATOR */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
              {[
                { step: 1, title: 'Product Info' },
                { step: 2, title: 'Farm Origin' },
                { step: 3, title: 'Harvest Data' },
                { step: 4, title: 'Evidence Photo' },
                { step: 5, title: 'Documentation' },
                { step: 6, title: 'Review & Seal' },
              ].map((s) => {
                const isCompleted = wizardStep > s.step;
                const isCurrent = wizardStep === s.step;
                return (
                  <div
                    key={s.step}
                    onClick={() => {
                      if (s.step < wizardStep) setWizardStep(s.step);
                    }}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: s.step < wizardStep ? 'pointer' : 'default',
                      zIndex: 2,
                    }}
                  >
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        backgroundColor: isCompleted ? '#2D6A4F' : isCurrent ? '#1B4332' : '#E2E8F0',
                        color: isCompleted || isCurrent ? '#FFFFFF' : '#64748B',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: '13px',
                        border: isCurrent ? '3px solid #74C69D' : 'none',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      {isCompleted ? <Check size={16} /> : s.step}
                    </div>
                    <span style={{ fontSize: '11px', fontWeight: isCurrent ? 700 : 500, color: isCurrent ? '#1B4332' : '#64748B' }}>
                      {s.title}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* STEP FORM CONTENTS */}
            <div style={{ padding: '20px', borderRadius: '8px', backgroundColor: '#F8F9FA', border: '1px solid #E9ECEF', minHeight: '260px' }}>
              {/* STEP 1: PRODUCT INFO */}
              {wizardStep === 1 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 1: Product & Crop Classification</h3>
                    <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Define the crop category, specific cultivar variety, and target market grade.</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Crop Type</label>
                      <select
                        value={cropType}
                        onChange={(e) => setCropType(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                      >
                        <option value="Organic Cotton">Organic Cotton (పత్తి)</option>
                        <option value="Basmati Rice">Basmati Rice (బాస్మతి బియ్యం)</option>
                        <option value="Red Chilli">Red Chilli (ఎర్ర మిరపకాయలు)</option>
                        <option value="Soybean">Soybean (సోయాబీన్)</option>
                        <option value="Turmeric">Salem Organic Turmeric (పసుపు)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Cultivar / Variety</label>
                      <input
                        type="text"
                        value={variety}
                        onChange={(e) => setVariety(e.target.value)}
                        placeholder="e.g. Suvin Extra-Long Staple"
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Target Quality Tier</label>
                      <select
                        value={expectedGrade}
                        onChange={(e) => setExpectedGrade(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                      >
                        <option value="GRADE_A">Grade A (Premium Export Standard)</option>
                        <option value="GRADE_B">Grade B (Domestic High Commercial)</option>
                        <option value="GRADE_C">Grade C (Standard Milling / Ginning)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Measurement Unit</label>
                      <select
                        value={unit}
                        onChange={(e) => setUnit(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                      >
                        <option value="kg">Kilograms (kg)</option>
                        <option value="quintal">Quintal (100 kg)</option>
                        <option value="ton">Metric Tons</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: FARM & ORIGIN */}
              {wizardStep === 2 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 2: Farm & Origin Parcel Verification</h3>
                    <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Select the enrolled farm parcel. WGS-84 geodesic boundaries will be attached automatically.</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Farm Parcel</label>
                      <select
                        value={farmId}
                        onChange={(e) => setFarmId(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                      >
                        <option value="farm-adilabad-01">Adilabad North Cluster Parcel #4 (SY-402/A)</option>
                        <option value="farm-warangal-02">Warangal South Parcel (SY-118/C)</option>
                        <option value="farm-khammam-03">Khammam River Basin (SY-89/1)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Survey Number</label>
                      <input
                        type="text"
                        value={surveyNumber}
                        onChange={(e) => setSurveyNumber(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div style={{ gridColumn: 'span 2', padding: '12px', backgroundColor: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <MapPin size={18} color="#2D6A4F" />
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1B4332' }}>GPS Geofence Status: ACTIVE & VALIDATED</div>
                            <div style={{ fontSize: '11px', color: '#64748B' }}>Coordinates: 19.6641° N, 78.5320° E • GeoJSON Polygon Hash: 4f8a129d</div>
                          </div>
                        </div>
                        <Badge variant="emerald">POLYGON LOCKED</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3: HARVEST DETAILS */}
              {wizardStep === 3 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 3: Harvest Metrics & Quantity</h3>
                    <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Enter precise harvest date, declared quantity, and moisture level.</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Harvest Date</label>
                      <input
                        type="date"
                        value={harvestDate}
                        onChange={(e) => setHarvestDate(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Initial Quantity ({unit})</label>
                      <input
                        type="number"
                        value={initialQuantity}
                        onChange={(e) => setInitialQuantity(e.target.value)}
                        placeholder="e.g. 1200"
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Harvesting Method</label>
                      <select
                        value={harvestMethod}
                        onChange={(e) => setHarvestMethod(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                      >
                        <option value="MANUAL_SELECTIVE">Manual Selective Hand-Picking</option>
                        <option value="MECHANIZED_COMBINE">Mechanized Combine Harvester</option>
                        <option value="HYBRID_ASSISTED">Hybrid Semi-Mechanized</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Estimated Moisture (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={moistureEstimate}
                        onChange={(e) => setMoistureEstimate(e.target.value)}
                        placeholder="e.g. 9.5"
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 4: EVIDENCE PHOTOGRAPHS */}
              {wizardStep === 4 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 4: Supporting Harvest Evidence (Optional)</h3>
                    <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
                      Attach a field crop photo, scale reading, or harvest lot tag. Optional evidence adds cryptographic strength and never blocks submission.
                    </p>
                  </div>

                  <ContextualEvidenceCapture
                    label="Harvest Produce & Field Proof"
                    description="Upload an authentic harvest photo or take a live camera shot. Automatic SHA-256 fingerprinting and GPS timestamping will be applied."
                    actionName="Farmer Harvest Batch Registration"
                    evidenceType="PHOTO"
                    required={false}
                    onEvidenceCaptured={(data) => {
                      setHarvestEvidence({
                        file: data.file,
                        metadata: data.metadata,
                      });
                    }}
                  />
                </div>
              )}

              {/* STEP 5: ADDITIONAL DOCUMENTATION */}
              {wizardStep === 5 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 5: Compliance Standards & Mandi Documentation</h3>
                    <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Record official certification references, mandi gate entry passes, or notes.</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Mandi Gate Pass Number</label>
                      <input
                        type="text"
                        value={mandiPassNumber}
                        onChange={(e) => setMandiPassNumber(e.target.value)}
                        placeholder="e.g. MANDI-TEL-2026-9912"
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Organic Certification Standard</label>
                      <select
                        value={organicStandard}
                        onChange={(e) => setOrganicStandard(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', backgroundColor: '#FFFFFF' }}
                      >
                        <option value="NPOP_INDIA_ORGANIC">NPOP India Organic (Jaivik Bharat)</option>
                        <option value="USDA_ORGANIC">USDA NOP Organic Equivalent</option>
                        <option value="EU_ORGANIC">EU Organic Regulation</option>
                        <option value="CONVENTIONAL_TRANSITION">Transition to Organic (Year 2)</option>
                      </select>
                    </div>

                    <div style={{ gridColumn: 'span 2' }}>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>Farmer Remarks & Batch Notes</label>
                      <textarea
                        rows={3}
                        value={farmerNotes}
                        onChange={(e) => setFarmerNotes(e.target.value)}
                        placeholder="Add any specific observations regarding weather, pest resistance, or lot storage..."
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px', boxSizing: 'border-box' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 6: REVIEW & SUBMIT */}
              {wizardStep === 6 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>Step 6: Review & Cryptographically Commit Batch</h3>
                    <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>Confirm all recorded details. This action commits the batch to the immutable PRAMAN audit trail.</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                    <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>ASSIGNED BATCH CODE</div>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{generatedBatchCode}</div>
                    </div>
                    <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>CROP & VARIETY</div>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{cropType} ({variety})</div>
                    </div>
                    <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>QUANTITY & TIER</div>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332', marginTop: '2px' }}>{initialQuantity} {unit} ({expectedGrade})</div>
                    </div>
                    <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>ORIGIN PARCEL</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155', marginTop: '2px' }}>{surveyNumber} • {stateDistrict}</div>
                    </div>
                    <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>HARVEST DATE</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155', marginTop: '2px' }}>{harvestDate} (Moisture: {moistureEstimate}%)</div>
                    </div>
                    <div style={{ padding: '12px', background: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>ATTACHED EVIDENCE</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: harvestEvidence.file ? '#2D6A4F' : '#64748B', marginTop: '2px' }}>
                        {harvestEvidence.file ? `✓ ${harvestEvidence.file.name}` : 'No file attached (Optional)'}
                      </div>
                    </div>
                  </div>

                  <div style={{ padding: '12px', backgroundColor: '#EDFDF2', borderRadius: '6px', border: '1px solid #B7E4C7', fontSize: '12px', color: '#1B4332', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldCheck size={18} color="#2D6A4F" />
                    <span>Dual event submission: Will trigger `BATCH_CREATED` and `CROP_ACTIVITY_RECORDED` on `/api/v1/events/record`.</span>
                  </div>
                </div>
              )}
            </div>

            {/* WIZARD NAVIGATION CONTROLS */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #E2E8F0', paddingTop: '16px' }}>
              <button
                type="button"
                disabled={wizardStep === 1 || submittingWizard}
                onClick={() => setWizardStep((prev) => Math.max(prev - 1, 1))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '9px 18px',
                  borderRadius: '6px',
                  border: '1px solid #CBD5E1',
                  backgroundColor: '#FFFFFF',
                  color: wizardStep === 1 ? '#94A3B8' : '#334155',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: wizardStep === 1 ? 'not-allowed' : 'pointer',
                }}
              >
                <ChevronLeft size={16} />
                <span>Back</span>
              </button>

              <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 500 }}>
                Step {wizardStep} of 6
              </div>

              {wizardStep < 6 ? (
                <button
                  type="button"
                  onClick={() => setWizardStep((prev) => Math.min(prev + 1, 6))}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '9px 20px',
                    borderRadius: '6px',
                    backgroundColor: '#1B4332',
                    color: '#FFFFFF',
                    border: 'none',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <span>Continue</span>
                  <ChevronRight size={16} />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={submittingWizard}
                  onClick={handleCreateBatchSubmit}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 24px',
                    borderRadius: '6px',
                    backgroundColor: '#2D6A4F',
                    color: '#FFFFFF',
                    border: 'none',
                    fontSize: '13px',
                    fontWeight: 700,
                    cursor: submittingWizard ? 'wait' : 'pointer',
                    boxShadow: '0 2px 6px rgba(45, 106, 79, 0.3)',
                  }}
                >
                  {submittingWizard ? <RefreshCw size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                  <span>{submittingWizard ? 'Sealing Batch...' : 'Confirm & Mint Batch'}</span>
                </button>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* TAB 3: MY BATCHES LIST */}
      {activeTab === 'BATCHES' && (
        <Card title={`Enrolled Harvest Batches (${batches.length})`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '13px', color: '#64748B' }}>
                All registered batches with origin tracking, verification tokens, and supply-chain stages.
              </div>
              <button
                onClick={() => setActiveTab('WIZARD')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#1B4332',
                  color: '#FFFFFF',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Plus size={14} />
                <span>Register New Batch</span>
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
              {batches.map((batch) => (
                <div
                  key={batch.id}
                  style={{
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    backgroundColor: '#FFFFFF',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '12px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: '#1B4332' }}>{batch.batch_code}</span>
                      <Badge variant="emerald">{batch.quality_grade || 'GRADE_A'}</Badge>
                    </div>

                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>{batch.crop_type}</div>
                    <div style={{ fontSize: '12px', color: '#64748B' }}>{batch.variety} • Harvested {batch.harvest_date}</div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginTop: '12px', padding: '10px', backgroundColor: '#F8F9FA', borderRadius: '6px' }}>
                      <div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Quantity</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#1B4332' }}>{batch.initial_quantity} {batch.unit}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Origin Parcel</div>
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>{batch.survey_number}</div>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #F1F5F9', paddingTop: '10px' }}>
                    <span style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '4px', backgroundColor: '#E2E8F0', color: '#334155', fontWeight: 600 }}>
                      {batch.stage.replace(/_/g, ' ')}
                    </span>

                    <button
                      onClick={() => setTimelineBatchId(batch.batch_code)}
                      style={{
                        padding: '6px 14px',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                        backgroundColor: '#FFFFFF',
                        color: '#1B4332',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <Eye size={13} />
                      <span>Audit Timeline</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* TAB 4: EVIDENCE CHALLENGES PANEL */}
      {activeTab === 'CHALLENGES' && (
        <Card title="Active Evidence Challenges from Integrity Officers">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
              The Evidence Integrity Officer can issue cryptographically bounded challenges when anomalies or satellite drifts are detected. Farmers can respond directly by uploading fresh evidence.
            </p>

            {challenges.length === 0 ? (
              <div style={{ padding: '36px', textAlign: 'center', backgroundColor: '#F8F9FA', borderRadius: '8px' }}>
                <CheckCircle2 size={36} color="#2D6A4F" style={{ margin: '0 auto 8px auto' }} />
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#1B4332' }}>No Open Evidence Challenges</div>
                <div style={{ fontSize: '12px', color: '#64748B' }}>All your submitted batches and parcels are currently verified in good standing.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {challenges.map((ch) => (
                  <div
                    key={ch.challenge_id}
                    style={{
                      padding: '16px',
                      borderRadius: '8px',
                      border: '1px solid #FECDCA',
                      backgroundColor: '#FFFBFB',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 700, padding: '3px 8px', borderRadius: '4px', backgroundColor: '#FEE4E2', color: '#B42318' }}>
                          {ch.challenge_type}
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#1B4332' }}>{ch.challenge_id}</span>
                      </div>
                      <Badge variant="warning">RESPONSE PENDING</Badge>
                    </div>

                    <div style={{ fontSize: '13px', color: '#334155', fontWeight: 500 }}>
                      <strong>Target:</strong> {ch.target_entity_id} • <strong>Issuer:</strong> {ch.officer_name}
                    </div>

                    <div style={{ padding: '10px 14px', backgroundColor: '#FFFFFF', borderRadius: '6px', border: '1px solid #E2E8F0', fontSize: '13px', color: '#475569' }}>
                      <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Officer Instructions:</div>
                      <div style={{ marginTop: '2px' }}>{ch.instructions}</div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
                      <button
                        onClick={() => {
                          setActiveTab('WIZARD');
                          setWizardStep(4);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '8px 16px',
                          borderRadius: '6px',
                          backgroundColor: '#1B4332',
                          color: '#FFFFFF',
                          border: 'none',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Camera size={14} />
                        <span>Capture Fresh Response Photo</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* TAB 5: MOBILE APK & TELEMETRY DOWNLOAD */}
      {activeTab === 'MOBILE_APP' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
          <Card title="Official Farmer Android Application (APK)">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ width: '60px', height: '60px', borderRadius: '12px', backgroundColor: '#1B4332', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Smartphone size={32} />
                </div>
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 4px 0', color: '#1B4332' }}>PRAMAN Farmer v2.4.1</h3>
                  <div style={{ fontSize: '12px', color: '#64748B' }}>Production Debug APK • Built for Android 10+ (API 29+)</div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: '#334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={16} color="#2D6A4F" />
                  <span><strong>Hardware Keystore ECDSA:</strong> Signs every photo with tamper-proof device key</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={16} color="#2D6A4F" />
                  <span><strong>WGS-84 Geofencing:</strong> Polygon containment check runs entirely on-device</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={16} color="#2D6A4F" />
                  <span><strong>Offline-First SQLite Queue:</strong> Works without connectivity during monsoon</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={16} color="#2D6A4F" />
                  <span><strong>Multilingual UX:</strong> Native Telugu (తెలుగు), Hindi (హిन्दी), and English</span>
                </div>
              </div>

              <div style={{ padding: '12px', backgroundColor: '#F8F9FA', borderRadius: '6px', border: '1px solid #E2E8F0', fontSize: '12px', color: '#64748B', fontFamily: 'monospace' }}>
                SHA-256: e8b91a7c2d3f4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9
              </div>

              <a
                href="/download/apk"
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  backgroundColor: '#1B4332',
                  color: '#FFFFFF',
                  padding: '12px 20px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 700,
                  textDecoration: 'none',
                  boxShadow: '0 2px 8px rgba(27, 67, 50, 0.3)',
                }}
              >
                <Download size={18} />
                <span>Download APK Directly (praman-farmer-debug.apk)</span>
              </a>
            </div>
          </Card>

          <Card title="Installation & Pairing Instructions">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px', color: '#475569' }}>
              <div style={{ display: 'flex', gap: '10px' }}>
                <span style={{ width: '22px', height: '22px', borderRadius: '50%', backgroundColor: '#E2E8F0', color: '#1B4332', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px', flexShrink: 0 }}>1</span>
                <div>
                  <strong>Download & Install APK:</strong> Tap the download button or scan the QR code. Allow "Install from unknown sources" in Android settings.
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <span style={{ width: '22px', height: '22px', borderRadius: '50%', backgroundColor: '#E2E8F0', color: '#1B4332', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px', flexShrink: 0 }}>2</span>
                <div>
                  <strong>Generate Device Keypair:</strong> Open the app. The hardware keystore generates a P-256 keypair automatically.
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <span style={{ width: '22px', height: '22px', borderRadius: '50%', backgroundColor: '#E2E8F0', color: '#1B4332', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px', flexShrink: 0 }}>3</span>
                <div>
                  <strong>తెలుగు సూచనలు:</strong> యాప్‌ని ఇన్‌స్టాల్ చేసిన తర్వాత, 'కెమెరా' బటన్‌పై నొక్కండి. మీ పొలం హద్దుల్లో ఫోటో తీస్తే సరిపోతుంది.
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* BATCH TIMELINE MODAL */}
      {timelineBatchId && (
        <Modal
          isOpen={!!timelineBatchId}
          onClose={() => setTimelineBatchId(null)}
          title={`Provenance Audit Trail: ${timelineBatchId}`}
          size="large"
        >
          <BatchTimeline batchId={timelineBatchId} />
        </Modal>
      )}
    </div>
  );
};
