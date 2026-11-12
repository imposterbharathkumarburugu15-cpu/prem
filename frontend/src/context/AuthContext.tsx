import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, UserSession } from '../services/api';

export type RoleType =
  | 'FARMER'
  | 'TRANSPORTER'
  | 'COLLECTION_CENTRE'
  | 'RETAILER'
  | 'EVIDENCE_INTEGRITY_OFFICER'
  | 'PLATFORM_ADMINISTRATOR';

interface AuthContextType {
  user: UserSession | null;
  role: RoleType;
  isAuthenticated: boolean;
  login: (username: string, pass: string) => Promise<void>;
  switchRoleQuick: (role: RoleType) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  error: string | null;
}

const DEFAULT_USERS: Record<RoleType, { username: string; pass: string; fallback: UserSession }> = {
  FARMER: {
    username: 'farmer1',
    pass: 'Praman@2026',
    fallback: {
      id: 'farmer-uuid-001',
      username: 'farmer1',
      email: 'farmer@praman.org',
      full_name: 'Lakshman Reddy (Farmer APK)',
      role: 'FARMER',
      organization_name: 'Khammam Organic Farmer Cluster',
    },
  },
  TRANSPORTER: {
    username: 'transporter1',
    pass: 'Praman@2026',
    fallback: {
      id: 'transporter-uuid-001',
      username: 'transporter1',
      email: 'transporter@praman.org',
      full_name: 'Rajesh Logistics Corp',
      role: 'TRANSPORTER',
      organization_name: 'Deccan Agro Transit Fleet',
    },
  },
  COLLECTION_CENTRE: {
    username: 'centre1',
    pass: 'Praman@2026',
    fallback: {
      id: 'centre-uuid-001',
      username: 'centre1',
      email: 'centre@praman.org',
      full_name: 'Warangal Agri Processing Hub',
      role: 'COLLECTION_CENTRE',
      organization_name: 'Telangana State Seed Processing',
    },
  },
  RETAILER: {
    username: 'retailer1',
    pass: 'Praman@2026',
    fallback: {
      id: 'retailer-uuid-001',
      username: 'retailer1',
      email: 'retailer@praman.org',
      full_name: 'PureAgro Retail Chain',
      role: 'RETAILER',
      organization_name: 'Organic Bharat Mart',
    },
  },
  EVIDENCE_INTEGRITY_OFFICER: {
    username: 'officer1',
    pass: 'Praman@2026',
    fallback: {
      id: 'officer-uuid-001',
      username: 'officer1',
      email: 'officer@praman.org',
      full_name: 'Dr. Rao Integrity Officer',
      role: 'EVIDENCE_INTEGRITY_OFFICER',
      organization_name: 'PRAMAN Forensic Integrity Bureau',
    },
  },
  PLATFORM_ADMINISTRATOR: {
    username: 'admin1',
    pass: 'Praman@2026',
    fallback: {
      id: 'admin-uuid-001',
      username: 'admin1',
      email: 'admin@praman.org',
      full_name: 'System Root Administrator',
      role: 'PLATFORM_ADMINISTRATOR',
      organization_name: 'PRAMAN Foundation Trust Core',
    },
  },
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(() => {
    const cached = localStorage.getItem('praman_user');
    if (cached) {
      try { return JSON.parse(cached); } catch { return null; }
    }
    return DEFAULT_USERS.EVIDENCE_INTEGRITY_OFFICER.fallback; // Default to flagship experience
  });

  const [role, setRole] = useState<RoleType>(() => {
    return user?.role || 'EVIDENCE_INTEGRITY_OFFICER';
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      localStorage.setItem('praman_user', JSON.stringify(user));
      setRole(user.role);
    }
  }, [user]);

  // Ensure an authenticated token is active so real backend data flows immediately
  useEffect(() => {
    const existingToken = api.getToken();
    if (!existingToken) {
      api.login('officer1', 'Praman@2026').then((resp) => {
        setUser(resp.user);
        setRole(resp.user.role);
      }).catch((e) => {
        console.warn('Initial auto-auth failed, using fallback:', e.message);
      });
    }
  }, []);

  const login = async (username: string, pass: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.login(username, pass);
      setUser(resp.user);
      setRole(resp.user.role);
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const switchRoleQuick = async (targetRole: RoleType) => {
    setIsLoading(true);
    setError(null);
    const targetConfig = DEFAULT_USERS[targetRole];
    try {
      if (targetRole === 'FARMER') {
        // Farmer is an Android APK role - set session directly
        setUser(targetConfig.fallback);
        setRole('FARMER');
      } else {
        const resp = await api.login(targetConfig.username, targetConfig.pass);
        setUser(resp.user);
        setRole(resp.user.role);
      }
    } catch {
      // If offline or network issue, fallback gracefully to mocked session
      setUser(targetConfig.fallback);
      setRole(targetRole);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.setToken(null);
    localStorage.removeItem('praman_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAuthenticated: !!user,
        login,
        switchRoleQuick,
        logout,
        isLoading,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
