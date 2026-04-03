import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { ProgressiveBlurCard } from '@/components/ui/progressive-blur-card';

interface CityData {
  name: string;
  tag: string;
  enabled: boolean;
  img: string;
}

const CITIES: CityData[] = [
  {
    name: 'Bengaluru',
    tag: "India's Silicon Valley",
    enabled: true,
    img: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800&h=800&fit=crop&q=80',
  },
  {
    name: 'Mumbai',
    tag: 'Coming Soon',
    enabled: false,
    img: 'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=800&h=800&fit=crop&q=80',
  },
  {
    name: 'Delhi',
    tag: 'Coming Soon',
    enabled: false,
    img: 'https://images.unsplash.com/photo-1587474260584-136574528ed5?w=800&h=800&fit=crop&q=80',
  },
];

export default function LoginPage() {
  const { login, signup, loginWithGoogle, selectCity, selectedCity } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [signUpSuccess, setSignUpSuccess] = useState(false);
  const [activeCity, setActiveCity] = useState(0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    if (!selectedCity) {
      setError('Please select a city first');
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      if (isSignUp) {
        const result = await signup(email, password);
        if (result.error) {
          setError(result.error);
        } else {
          setSignUpSuccess(true);
        }
      } else {
        const result = await login(email, password);
        if (result.error) {
          setError(result.error);
        }
      }
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogle = async () => {
    if (!selectedCity) {
      selectCity('Bengaluru');
    }
    await loginWithGoogle();
  };

  const handleCitySelect = (index: number) => {
    setActiveCity(index);
    const city = CITIES[index];
    if (city.enabled) selectCity(city.name);
  };

  return (
    <section
      id="login-section"
      className="h-screen w-full flex select-none relative overflow-hidden"
      style={{ background: '#f5f0e8' }}
    >
      {/* Left: City Card */}
      <div className="flex-1 flex items-center justify-center relative z-10">
        <div className="flex flex-col items-center">
          {/* City selector dots */}
          <div className="flex items-center gap-3 mb-6">
            {CITIES.map((city, i) => (
              <button
                key={city.name}
                onClick={() => handleCitySelect(i)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-all cursor-pointer border-none"
                style={{
                  background: activeCity === i ? '#1a1a1a' : 'transparent',
                  color: activeCity === i ? '#f5f0e8' : '#8a8a8a',
                }}
              >
                <span className="text-[11px] font-medium tracking-wide">{city.name}</span>
              </button>
            ))}
          </div>

          {/* Progressive blur card */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeCity}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.3 }}
            >
              <ProgressiveBlurCard
                imageSrc={CITIES[activeCity].img}
                imageAlt={CITIES[activeCity].name}
                title={`${CITIES[activeCity].name},`}
                subtitle={CITIES[activeCity].tag}
                selected={selectedCity === CITIES[activeCity].name}
                enabled={CITIES[activeCity].enabled}
              />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Vertical divider */}
      <div
        className="absolute left-1/2 top-[10%] bottom-[10%] w-px z-10"
        style={{ background: 'linear-gradient(to bottom, transparent, #d0c8b8, transparent)' }}
      />

      {/* Right: Sign-In Form */}
      <div className="flex-1 flex items-center justify-start pl-12 relative z-10">
        <div className="w-full max-w-[380px]">
          {/* Brand */}
          <div className="flex items-center gap-2.5 mb-12">
            <div
              className="w-9 h-9 rounded-[10px] flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #002c7c, #005075, #007260, #2ad587)' }}
            >
              <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="#000" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
            </div>
            <span className="text-lg font-semibold tracking-tight" style={{ color: '#1a1a1a' }}>
              Neighborhood <span style={{ color: '#007260' }}>Score</span>
            </span>
          </div>

          <h1 className="text-[32px] font-medium tracking-tight mb-2" style={{ color: '#1a1a1a' }}>
            {isSignUp ? 'Create account' : 'Sign in'}
          </h1>
          <p className="text-sm mb-9 leading-relaxed" style={{ color: '#8a8a8a' }}>
            {isSignUp
              ? 'Sign up to start exploring neighborhood scores and builder trust ratings.'
              : `Sign in to explore neighborhood scores, commute data, and builder trust ratings${selectedCity ? ` across ${selectedCity}.` : '.'}`
            }
          </p>

          {signUpSuccess && (
            <div className="mb-5 p-3 rounded-xl border border-emerald-200 bg-emerald-50">
              <p className="text-sm text-emerald-700">Check your email for a confirmation link, then sign in.</p>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Email */}
            <div className="mb-5">
              <label className="block text-[11px] font-medium tracking-[0.08em] uppercase mb-2" style={{ color: '#4a4a4a' }}>
                Email
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3.5 rounded-xl text-[15px] outline-none transition-all"
                style={{
                  background: 'rgba(255,255,255,0.5)',
                  border: '1px solid #d0c8b8',
                  color: '#1a1a1a',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#1a1a1a';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(26,26,26,0.06)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = '#d0c8b8';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>

            {/* Password */}
            <div className="mb-5">
              <label className="block text-[11px] font-medium tracking-[0.08em] uppercase mb-2" style={{ color: '#4a4a4a' }}>
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3.5 rounded-xl text-[15px] outline-none transition-all"
                style={{
                  background: 'rgba(255,255,255,0.5)',
                  border: '1px solid #d0c8b8',
                  color: '#1a1a1a',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#1a1a1a';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(26,26,26,0.06)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = '#d0c8b8';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>

            {/* Error */}
            {error && (
              <p className="text-red-700 text-xs mb-3">{error}</p>
            )}

            {/* Sign In */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 rounded-xl text-[15px] font-semibold tracking-[0.01em] transition-all hover:-translate-y-px active:translate-y-0 disabled:opacity-60 border-none cursor-pointer"
              style={{ background: '#1a1a1a', color: '#f5f0e8' }}
            >
              {submitting
                ? (isSignUp ? 'Creating account\u2026' : 'Signing in\u2026')
                : (isSignUp ? 'Create Account' : 'Sign In')
              }
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-7">
            <div className="flex-1 h-px" style={{ background: '#d0c8b8' }} />
            <span className="text-xs tracking-wide" style={{ color: '#a09888' }}>or</span>
            <div className="flex-1 h-px" style={{ background: '#d0c8b8' }} />
          </div>

          {/* Google */}
          <button
            onClick={handleGoogle}
            className="w-full py-3.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2.5 transition-all cursor-pointer"
            style={{
              background: 'transparent',
              border: '1px solid #d0c8b8',
              color: '#1a1a1a',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.5)';
              e.currentTarget.style.borderColor = '#a09888';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.borderColor = '#d0c8b8';
            }}
          >
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
              <path fill="#FBBC05" d="M10.53 28.59a14.5 14.5 0 0 1 0-9.18l-7.98-6.19a24.01 24.01 0 0 0 0 21.56l7.98-6.19z" />
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
            </svg>
            Continue with Google
          </button>

          <p className="text-center mt-7 text-[13px]" style={{ color: '#8a8a8a' }}>
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              type="button"
              className="font-medium hover:underline bg-transparent border-none cursor-pointer"
              style={{ color: '#1a1a1a' }}
              onClick={() => { setIsSignUp(!isSignUp); setError(''); setSignUpSuccess(false); }}
            >
              {isSignUp ? 'Sign in' : 'Create one'}
            </button>
          </p>
        </div>
      </div>

      {/* Back to top */}
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        className="absolute top-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 bg-transparent border-none cursor-pointer opacity-40 hover:opacity-80 transition-opacity"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1a1a1a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="18 15 12 9 6 15" />
        </svg>
        <span className="text-[10px] tracking-[0.1em] uppercase" style={{ color: '#1a1a1a' }}>Back</span>
      </button>

      {/* Responsive */}
      <style>{`
        @media (max-width: 900px) {
          #login-section {
            flex-direction: column !important;
          }
          #login-section > div:first-of-type {
            min-height: 60vh;
          }
          #login-section > div:nth-of-type(2) {
            padding: 48px 24px !important;
          }
        }
        #login-section input::placeholder {
          color: #a09888;
        }
      `}</style>
    </section>
  );
}
