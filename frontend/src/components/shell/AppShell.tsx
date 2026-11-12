import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ShieldCheck,
  Truck,
  Building2,
  Store,
  Cpu,
  ChevronLeft,
  ChevronRight,
  Play,
  Download,
  Smartphone,
  ExternalLink,
  CheckCircle2,
  Bell,
  Sparkles,
  Globe,
  User,
  LogOut,
  Menu,
  X,
  Layers,
  ChevronDown,
  Info,
  Clock,
  Shield,
} from 'lucide-react';
import { useAuth, RoleType } from '../../context/AuthContext';
import { Badge } from '../common/Badge';

interface AppShellProps {
  children: React.ReactNode;
  onOpenLiveDemo?: () => void;
}

type SupportedLanguage = 'en' | 'te' | 'hi';

const translations: Record<SupportedLanguage, { name: string; native: string; subtitle: string }> = {
  en: { name: 'English', native: 'English', subtitle: 'Trusted Evidence Platform' },
  te: { name: 'Telugu', native: 'తెలుగు', subtitle: 'విశ్వసనీయ ధృవీకరణ వేదిక' },
  hi: { name: 'Hindi', native: 'हिन्दी', subtitle: 'विश्वसनीय साक्ष्य मंच' },
};

export const AppShell: React.FC<AppShellProps> = ({ children, onOpenLiveDemo }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [language, setLanguage] = useState<SupportedLanguage>('en');

  const { user, role, switchRoleQuick, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Role-specific navigation structures for all 6 roles
  const roleNavItems: Record<RoleType, Array<{ path: string; label: string; icon: any }>> = {
    FARMER: [
      { path: '/farmer', label: 'Farmer Dashboard & APK', icon: Smartphone },
      { path: '/architecture', label: 'Explore PRAMAN Technology', icon: Cpu },
    ],
    TRANSPORTER: [
      { path: '/transporter', label: 'Transporter Logistics Command', icon: Truck },
      { path: '/architecture', label: 'Explore PRAMAN Technology', icon: Cpu },
    ],
    COLLECTION_CENTRE: [
      { path: '/centre', label: 'Collection Hub & Processing', icon: Building2 },
      { path: '/architecture', label: 'Explore PRAMAN Technology', icon: Cpu },
    ],
    RETAILER: [
      { path: '/retailer', label: 'Retailer & QR Workspace', icon: Store },
      { path: '/verify/prm_3152005f74824af1b6b4715603f8b302', label: 'Customer QR Verification', icon: ExternalLink },
      { path: '/architecture', label: 'Explore PRAMAN Technology', icon: Cpu },
    ],
    EVIDENCE_INTEGRITY_OFFICER: [
      { path: '/officer', label: 'Evidence Command Center', icon: ShieldCheck },
      { path: '/architecture', label: 'Explore PRAMAN Technology', icon: Cpu },
    ],
    PLATFORM_ADMINISTRATOR: [
      { path: '/admin', label: 'Platform Management', icon: Cpu },
      { path: '/architecture', label: 'Explore PRAMAN Technology', icon: Cpu },
    ],
  };

  const rolesList: Array<{ id: RoleType; name: string; shortName: string; icon: any; desc: string }> = [
    { id: 'FARMER', name: 'Farmer', shortName: 'Farmer App', icon: Smartphone, desc: 'Mobile app & harvest telemetry' },
    { id: 'TRANSPORTER', name: 'Transporter', shortName: 'Transporter', icon: Truck, desc: 'Pickups, checkpoints & delivery' },
    { id: 'COLLECTION_CENTRE', name: 'Collection Centre', shortName: 'Collection Centre', icon: Building2, desc: 'Weighing, grading & batch split' },
    { id: 'RETAILER', name: 'Retailer', shortName: 'Retailer', icon: Store, desc: 'Receipt, packaging & QR minting' },
    { id: 'EVIDENCE_INTEGRITY_OFFICER', name: 'Evidence Officer', shortName: 'Officer', icon: ShieldCheck, desc: 'Forensics, trust graph & challenges' },
    { id: 'PLATFORM_ADMINISTRATOR', name: 'Platform Admin', shortName: 'Admin', icon: Cpu, desc: 'Users, devices & audit log' },
  ];

  const currentNav = roleNavItems[role] || roleNavItems.EVIDENCE_INTEGRITY_OFFICER;

  // Breadcrumb generator
  const getBreadcrumbs = () => {
    const segments = location.pathname.split('/').filter(Boolean);
    if (segments.length === 0) return ['Home'];
    return [
      'PRAMAN',
      rolesList.find((r) => r.id === role)?.shortName || 'Workspace',
      segments[0].toUpperCase(),
    ];
  };

  const notifications = [
    {
      id: 1,
      type: 'VERIFIED',
      title: 'Batch BATCH-2026-001 Verified',
      time: '10m ago',
      desc: 'All 14 cryptographic checks confirmed by Evidence Engine.',
    },
    {
      id: 2,
      type: 'ALERT',
      title: 'Transit Checkpoint Recorded',
      time: '45m ago',
      desc: 'TS-08-UB-4912 logged checkpoint at Highway Toll Plaza #3.',
    },
    {
      id: 3,
      type: 'POLICY',
      title: 'Immutable Epoch Sealed',
      time: '2h ago',
      desc: 'Merkle root anchored with 5 supply chain events.',
    },
  ];

  const handleRoleSelect = async (newRole: RoleType) => {
    await switchRoleQuick(newRole);
    if (newRole === 'FARMER') navigate('/farmer');
    else if (newRole === 'TRANSPORTER') navigate('/transporter');
    else if (newRole === 'COLLECTION_CENTRE') navigate('/centre');
    else if (newRole === 'RETAILER') navigate('/retailer');
    else if (newRole === 'EVIDENCE_INTEGRITY_OFFICER') navigate('/officer');
    else if (newRole === 'PLATFORM_ADMINISTRATOR') navigate('/admin');
    setMobileDrawerOpen(false);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: '#FBFBF9' }}>
      {/* MOBILE BACKDROP DRAWER */}
      {mobileDrawerOpen && (
        <div
          onClick={() => setMobileDrawerOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(8, 28, 21, 0.6)',
            zIndex: 90,
          }}
        />
      )}

      {/* LEFT SIDEBAR (FOREST GREEN VISUAL IDENTITY) */}
      <aside
        style={{
          width: collapsed ? '72px' : '260px',
          backgroundColor: '#1B4332',
          color: '#FFFFFF',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          borderRight: '1px solid #2D6A4F',
          zIndex: 95,
          flexShrink: 0,
          position: mobileDrawerOpen ? 'fixed' : 'relative',
          top: 0,
          bottom: 0,
          left: 0,
        }}
      >
        {/* Brand Header */}
        <div
          style={{
            height: '64px',
            padding: collapsed ? '0 16px' : '0 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <div
            onClick={() => navigate('/')}
            style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}
          >
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                backgroundColor: '#40916C',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                fontWeight: 800,
                fontSize: '16px',
                letterSpacing: '0.05em',
                color: '#FFFFFF',
              }}
            >
              P
            </div>
            {!collapsed && (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 800, fontSize: '15px', letterSpacing: '0.04em', color: '#FFFFFF' }}>
                  PRAMAN
                </span>
                <span style={{ fontSize: '11px', color: '#D8F3DC' }}>
                  {translations[language].subtitle}
                </span>
              </div>
            )}
          </div>

          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              style={{ color: '#D8F3DC', padding: '4px', display: 'flex', alignItems: 'center', cursor: 'pointer' }}
              title="Collapse Sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        {collapsed && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0' }}>
            <button
              onClick={() => setCollapsed(false)}
              style={{ color: '#D8F3DC', padding: '4px', display: 'flex', alignItems: 'center', cursor: 'pointer' }}
              title="Expand Sidebar"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* Guided Walkthrough CTA */}
        <div style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <button
            onClick={onOpenLiveDemo}
            style={{
              width: '100%',
              backgroundColor: '#40916C',
              color: '#FFFFFF',
              borderRadius: '8px',
              padding: collapsed ? '10px 0' : '10px 14px',
              fontSize: '12px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              gap: '8px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
              transition: 'background-color 0.15s ease',
            }}
            title="SEE HOW PRAMAN WORKS (Guided Walkthrough)"
          >
            <Sparkles size={15} fill="#FFFFFF" />
            {!collapsed && <span>SEE HOW PRAMAN WORKS</span>}
          </button>
        </div>

        {/* Navigation Links */}
        <div style={{ flex: 1, padding: '16px 12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {!collapsed && (
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#A7D7C5', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '4px 8px' }}>
              Role Workspaces
            </span>
          )}

          {currentNav.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setMobileDrawerOpen(false);
                }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: collapsed ? '10px 0' : '10px 12px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  borderRadius: '6px',
                  backgroundColor: active ? '#2D6A4F' : 'transparent',
                  color: active ? '#FFFFFF' : '#E8F5E9',
                  fontWeight: active ? 700 : 500,
                  fontSize: '13px',
                  cursor: 'pointer',
                  transition: 'background-color 0.12s ease',
                }}
                title={item.label}
              >
                <Icon size={17} color={active ? '#FFFFFF' : '#C7E8D8'} />
                {!collapsed && <span className="text-truncate">{item.label}</span>}
              </button>
            );
          })}

          <div style={{ height: '1px', backgroundColor: 'rgba(255, 255, 255, 0.1)', margin: '12px 0' }} />

          {!collapsed && (
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#A7D7C5', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '4px 8px' }}>
              Public & Architecture
            </span>
          )}

          <button
            onClick={() => {
              navigate('/architecture');
              setMobileDrawerOpen(false);
            }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: collapsed ? '10px 0' : '9px 12px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              borderRadius: '6px',
              backgroundColor: location.pathname === '/architecture' ? '#2D6A4F' : 'transparent',
              color: location.pathname === '/architecture' ? '#FFFFFF' : '#E8F5E9',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            <Cpu size={17} color={location.pathname === '/architecture' ? '#FFFFFF' : '#C7E8D8'} />
            {!collapsed && <span>PRAMAN Architecture</span>}
          </button>

          <button
            onClick={() => {
              navigate('/verify/prm_3152005f74824af1b6b4715603f8b302');
              setMobileDrawerOpen(false);
            }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: collapsed ? '10px 0' : '9px 12px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              borderRadius: '6px',
              backgroundColor: location.pathname.startsWith('/verify') ? '#2D6A4F' : 'transparent',
              color: location.pathname.startsWith('/verify') ? '#FFFFFF' : '#E8F5E9',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            <CheckCircle2 size={17} color={location.pathname.startsWith('/verify') ? '#FFFFFF' : '#C7E8D8'} />
            {!collapsed && <span>Public QR Verification</span>}
          </button>
        </div>

        {/* Farmer Mobile App Download Card */}
        <div style={{ padding: '12px 14px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <a
            href="http://127.0.0.1:8000/download/apk"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: collapsed ? '8px 0' : '8px 10px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              borderRadius: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              color: '#FFFFFF',
              fontSize: '12px',
              textDecoration: 'none',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              fontWeight: 500,
            }}
            title="Download Farmer Android APK"
          >
            <Download size={14} color="#74C69D" />
            {!collapsed && <span>Farmer Android APK</span>}
          </a>
        </div>

        {/* User Profile Footer */}
        <div
          style={{
            padding: '14px 16px',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              backgroundColor: '#2D6A4F',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              fontWeight: 700,
              fontSize: '13px',
              flexShrink: 0,
            }}
          >
            {user?.full_name ? user.full_name[0] : 'U'}
          </div>
          {!collapsed && (
            <div style={{ overflow: 'hidden', flex: 1 }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }} className="text-truncate">
                {user?.full_name || 'Active Participant'}
              </div>
              <div style={{ fontSize: '11px', color: '#D8F3DC' }} className="text-truncate">
                {user?.organization_name || 'PRAMAN Network'}
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* MAIN CONTAINER */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* TOP BAR */}
        <header
          style={{
            height: '64px',
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E5E7EB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            flexShrink: 0,
            zIndex: 30,
            gap: '12px',
          }}
        >
          {/* Left: Mobile hamburger + Breadcrumbs + Environment Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => setMobileDrawerOpen(!mobileDrawerOpen)}
              style={{
                display: 'inline-flex',
                padding: '6px',
                borderRadius: '6px',
                color: '#374151',
                cursor: 'pointer',
              }}
              title="Toggle Menu"
            >
              <Menu size={20} />
            </button>

            {/* Breadcrumbs */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
              {getBreadcrumbs().map((b, i, arr) => (
                <React.Fragment key={b}>
                  <span
                    style={{
                      fontWeight: i === arr.length - 1 ? 700 : 500,
                      color: i === arr.length - 1 ? '#111827' : '#64748B',
                    }}
                  >
                    {b}
                  </span>
                  {i < arr.length - 1 && <span style={{ color: '#D1D5DB' }}>/</span>}
                </React.Fragment>
              ))}
            </div>

            {/* Environment Pill */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                backgroundColor: '#EBF8EE',
                border: '1px solid #D8F3DC',
                padding: '3px 8px',
                borderRadius: '12px',
                fontSize: '11px',
                fontWeight: 600,
                color: '#1B4332',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: '#40916C',
                  display: 'inline-block',
                }}
              />
              <span>Production v2.4 (Tamper-Sealed)</span>
            </div>
          </div>

          {/* Center: Role Switcher Quick Pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto' }}>
            {rolesList.map((r) => {
              const RoleIcon = r.icon;
              const isSelected = role === r.id;
              return (
                <button
                  key={r.id}
                  onClick={() => handleRoleSelect(r.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '5px 10px',
                    borderRadius: '16px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    border: isSelected ? '1px solid #1B4332' : '1px solid #E5E7EB',
                    backgroundColor: isSelected ? '#1B4332' : '#FFFFFF',
                    color: isSelected ? '#FFFFFF' : '#4B5563',
                    boxShadow: isSelected ? '0 1px 2px rgba(27, 67, 50, 0.2)' : 'none',
                    whiteSpace: 'nowrap',
                  }}
                  title={r.desc}
                >
                  <RoleIcon size={12} color={isSelected ? '#FFFFFF' : '#6B7280'} />
                  <span>{r.shortName}</span>
                </button>
              );
            })}
          </div>

          {/* Right: Language toggle + Notifications + Profile dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Multilingual Toggle */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowLangMenu(!showLangMenu)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  border: '1px solid #E5E7EB',
                  backgroundColor: '#FFFFFF',
                  color: '#374151',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
                title="Select Language"
              >
                <Globe size={14} color="#1B4332" />
                <span>{translations[language].native}</span>
                <ChevronDown size={12} color="#9CA3AF" />
              </button>

              {showLangMenu && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '6px',
                    width: '140px',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                    zIndex: 100,
                    padding: '4px',
                  }}
                >
                  {(Object.keys(translations) as SupportedLanguage[]).map((langKey) => (
                    <button
                      key={langKey}
                      onClick={() => {
                        setLanguage(langKey);
                        setShowLangMenu(false);
                      }}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '6px 10px',
                        fontSize: '12px',
                        fontWeight: language === langKey ? 700 : 500,
                        color: language === langKey ? '#1B4332' : '#374151',
                        backgroundColor: language === langKey ? '#EBF8EE' : 'transparent',
                        borderRadius: '4px',
                        cursor: 'pointer',
                      }}
                    >
                      {translations[langKey].native} ({translations[langKey].name})
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Notification Drawer Button */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                style={{
                  padding: '7px',
                  borderRadius: '6px',
                  border: '1px solid #E5E7EB',
                  backgroundColor: '#FFFFFF',
                  color: '#4B5563',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  position: 'relative',
                }}
                title="Notifications"
              >
                <Bell size={16} />
                <span
                  style={{
                    position: 'absolute',
                    top: '3px',
                    right: '3px',
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    backgroundColor: '#1B4332',
                  }}
                />
              </button>

              {showNotifications && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '6px',
                    width: '320px',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                    zIndex: 100,
                    padding: '12px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '8px',
                    }}
                  >
                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#111827' }}>
                      Supply Chain Events Feed
                    </span>
                    <button
                      onClick={() => setShowNotifications(false)}
                      style={{ color: '#9CA3AF', cursor: 'pointer' }}
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        style={{
                          padding: '8px 10px',
                          backgroundColor: '#F8F9FA',
                          borderRadius: '6px',
                          border: '1px solid #E5E7EB',
                          fontSize: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                          <strong style={{ color: '#1B4332' }}>{n.title}</strong>
                          <span style={{ fontSize: '10px', color: '#9CA3AF' }}>{n.time}</span>
                        </div>
                        <p style={{ margin: 0, color: '#64748B', fontSize: '11px' }}>{n.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* User Profile Dropdown */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  border: '1px solid #E5E7EB',
                  backgroundColor: '#FFFFFF',
                  cursor: 'pointer',
                }}
              >
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: '#1B4332',
                    color: '#FFFFFF',
                    fontSize: '11px',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {user?.full_name ? user.full_name[0] : 'U'}
                </div>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#374151' }}>
                  {user?.full_name ? user.full_name.split(' ')[0] : 'Account'}
                </span>
                <ChevronDown size={12} color="#9CA3AF" />
              </button>

              {showProfileMenu && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '6px',
                    width: '240px',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                    zIndex: 100,
                    padding: '12px',
                  }}
                >
                  <div style={{ borderBottom: '1px solid #F3F4F6', paddingBottom: '8px', marginBottom: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#111827' }}>
                      {user?.full_name || 'Active User'}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B' }}>
                      {user?.email || 'user@praman.org'}
                    </div>
                    <div style={{ marginTop: '4px' }}>
                      <Badge variant="emerald">{role}</Badge>
                    </div>
                  </div>

                  <div style={{ fontSize: '11px', color: '#64748B', marginBottom: '8px' }}>
                    <strong>Organization:</strong> {user?.organization_name || 'PRAMAN Trust Network'}
                  </div>

                  <button
                    onClick={() => {
                      logout();
                      setShowProfileMenu(false);
                      navigate('/');
                    }}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 8px',
                      borderRadius: '4px',
                      backgroundColor: '#FEF2F2',
                      color: '#DC2626',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <LogOut size={13} />
                    <span>Log Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* WORKSPACE CANVAS */}
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
            backgroundColor: '#FBFBF9',
            padding: '24px 32px',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
};
