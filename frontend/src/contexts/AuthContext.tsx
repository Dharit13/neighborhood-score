import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface User {
  email: string;
  name?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  selectedCity: string | null;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  selectCity: (city: string) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY = 'ns_auth';

function getStoredSession(): { user: User | null; selectedCity: string | null } {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        user: parsed.user ?? null,
        selectedCity: parsed.selectedCity ?? null,
      };
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
  return { user: null, selectedCity: null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = getStoredSession();
  const [user, setUser] = useState<User | null>(stored.user);
  const [selectedCity, setSelectedCity] = useState<string | null>(stored.selectedCity);

  const persistSession = (u: User | null, city: string | null) => {
    if (u) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: u, selectedCity: city }));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const login = useCallback(async (email: string, _password: string) => {
    const u = { email, name: email.split('@')[0] };
    setUser(u);
    persistSession(u, selectedCity);
  }, [selectedCity]);

  const loginWithGoogle = useCallback(async () => {
    const u = { email: 'user@gmail.com', name: 'Google User' };
    setUser(u);
    persistSession(u, selectedCity);
  }, [selectedCity]);

  const logout = useCallback(() => {
    setUser(null);
    setSelectedCity(null);
    persistSession(null, null);
  }, []);

  const selectCity = useCallback((city: string) => {
    setSelectedCity(city);
    if (user) persistSession(user, city);
  }, [user]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!user,
        user,
        selectedCity,
        login,
        loginWithGoogle,
        logout,
        selectCity,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
