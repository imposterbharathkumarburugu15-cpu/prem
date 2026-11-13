import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AppShell } from './components/shell/AppShell';
import { LandingPage } from './pages/LandingPage';
import { EvidenceOfficerWorkspace } from './pages/EvidenceOfficerWorkspace';
import { TransporterWorkspace } from './pages/TransporterWorkspace';
import { CollectionCentreWorkspace } from './pages/CollectionCentreWorkspace';
import { RetailerWorkspace } from './pages/RetailerWorkspace';
import { AdminWorkspace } from './pages/AdminWorkspace';
import { FarmerInfoPage } from './pages/FarmerInfoPage';
import { ArchitectureExplorer } from './pages/ArchitectureExplorer';
import { PublicVerifyPage } from './pages/PublicVerifyPage';
import { CyberTrapWorkspace } from './pages/CyberTrapWorkspace';
import { LiveDemoModal } from './pages/LiveDemoModal';

export const App: React.FC = () => {
  const [demoOpen, setDemoOpen] = useState(false);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Landing Page (The Judge Experience) */}
          <Route path="/" element={<LandingPage onStartDemo={() => setDemoOpen(true)} />} />

          {/* Operational Shell Workspaces */}
          <Route
            path="/officer"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <EvidenceOfficerWorkspace />
              </AppShell>
            }
          />
          <Route
            path="/transporter"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <TransporterWorkspace />
              </AppShell>
            }
          />
          <Route
            path="/centre"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <CollectionCentreWorkspace />
              </AppShell>
            }
          />
          <Route
            path="/retailer"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <RetailerWorkspace />
              </AppShell>
            }
          />
          <Route
            path="/admin"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <AdminWorkspace />
              </AppShell>
            }
          />
          <Route
            path="/farmer"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <FarmerInfoPage />
              </AppShell>
            }
          />
          <Route
            path="/architecture"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <ArchitectureExplorer />
              </AppShell>
            }
          />
          <Route
            path="/cybertrap"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <CyberTrapWorkspace />
              </AppShell>
            }
          />

          {/* Consumer QR Verification Views */}
          <Route
            path="/verify/:token"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <PublicVerifyPage />
              </AppShell>
            }
          />
          <Route
            path="/verify"
            element={
              <AppShell onOpenLiveDemo={() => setDemoOpen(true)}>
                <PublicVerifyPage />
              </AppShell>
            }
          />

          {/* Fallback to Home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {/* Global 11-Step Automated Live Demonstration */}
        <LiveDemoModal isOpen={demoOpen} onClose={() => setDemoOpen(false)} />
      </BrowserRouter>
    </AuthProvider>
  );
};
