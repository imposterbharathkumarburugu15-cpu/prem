import React, { useState } from 'react';
import { SafeAreaView, StyleSheet, StatusBar, View, Text, TouchableOpacity, Modal, ScrollView } from 'react-native';
import { SupportedLanguage } from './src/i18n/catalogs';
import { LanguageSelectScreen } from './src/screens/LanguageSelectScreen';
import { AuthScreen } from './src/screens/AuthScreen';
import { FarmBoundaryScreen } from './src/screens/FarmBoundaryScreen';
import { EvidenceCaptureScreen } from './src/screens/EvidenceCaptureScreen';
import { NotificationProvider, useAppNotification } from './src/context/NotificationContext';

type AppStep = 'LANGUAGE' | 'AUTH' | 'FARM_SETUP' | 'CAPTURE';

function MainAppNavigator() {
  const [step, setStep] = useState<AppStep>('LANGUAGE');
  const [language, setLanguage] = useState<SupportedLanguage>('en');
  const [farmer, setFarmer] = useState<{ id: string; fullName: string; phone: string } | null>(null);
  const [farm, setFarm] = useState<{ id: string; name: string } | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);

  const { history, showAlert } = useAppNotification();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#F8F9FA" />

      {/* TOP NOTIFICATION BAR HEADER (Always visible across all screens) */}
      <View style={styles.headerBar}>
        <View style={styles.brandContainer}>
          <Text style={styles.brandTitle}>PRAMAN</Text>
          <Text style={styles.brandSub}>Farmer APK • Offline-First</Text>
        </View>

        <TouchableOpacity
          onPress={() => setShowHistoryModal(true)}
          style={styles.bellButton}
          activeOpacity={0.7}
        >
          <Text style={styles.bellIcon}>🔔</Text>
          {history.length > 0 && (
            <View style={styles.bellBadge}>
              <Text style={styles.bellBadgeText}>{history.length > 9 ? '9+' : history.length}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* SCREENS */}
      <View style={styles.content}>
        {step === 'LANGUAGE' && (
          <LanguageSelectScreen
            onLanguageSelected={(selectedLang) => {
              setLanguage(selectedLang);
              setStep('AUTH');
              showAlert('Language Selected', `Interface configured for ${selectedLang.toUpperCase()}`, 'info');
            }}
          />
        )}

        {step === 'AUTH' && (
          <AuthScreen
            language={language}
            onAuthSuccess={(authenticatedFarmer) => {
              setFarmer(authenticatedFarmer);
              setStep('FARM_SETUP');
              showAlert('Welcome Farmer', `Signed in as ${authenticatedFarmer.fullName}`, 'success');
            }}
          />
        )}

        {step === 'FARM_SETUP' && farmer && (
          <FarmBoundaryScreen
            language={language}
            farmerId={farmer.id}
            onFarmCreated={(createdFarm) => {
              setFarm(createdFarm);
              setStep('CAPTURE');
              showAlert('Parcel Boundary Saved', `Geo-fencing established for ${createdFarm.name}`, 'success');
            }}
          />
        )}

        {step === 'CAPTURE' && farmer && farm && (
          <EvidenceCaptureScreen
            farmId={farm.id}
            farmerId={farmer.id}
            onEvidenceCaptured={(evidenceId) => {
              showAlert(
                'Evidence Queued for Ledger Anchor',
                `Evidence ${evidenceId} signed with device hardware key and stored in tamper-proof queue.`,
                'success',
                6000
              );
            }}
          />
        )}
      </View>

      {/* NOTIFICATION INBOX MODAL */}
      <Modal visible={showHistoryModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View style={styles.modalHeaderTitleRow}>
                <Text style={styles.modalBell}>🔔</Text>
                <Text style={styles.modalTitle}>App Notifications & Alerts</Text>
              </View>
              <TouchableOpacity onPress={() => setShowHistoryModal(false)} style={styles.modalCloseBtn}>
                <Text style={styles.modalCloseText}>✕</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalScroll}>
              {history.length === 0 ? (
                <View style={styles.emptyInbox}>
                  <Text style={styles.emptyIcon}>📭</Text>
                  <Text style={styles.emptyText}>No notifications yet</Text>
                  <Text style={styles.emptySub}>All alerts, upload syncs, and verification notices will appear here.</Text>
                </View>
              ) : (
                history.map((item) => (
                  <View key={item.id} style={[styles.historyCard, item.type === 'error' && styles.historyCardError, item.type === 'warning' && styles.historyCardWarning]}>
                    <View style={styles.historyRow}>
                      <Text style={styles.historyIcon}>
                        {item.type === 'error' ? '❌' : item.type === 'warning' ? '⚠️' : item.type === 'success' ? '✅' : 'ℹ️'}
                      </Text>
                      <Text style={styles.historyTitle}>{item.title}</Text>
                      <Text style={styles.historyTime}>{item.timestamp}</Text>
                    </View>
                    <Text style={styles.historyMsg}>{item.message}</Text>
                  </View>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <NotificationProvider>
      <MainAppNavigator />
    </NotificationProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
  },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  brandContainer: {
    flexDirection: 'column',
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#1B4332',
    letterSpacing: 0.5,
  },
  brandSub: {
    fontSize: 10,
    color: '#64748B',
    fontWeight: '500',
  },
  bellButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  bellIcon: {
    fontSize: 18,
  },
  bellBadge: {
    position: 'absolute',
    top: -2,
    right: -2,
    backgroundColor: '#DC2626',
    borderRadius: 9,
    minWidth: 18,
    height: 18,
    paddingHorizontal: 4,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: '#FFFFFF',
  },
  bellBadgeText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: '800',
  },
  content: {
    flex: 1,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '75%',
    padding: 16,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  modalHeaderTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  modalBell: {
    fontSize: 18,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1B4332',
  },
  modalCloseBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCloseText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#64748B',
  },
  modalScroll: {
    paddingVertical: 12,
  },
  emptyInbox: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyIcon: {
    fontSize: 36,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#334155',
  },
  emptySub: {
    fontSize: 12,
    color: '#94A3B8',
    textAlign: 'center',
    marginTop: 4,
    paddingHorizontal: 24,
  },
  historyCard: {
    backgroundColor: '#F8F9FA',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#059669',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  historyCardError: {
    borderLeftColor: '#DC2626',
    backgroundColor: '#FEF2F2',
  },
  historyCardWarning: {
    borderLeftColor: '#D97706',
    backgroundColor: '#FFFBEB',
  },
  historyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  historyIcon: {
    fontSize: 13,
    marginRight: 6,
  },
  historyTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1E293B',
    flex: 1,
  },
  historyTime: {
    fontSize: 10,
    color: '#94A3B8',
  },
  historyMsg: {
    fontSize: 12,
    color: '#475569',
    lineHeight: 16,
  },
});
