import React, { createContext, useContext, useState, useRef, useEffect, ReactNode } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  StatusBar,
  Platform,
} from 'react-native';

export type AlertType = 'error' | 'warning' | 'success' | 'info';

export interface InAppAlert {
  id: string;
  title: string;
  message: string;
  type: AlertType;
  timestamp: string;
}

interface NotificationContextType {
  showAlert: (title: string, message: string, type?: AlertType, durationMs?: number) => void;
  dismissAlert: () => void;
  activeAlert: InAppAlert | null;
  history: InAppAlert[];
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [activeAlert, setActiveAlert] = useState<InAppAlert | null>(null);
  const [history, setHistory] = useState<InAppAlert[]>([]);
  const slideAnim = useRef(new Animated.Value(-120)).current;
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const dismissAlert = () => {
    Animated.timing(slideAnim, {
      toValue: -120,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      setActiveAlert(null);
    });
  };

  const showAlert = (
    title: string,
    message: string,
    type: AlertType = 'info',
    durationMs: number = 4500
  ) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    const newAlert: InAppAlert = {
      id: 'alert_' + Date.now(),
      title,
      message,
      type,
      timestamp: new Date().toLocaleTimeString(),
    };

    setActiveAlert(newAlert);
    setHistory((prev) => [newAlert, ...prev.slice(0, 49)]);

    // Slide down animation
    Animated.spring(slideAnim, {
      toValue: Platform.OS === 'ios' ? 44 : 16,
      useNativeDriver: true,
      bounciness: 6,
    }).start();

    if (durationMs > 0) {
      timeoutRef.current = setTimeout(() => {
        dismissAlert();
      }, durationMs);
    }
  };

  const getStyleForType = (type: AlertType) => {
    switch (type) {
      case 'error':
        return {
          bg: '#FEF2F2',
          border: '#DC2626',
          titleColor: '#991B1B',
          textColor: '#B91C1C',
          badgeBg: '#DC2626',
          icon: '⚠️',
          badgeText: 'ALERT',
        };
      case 'warning':
        return {
          bg: '#FFFBEB',
          border: '#D97706',
          titleColor: '#92400E',
          textColor: '#B45309',
          badgeBg: '#D97706',
          icon: '⚡',
          badgeText: 'WARNING',
        };
      case 'success':
        return {
          bg: '#ECFDF5',
          border: '#059669',
          titleColor: '#065F46',
          textColor: '#047857',
          badgeBg: '#059669',
          icon: '✅',
          badgeText: 'SUCCESS',
        };
      case 'info':
      default:
        return {
          bg: '#EFF6FF',
          border: '#2563EB',
          titleColor: '#1E40AF',
          textColor: '#1D4ED8',
          badgeBg: '#2563EB',
          icon: '🔔',
          badgeText: 'NOTICE',
        };
    }
  };

  return (
    <NotificationContext.Provider value={{ showAlert, dismissAlert, activeAlert, history }}>
      {children}
      {activeAlert && (
        <Animated.View
          style={[
            styles.alertContainer,
            {
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          {(() => {
            const theme = getStyleForType(activeAlert.type);
            return (
              <View
                style={[
                  styles.alertCard,
                  {
                    backgroundColor: theme.bg,
                    borderLeftColor: theme.border,
                    borderColor: '#E2E8F0',
                  },
                ]}
              >
                <View style={styles.alertHeader}>
                  <View style={styles.badgeRow}>
                    <Text style={styles.alertIcon}>{theme.icon}</Text>
                    <View style={[styles.typeBadge, { backgroundColor: theme.badgeBg }]}>
                      <Text style={styles.typeBadgeText}>{theme.badgeText}</Text>
                    </View>
                    <Text style={[styles.alertTitle, { color: theme.titleColor }]} numberOfLines={1}>
                      {activeAlert.title}
                    </Text>
                  </View>
                  <TouchableOpacity onPress={dismissAlert} style={styles.closeBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                    <Text style={styles.closeBtnText}>✕</Text>
                  </TouchableOpacity>
                </View>

                <Text style={[styles.alertMessage, { color: theme.textColor }]}>
                  {activeAlert.message}
                </Text>

                <View style={styles.alertFooter}>
                  <Text style={styles.timestampText}>PRAMAN Mobile System • {activeAlert.timestamp}</Text>
                  <Text style={styles.dismissHint}>Tap ✕ to dismiss</Text>
                </View>
              </View>
            );
          })()}
        </Animated.View>
      )}
    </NotificationContext.Provider>
  );
};

export const useAppNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useAppNotification must be used within a NotificationProvider');
  }
  return context;
};

const styles = StyleSheet.create({
  alertContainer: {
    position: 'absolute',
    top: 0,
    left: 12,
    right: 12,
    zIndex: 99999,
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 8,
  },
  alertCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderLeftWidth: 5,
    padding: 12,
    backgroundColor: '#FFFFFF',
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 8,
  },
  alertIcon: {
    fontSize: 15,
    marginRight: 6,
  },
  typeBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginRight: 8,
  },
  typeBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  alertTitle: {
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
  },
  closeBtn: {
    padding: 4,
  },
  closeBtnText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#64748B',
  },
  alertMessage: {
    fontSize: 12,
    lineHeight: 17,
    marginTop: 2,
    fontWeight: '500',
  },
  alertFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 6,
    paddingTop: 4,
    borderTopWidth: 0.5,
    borderTopColor: 'rgba(0,0,0,0.06)',
  },
  timestampText: {
    fontSize: 10,
    color: '#64748B',
    fontWeight: '500',
  },
  dismissHint: {
    fontSize: 10,
    color: '#94A3B8',
  },
});

