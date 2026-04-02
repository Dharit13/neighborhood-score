import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, type PanInfo } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';

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
    img: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=600&h=900&fit=crop&q=80',
  },
  {
    name: 'Mumbai',
    tag: 'Coming Soon',
    enabled: false,
    img: 'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=600&h=900&fit=crop&q=80',
  },
  {
    name: 'Delhi',
    tag: 'Coming Soon',
    enabled: false,
    img: 'https://images.unsplash.com/photo-1587474260584-136574528ed5?w=600&h=900&fit=crop&q=80',
  },
];

function CityCardStack({
  selectedCity,
  onSelect,
}: {
  selectedCity: string | null;
  onSelect: (city: string) => void;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const lastNavTime = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const cooldown = 400;

  const navigate = useCallback((direction: number) => {
    const now = Date.now();
    if (now - lastNavTime.current < cooldown) return;
    lastNavTime.current = now;

    setCurrentIndex((prev) => {
      if (direction > 0) return prev === CITIES.length - 1 ? 0 : prev + 1;
      return prev === 0 ? CITIES.length - 1 : prev - 1;
    });
  }, []);

  const handleDragEnd = (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const threshold = 50;
    if (info.offset.y < -threshold) navigate(1);
    else if (info.offset.y > threshold) navigate(-1);
  };

  // Scroll/wheel navigation scoped to the card container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) > 30) {
        e.preventDefault();
        navigate(e.deltaY > 0 ? 1 : -1);
      }
    };
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [navigate]);

  // Select city when card changes
  useEffect(() => {
    const city = CITIES[currentIndex];
    if (city.enabled) onSelect(city.name);
  }, [currentIndex, onSelect]);

  const getCardStyle = (index: number) => {
    const total = CITIES.length;
    let diff = index - currentIndex;
    if (diff > total / 2) diff -= total;
    if (diff < -total / 2) diff += total;

    if (diff === 0) return { y: 0, scale: 1, opacity: 1, zIndex: 5, rotateX: 0 };
    if (diff === -1) return { y: -150, scale: 0.85, opacity: 0.6, zIndex: 4, rotateX: 8 };
    if (diff === -2) return { y: -260, scale: 0.72, opacity: 0.3, zIndex: 3, rotateX: 15 };
    if (diff === 1) return { y: 150, scale: 0.85, opacity: 0.6, zIndex: 4, rotateX: -8 };
    if (diff === 2) return { y: 260, scale: 0.72, opacity: 0.3, zIndex: 3, rotateX: -15 };
    return { y: diff > 0 ? 380 : -380, scale: 0.6, opacity: 0, zIndex: 0, rotateX: diff > 0 ? -20 : 20 };
  };

  const isVisible = (index: number) => {
    const total = CITIES.length;
    let diff = index - currentIndex;
    if (diff > total / 2) diff -= total;
    if (diff < -total / 2) diff += total;
    return Math.abs(diff) <= 2;
  };

  return (
    <div className="relative flex items-center" ref={containerRef}>
      {/* Card stack */}
      <div
        className="relative flex items-center justify-center"
        style={{ width: 280, height: 500, perspective: '1200px' }}
      >
        {CITIES.map((city, index) => {
          if (!isVisible(index)) return null;
          const style = getCardStyle(index);
          const isCurrent = index === currentIndex;
          const isSelected = selectedCity === city.name;

          return (
            <motion.div
              key={city.name}
              className="absolute cursor-grab active:cursor-grabbing"
              animate={{
                y: style.y,
                scale: style.scale,
                opacity: style.opacity,
                rotateX: style.rotateX,
                zIndex: style.zIndex,
              }}
              transition={{ type: 'spring', stiffness: 300, damping: 30, mass: 1 }}
              drag={isCurrent ? 'y' : false}
              dragConstraints={{ top: 0, bottom: 0 }}
              dragElastic={0.2}
              onDragEnd={handleDragEnd}
              onClick={() => {
                if (index !== currentIndex) {
                  setCurrentIndex(index);
                } else if (city.enabled) {
                  onSelect(city.name);
                }
              }}
              style={{ transformStyle: 'preserve-3d', zIndex: style.zIndex }}
            >
              <div
                className="relative overflow-hidden rounded-3xl"
                style={{
                  width: 280,
                  height: 420,
                  border: isSelected
                    ? '2px solid rgba(42,213,135,0.7)'
                    : '1px solid rgba(255,255,255,0.1)',
                  boxShadow: isSelected
                    ? '0 0 40px rgba(42,213,135,0.3), 0 25px 50px -12px rgba(0,0,0,0.4)'
                    : isCurrent
                      ? '0 25px 50px -12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)'
                      : '0 10px 30px -10px rgba(0,0,0,0.4)',
                }}
              >
                {/* Inner glow */}
                <div className="absolute inset-0 rounded-3xl bg-gradient-to-b from-white/10 via-transparent to-transparent" />

                {/* City image */}
                <img
                  src={city.img}
                  alt={city.name}
                  className="absolute inset-0 w-full h-full object-cover"
                  draggable={false}
                />

                {/* Bottom gradient + city info */}
                <div
                  className="absolute inset-0 flex flex-col justify-end p-6"
                  style={{
                    background:
                      'linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.4) 40%, transparent 65%)',
                  }}
                >
                  <h3
                    className="text-[26px] font-medium leading-tight tracking-tight text-white"
                  >
                    {city.name}
                  </h3>
                  <p className="text-[11px] font-semibold tracking-[0.15em] uppercase mt-1.5" style={{ color: '#2ad587' }}>
                    {city.tag}
                  </p>
                </div>

                {/* Coming soon overlay */}
                {!city.enabled && (
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-[1px] flex items-center justify-center">
                    <span className="text-white/60 text-xs font-medium tracking-wider uppercase">Coming Soon</span>
                  </div>
                )}

                {/* Shimmer */}
                <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-white/[0.06] via-transparent to-transparent pointer-events-none" />
              </div>
            </motion.div>
          );
        })}
      </div>

    </div>
  );
}

export default function LoginPage() {
  const { login, signup, loginWithGoogle, selectCity, selectedCity } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [signUpSuccess, setSignUpSuccess] = useState(false);

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

  return (
    <section
      id="login-section"
      className="h-screen w-full flex select-none relative"
    >
      {/* Left: Vertical City Card Stack */}
      <div className="flex-1 flex items-center justify-end pr-24 relative overflow-hidden">
        {/* Ambient glow */}
        <div
          className="absolute top-1/2 left-1/2 w-[600px] h-[600px] -translate-x-1/2 -translate-y-1/2 pointer-events-none"
          style={{
            background:
              'radial-gradient(circle, rgba(0,114,96,0.12) 0%, rgba(42,213,135,0.06) 40%, transparent 70%)',
          }}
        />

        <div className="flex flex-col items-center gap-4">
          <CityCardStack selectedCity={selectedCity} onSelect={selectCity} />

          {/* Hint */}
          <motion.div
            className="flex flex-col items-center gap-1 text-white/30"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
          >
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 5v14M5 12l7-7 7 7" />
              </svg>
            </motion.div>
            <span className="text-[10px] font-medium tracking-widest uppercase">Scroll or drag</span>
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 5v14M19 12l-7 7-7-7" />
              </svg>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Right: Sign-In Form */}
      <div className="flex-1 flex items-center justify-start pl-12 relative">
        {/* Vertical divider */}
        <div
          className="absolute left-0 top-[10%] bottom-[10%] w-px"
          style={{ background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,0.06), transparent)' }}
        />

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
            <span className="text-lg font-semibold tracking-tight text-white">
              Neighborhood <span style={{ color: '#2ad587' }}>Score</span>
            </span>
          </div>

          <h1
            className="text-[32px] font-medium tracking-tight mb-2 text-white"
          >
            {isSignUp ? 'Create account' : 'Sign in'}
          </h1>
          <p className="text-sm text-white/50 mb-9 leading-relaxed">
            {isSignUp
              ? 'Sign up to start exploring neighborhood scores and builder trust ratings.'
              : `Sign in to explore neighborhood scores, commute data, and builder trust ratings${selectedCity ? ` across ${selectedCity}.` : '.'}`
            }
          </p>

          {signUpSuccess && (
            <div className="mb-5 p-3 rounded-xl border border-[#2ad587]/30 bg-[#2ad587]/10">
              <p className="text-sm text-[#2ad587]">Check your email for a confirmation link, then sign in.</p>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Email */}
            <div className="mb-5">
              <label className="block text-[11px] font-medium tracking-[0.08em] uppercase text-white mb-2">
                Email
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3.5 bg-white/[0.06] border border-white/30 rounded-xl text-white text-[15px] outline-none transition-all placeholder:text-white/25 focus:border-[#2ad587] focus:shadow-[0_0_0_3px_rgba(42,213,135,0.12)]"
              />
            </div>

            {/* Password */}
            <div className="mb-5">
              <label className="block text-[11px] font-medium tracking-[0.08em] uppercase text-white mb-2">
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3.5 bg-white/[0.06] border border-white/30 rounded-xl text-white text-[15px] outline-none transition-all placeholder:text-white/25 focus:border-[#2ad587] focus:shadow-[0_0_0_3px_rgba(42,213,135,0.12)]"
              />
            </div>

            {/* Error */}
            {error && (
              <p className="text-red-400 text-xs mb-3">{error}</p>
            )}

            {/* Sign In */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 rounded-xl text-[15px] font-semibold text-white tracking-[0.01em] transition-all hover:-translate-y-px hover:shadow-[0_8px_30px_rgba(42,213,135,0.25)] active:translate-y-0 disabled:opacity-60 border-none cursor-pointer"
              style={{ background: 'linear-gradient(135deg, #002c7c, #005075, #007260, #2ad587)' }}
            >
              {submitting
                ? (isSignUp ? 'Creating account\u2026' : 'Signing in\u2026')
                : (isSignUp ? 'Create Account' : 'Sign In')
              }
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-7">
            <div className="flex-1 h-px bg-white/[0.06]" />
            <span className="text-xs text-white/50 tracking-wide">or</span>
            <div className="flex-1 h-px bg-white/[0.06]" />
          </div>

          {/* Google */}
          <button
            onClick={handleGoogle}
            className="w-full py-3.5 bg-transparent border border-white/30 rounded-xl text-white text-sm font-medium flex items-center justify-center gap-2.5 transition-all hover:bg-white/[0.04] hover:border-white/[0.12] cursor-pointer"
          >
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
              <path fill="#FBBC05" d="M10.53 28.59a14.5 14.5 0 0 1 0-9.18l-7.98-6.19a24.01 24.01 0 0 0 0 21.56l7.98-6.19z" />
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
            </svg>
            Continue with Google
          </button>

          <p className="text-center mt-7 text-[13px] text-white/50">
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              type="button"
              className="text-[#2ad587] font-medium hover:underline bg-transparent border-none cursor-pointer"
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
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="18 15 12 9 6 15" />
        </svg>
        <span className="text-[10px] text-white tracking-[0.1em] uppercase">Back</span>
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
      `}</style>
    </section>
  );
}
