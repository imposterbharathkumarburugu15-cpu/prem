import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  ArrowRight,
  Truck,
  Building2,
  Store,
  Cpu,
  Smartphone,
  CheckCircle2,
  HelpCircle,
  Camera,
  MapPin,
  Lock,
} from 'lucide-react';
import { Badge } from '../components/common/Badge';

interface LandingPageProps {
  onStartDemo: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onStartDemo }) => {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#F8FAFC', color: '#101828', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <header
        style={{
          height: '70px',
          backgroundColor: '#FFFFFF',
          borderBottom: '1px solid #E4E7EC',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 40px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: '#087F5B',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              fontWeight: 800,
              fontSize: '18px',
              boxShadow: '0 2px 8px rgba(8, 127, 91, 0.4)',
            }}
          >
            P
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '18px', letterSpacing: '0.04em', color: '#142B45' }}>
              PRAMAN
            </div>
            <div style={{ fontSize: '11px', color: '#64748B' }}>
              Trusted Evidence Platform
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={onStartDemo}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#087F5B',
              color: '#FFFFFF',
              borderRadius: '6px',
              padding: '9px 18px',
              fontSize: '13px',
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(8, 127, 91, 0.3)',
            }}
          >
            <Sparkles size={16} fill="#FFFFFF" />
            <span>SEE HOW PRAMAN WORKS</span>
          </button>

          <button
            onClick={() => navigate('/officer')}
            style={{
              padding: '9px 18px',
              borderRadius: '6px',
              backgroundColor: '#142B45',
              color: '#FFFFFF',
              fontSize: '13px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Open Workspace
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section
        style={{
          padding: '64px 32px 48px 32px',
          maxWidth: '1100px',
          margin: '0 auto',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div style={{ marginBottom: '16px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '9999px',
              backgroundColor: '#EBFBEE',
              color: '#087F5B',
              border: '1px solid #B2F2BB',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            <ShieldCheck size={16} />
            Complex technology. Simple experience.
          </span>
        </div>

        <h1
          style={{
            fontSize: '48px',
            fontWeight: 800,
            color: '#101828',
            letterSpacing: '-0.03em',
            lineHeight: 1.15,
            maxWidth: '850px',
            marginBottom: '16px',
          }}
        >
          Trust the Evidence.
          <br />
          <span style={{ color: '#087F5B' }}>Verified in Seconds.</span>
        </h1>

        <p
          style={{
            fontSize: '17px',
            color: '#475467',
            maxWidth: '740px',
            lineHeight: 1.6,
            marginBottom: '32px',
          }}
        >
          PRAMAN performs sophisticated cybersecurity, AI forensics, cryptographic verification,
          and blockchain operations internally — giving every user simple explanations, meaningful results, and clear next actions.
        </p>

        {/* Hero Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            onClick={onStartDemo}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: '#087F5B',
              color: '#FFFFFF',
              padding: '14px 28px',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 700,
              boxShadow: '0 4px 14px rgba(8, 127, 91, 0.35)',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <Play size={18} fill="#FFFFFF" />
            <span>SEE HOW PRAMAN WORKS</span>
          </button>

          <button
            onClick={() => navigate('/officer')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: '#142B45',
              color: '#FFFFFF',
              padding: '14px 28px',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <span>Evidence Verification Centre</span>
            <ArrowRight size={18} />
          </button>

          <button
            onClick={() => navigate('/architecture')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#FFFFFF',
              color: '#344054',
              border: '1px solid #D0D5DD',
              padding: '14px 24px',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Cpu size={18} color="#087F5B" />
            <span>Explore PRAMAN Technology</span>
          </button>
        </div>
      </section>

      {/* 60-SECOND PRODUCT CLARITY SECTION (ANSWERS THE 5 CRITICAL QUESTIONS) */}
      <section style={{ backgroundColor: '#FFFFFF', borderTop: '1px solid #E4E7EC', borderBottom: '1px solid #E4E7EC', padding: '48px 32px' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#101828' }}>
              Understand PRAMAN in 60 Seconds
            </h2>
            <p style={{ fontSize: '14px', color: '#667085', marginTop: '4px' }}>
              Everything you need to know about the platform at a glance.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
            {/* Q1 */}
            <div style={{ padding: '20px 16px', borderRadius: '10px', backgroundColor: '#F8FAFC', border: '1px solid #E4E7EC' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#EBFBEE', color: '#087F5B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '14px', marginBottom: '10px' }}>
                1
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', marginBottom: '6px' }}>
                What is PRAMAN?
              </h3>
              <p style={{ fontSize: '12px', color: '#475467', lineHeight: '1.5' }}>
                An evidence verification platform that protects the integrity of agricultural supply chains from farm to shelf.
              </p>
            </div>

            {/* Q2 */}
            <div style={{ padding: '20px 16px', borderRadius: '10px', backgroundColor: '#F8FAFC', border: '1px solid #E4E7EC' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#EBFBEE', color: '#087F5B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '14px', marginBottom: '10px' }}>
                2
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', marginBottom: '6px' }}>
                What does it protect?
              </h3>
              <p style={{ fontSize: '12px', color: '#475467', lineHeight: '1.5' }}>
                Harvest records, transit integrity, organic purity, and consumer trust against duplicate or manipulated claims.
              </p>
            </div>

            {/* Q3 */}
            <div style={{ padding: '20px 16px', borderRadius: '10px', backgroundColor: '#F8FAFC', border: '1px solid #E4E7EC' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#EBFBEE', color: '#087F5B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '14px', marginBottom: '10px' }}>
                3
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', marginBottom: '6px' }}>
                How does it verify?
              </h3>
              <p style={{ fontSize: '12px', color: '#475467', lineHeight: '1.5' }}>
                Automatically cross-checks photos, GPS boundaries, satellite vegetation, and tamper-proof hardware seals.
              </p>
            </div>

            {/* Q4 */}
            <div style={{ padding: '20px 16px', borderRadius: '10px', backgroundColor: '#F8FAFC', border: '1px solid #E4E7EC' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#EBFBEE', color: '#087F5B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '14px', marginBottom: '10px' }}>
                4
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', marginBottom: '6px' }}>
                What if suspicious?
              </h3>
              <p style={{ fontSize: '12px', color: '#475467', lineHeight: '1.5' }}>
                Instantly halts auto-approval, flags the discrepancy, and sends the case to an officer for guided review.
              </p>
            </div>

            {/* Q5 */}
            <div style={{ padding: '20px 16px', borderRadius: '10px', backgroundColor: '#F8FAFC', border: '1px solid #E4E7EC' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#EBFBEE', color: '#087F5B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '14px', marginBottom: '10px' }}>
                5
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#101828', marginBottom: '6px' }}>
                What must I do?
              </h3>
              <p style={{ fontSize: '12px', color: '#475467', lineHeight: '1.5' }}>
                Follow your simple role workspace. Officers review cases, transporters log pickups, and retailers issue QRs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* WORKSPACES GRID */}
      <section style={{ padding: '48px 32px', maxWidth: '1100px', margin: '0 auto', width: '100%' }}>
        <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#101828', marginBottom: '18px' }}>
          Select an Operational Workspace
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          {[
            {
              title: 'Evidence Verification Centre',
              role: 'Investigation Officer',
              desc: 'Review submitted evidence, identify suspicious activity, and make trusted decisions.',
              path: '/officer',
              icon: ShieldCheck,
              accent: '#087F5B',
            },
            {
              title: 'My Shipments',
              role: 'Transporter',
              desc: 'Start pickups, update transit checkpoints, report issues, and confirm delivery.',
              path: '/transporter',
              icon: Truck,
              accent: '#142B45',
            },
            {
              title: 'Collection Centre',
              role: 'Hub Operator',
              desc: 'Receive incoming produce, record certified scale weights, inspect quality, and create batches.',
              path: '/centre',
              icon: Building2,
              accent: '#142B45',
            },
            {
              title: 'Retailer Workspace',
              role: 'Retailer',
              desc: 'Receive batches, inspect products, verify packaging seals, and issue consumer QR codes.',
              path: '/retailer',
              icon: Store,
              accent: '#142B45',
            },
            {
              title: 'Farmer Experience',
              role: 'Farmer Mobile App',
              desc: 'Simple mobile application for farmers. Background technology handles security automatically.',
              path: '/farmer',
              icon: Smartphone,
              accent: '#087F5B',
            },
            {
              title: 'Platform Management',
              role: 'Platform Admin',
              desc: 'Overview of registered organizations, active users, registered devices, and system health.',
              path: '/admin',
              icon: Cpu,
              accent: '#142B45',
            },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                onClick={() => navigate(item.path)}
                style={{
                  padding: '20px',
                  borderRadius: '10px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E4E7EC',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transition: 'all 0.15s ease',
                  boxShadow: '0 1px 3px rgba(16, 24, 40, 0.05)',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <Icon size={18} color={item.accent} />
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                      {item.role}
                    </span>
                  </div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#101828', marginBottom: '6px' }}>
                    {item.title}
                  </h3>
                  <p style={{ fontSize: '13px', color: '#64748B', lineHeight: '1.5' }}>
                    {item.desc}
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#087F5B', fontWeight: 600, fontSize: '13px', marginTop: '16px' }}>
                  <span>Open workspace</span>
                  <ArrowRight size={14} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ marginTop: 'auto', borderTop: '1px solid #E4E7EC', padding: '24px 40px', backgroundColor: '#FFFFFF', textAlign: 'center', fontSize: '13px', color: '#667085' }}>
        PRAMAN Evidence Platform • Complex technology. Simple experience.
      </footer>
    </div>
  );
};
