import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  session: Session | null;
  selectedCity: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ error?: string }>;
  signup: (email: string, password: string) => Promise<{ error?: string }>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  selectCity: (city: string) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const CITY_KEY = 'ns_selected_city';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [selectedCity, setSelectedCity] = useState<string | null>(
    () => localStorage.getItem(CITY_KEY),
  );
  // @ts-expect-error - loading bypassed for local dev, setLoading still used in effects
  const [loading, setLoading] = useState(true);

  // Listen to Supabase auth state changes (handles initial session + OAuth redirect)
  useEffect(() => {
    // Subscribe to auth changes FIRST — this catches the OAuth token exchange
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, s) => {
        setSession(s);
        setUser(s?.user ?? null);
        setLoading(false);

        // Clean up the URL hash after successful OAuth callback
        if (event === 'SIGNED_IN' && window.location.hash.includes('access_token')) {
          window.history.replaceState(null, '', '/');
        }
      },
    );

    // Check for existing session from localStorage
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<{ error?: string }> => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error: error.message };
    return {};
  }, []);

  const signup = useCallback(async (email: string, password: string): Promise<{ error?: string }> => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) return { error: error.message };
    return {};
  }, []);

  const loginWithGoogle = useCallback(async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    });
  }, []);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setSelectedCity(null);
    localStorage.removeItem(CITY_KEY);
  }, []);

  const selectCity = useCallback((city: string) => {
    setSelectedCity(city);
    localStorage.setItem(CITY_KEY, city);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: true, // TODO: revert — bypassed for local dev
        user,
        session,
        selectedCity,
        loading: false, // TODO: revert — bypassed for local dev
        login,
        signup,
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
