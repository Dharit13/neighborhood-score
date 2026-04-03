import { useState, useEffect, useCallback } from 'react';
import { Droplets, Wind, Thermometer } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

const WMO_CODES: Record<number, { desc: string; icon: string }> = {
  0: { desc: 'Clear sky', icon: '☀️' }, 1: { desc: 'Mainly clear', icon: '🌤️' },
  2: { desc: 'Partly cloudy', icon: '⛅' }, 3: { desc: 'Overcast', icon: '☁️' },
  45: { desc: 'Foggy', icon: '🌫️' }, 48: { desc: 'Rime fog', icon: '🌫️' },
  51: { desc: 'Light drizzle', icon: '🌦️' }, 53: { desc: 'Drizzle', icon: '🌦️' },
  55: { desc: 'Dense drizzle', icon: '🌧️' }, 61: { desc: 'Light rain', icon: '🌦️' },
  63: { desc: 'Rain', icon: '🌧️' }, 65: { desc: 'Heavy rain', icon: '🌧️' },
  71: { desc: 'Light snow', icon: '❄️' }, 73: { desc: 'Snow', icon: '❄️' },
  75: { desc: 'Heavy snow', icon: '❄️' }, 80: { desc: 'Rain showers', icon: '🌧️' },
  81: { desc: 'Moderate showers', icon: '🌧️' }, 82: { desc: 'Violent showers', icon: '⛈️' },
  95: { desc: 'Thunderstorm', icon: '⛈️' }, 96: { desc: 'Thunderstorm + hail', icon: '⛈️' },
  99: { desc: 'Thunderstorm + heavy hail', icon: '⛈️' },
};

function getWeatherInfo(code: number) {
  return WMO_CODES[code] ?? { desc: 'Unknown', icon: '🌡️' };
}

function timeAgo(dateStr: string): string {
  if (!dateStr) return '';
  const diff = Math.max(0, Date.now() - new Date(dateStr).getTime());
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function getDayName(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (d.getTime() === today.getTime()) return 'Today';
  return d.toLocaleDateString('en-US', { weekday: 'short' });
}

function formatDate(): string {
  return new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

interface WeatherData {
  city: string;
  current: { temperature: number; apparent_temperature: number; humidity: number; wind_speed: number; weather_code: number };
  daily: Array<{ date: string; weather_code: number; temp_max: number; temp_min: number }>;
}
interface NewsArticle { title: string; source: string; published: string; link: string; thumbnail: string; category: string }
interface NewsData { city: string; articles: NewsArticle[] }

interface CityData {
  population: string; area: string; density: string; founded: string;
  nickname: string; tagline: string; history: string;
  landmarks: number; parks: number; techParks: number;
  photos: { hero: string; street: string; landmark: string; skyline: string };
}

const CITY_DATA: Record<string, CityData> = {
  bengaluru: {
    population: '1.35 Cr', area: '741', density: '18,200', founded: '1537',
    nickname: 'Silicon Valley of India',
    tagline: 'Where tradition meets innovation',
    history: 'Founded in 1537 by Kempe Gowda I, Bengaluru evolved from a mud-fort town into India\'s tech capital. The IT revolution of the 1990s brought Infosys, Wipro, and 400+ R&D centres here, transforming the city\'s landscape forever. Today, the city is home to over 67 tech parks, 800+ public parks, and a vibrant cultural scene that blends Dravidian heritage with cosmopolitan ambition.',
    landmarks: 45, parks: 800, techParks: 67,
    photos: {
      hero: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800&h=600&fit=crop&q=80',
      street: 'https://images.unsplash.com/photo-1580581096469-8afb39cd0655?w=600&h=400&fit=crop&q=80',
      landmark: 'https://images.unsplash.com/photo-1600689182327-cb0e3e0f1ab3?w=600&h=400&fit=crop&q=80',
      skyline: 'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=1200&h=400&fit=crop&q=80',
    },
  },
  mumbai: {
    population: '2.1 Cr', area: '603', density: '34,800', founded: '1507',
    nickname: 'City of Dreams',
    tagline: 'The city that never sleeps',
    history: 'Originally seven islands, Mumbai was ceded to the British in 1661 and became India\'s financial capital. Home to BSE, RBI, and Bollywood — producing 1,500+ films annually. The city\'s spirit is defined by its legendary resilience, its crowded local trains carrying 8 million commuters daily, and a cultural tapestry woven from every corner of the subcontinent.',
    landmarks: 62, parks: 300, techParks: 45,
    photos: {
      hero: 'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=800&h=600&fit=crop&q=80',
      street: 'https://images.unsplash.com/photo-1567157577867-05ccb1388e13?w=600&h=400&fit=crop&q=80',
      landmark: 'https://images.unsplash.com/photo-1529253355930-ddbe423a2ac7?w=600&h=400&fit=crop&q=80',
      skyline: 'https://images.unsplash.com/photo-1566552881560-0be862a7c445?w=1200&h=400&fit=crop&q=80',
    },
  },
  delhi: {
    population: '3.2 Cr', area: '1,484', density: '21,500', founded: '~600 BCE',
    nickname: 'Heart of India',
    tagline: 'Capital of seven empires',
    history: 'Continuously inhabited since the 6th century BCE, Delhi served as capital of several empires. Shah Jahan built Shahjahanabad in 1639. The British moved the capital here in 1911. Today, Delhi is the political nerve centre of the world\'s largest democracy, home to 174 monuments and a metro network spanning over 390 kilometres.',
    landmarks: 174, parks: 500, techParks: 38,
    photos: {
      hero: 'https://images.unsplash.com/photo-1587474260584-136574528ed5?w=800&h=600&fit=crop&q=80',
      street: 'https://images.unsplash.com/photo-1597040663342-45b6ba68fa1e?w=600&h=400&fit=crop&q=80',
      landmark: 'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=600&h=400&fit=crop&q=80',
      skyline: 'https://images.unsplash.com/photo-1564823839403-3f8e06d376d6?w=1200&h=400&fit=crop&q=80',
    },
  },
};

// Ink-on-paper colors
const INK = '#1a1a1a';
const INK_LIGHT = '#4a4a4a';
const INK_FAINT = '#8a8a8a';
const RULE = '#d0c8b8';
const RULE_DARK = '#a09888';

function Rule({ className = '' }: { className?: string }) {
  return <div className={`h-px ${className}`} style={{ background: RULE }} />;
}

function DoubleRule({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-col gap-[2px] ${className}`}>
      <div className="h-[2px]" style={{ background: RULE_DARK }} />
      <div className="h-px" style={{ background: RULE }} />
    </div>
  );
}

function WeatherSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-14 rounded" style={{ background: 'rgba(0,0,0,0.05)' }} />
    </div>
  );
}

function NewsSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {[...Array(3)].map((_, i) => <div key={i} className="h-20 rounded" style={{ background: 'rgba(0,0,0,0.05)' }} />)}
    </div>
  );
}

export default function CityDashboard() {
  const { selectedCity } = useAuth();
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [news, setNews] = useState<NewsData | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(true);
  const [newsLoading, setNewsLoading] = useState(true);
  const [batchIndex, setBatchIndex] = useState(0);
  const [fading, setFading] = useState(false);

  const city = selectedCity ?? 'Bengaluru';
  const BATCH_SIZE = 8;
  const ROTATE_INTERVAL = 15000;
  const totalBatches = news ? Math.ceil(news.articles.length / BATCH_SIZE) : 0;
  const currentBatch = news ? news.articles.slice(batchIndex * BATCH_SIZE, (batchIndex + 1) * BATCH_SIZE) : [];

  const rotateBatch = useCallback(() => {
    if (totalBatches <= 1) return;
    setFading(true);
    setTimeout(() => { setBatchIndex((prev) => (prev + 1) % totalBatches); setFading(false); }, 400);
  }, [totalBatches]);

  useEffect(() => {
    if (totalBatches <= 1) return;
    const timer = setInterval(rotateBatch, ROTATE_INTERVAL);
    return () => clearInterval(timer);
  }, [rotateBatch, totalBatches]);

  useEffect(() => {
    let cancelled = false;
    async function fetchWeather() {
      setWeatherLoading(true);
      try {
        const resp = await apiFetch(`/api/weather?city=${encodeURIComponent(city)}`);
        if (!resp.ok) throw new Error('fail');
        const data = await resp.json();
        if (!cancelled) setWeather(data);
      } catch { /* skip */ } finally { if (!cancelled) setWeatherLoading(false); }
    }
    async function fetchNews() {
      setNewsLoading(true);
      try {
        const resp = await apiFetch(`/api/news?city=${encodeURIComponent(city)}`);
        if (!resp.ok) throw new Error('fail');
        const data = await resp.json();
        if (!cancelled) setNews(data);
      } catch { /* skip */ } finally { if (!cancelled) setNewsLoading(false); }
    }
    fetchWeather();
    fetchNews();
    return () => { cancelled = true; };
  }, [city]);

  const d = CITY_DATA[city.toLowerCase()] ?? CITY_DATA['bengaluru'];

  const leadArticle = currentBatch[0];
  const secondaryArticles = currentBatch.slice(1, 3);
  const columnArticles = currentBatch.slice(3);

  return (
    <div className="max-w-7xl">

      {/* DATE BAR */}
      <DoubleRule />
      <div className="flex items-center justify-between py-2.5">
        <span className="text-[10px] uppercase tracking-[0.3em] font-medium" style={{ color: INK_FAINT }}>{formatDate()}</span>
        <span className="text-[10px] uppercase tracking-[0.3em] font-medium" style={{ color: INK_FAINT }}>{city} &middot; {d.nickname}</span>
      </div>
      <div className="h-[3px]" style={{ background: INK }} />

      {/* WEATHER TICKER */}
      <div className="py-3">
        {weatherLoading ? <WeatherSkeleton /> : weather ? (
          <div className="flex items-center gap-6 overflow-x-auto">
            <div className="flex items-center gap-3 flex-shrink-0">
              <span className="text-3xl">{getWeatherInfo(weather.current.weather_code).icon}</span>
              <div>
                <span className="text-2xl font-bold tracking-tight" style={{ color: INK }}>
                  {Math.round(weather.current.temperature)}°C
                </span>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: INK_FAINT }}>{getWeatherInfo(weather.current.weather_code).desc}</p>
              </div>
            </div>
            <div className="w-px h-8 flex-shrink-0" style={{ background: RULE }} />
            <div className="flex items-center gap-5 text-xs flex-shrink-0" style={{ color: INK_LIGHT }}>
              <span className="flex items-center gap-1.5"><Thermometer className="w-3.5 h-3.5" style={{ color: INK_FAINT }} />Feels {Math.round(weather.current.apparent_temperature)}°</span>
              <span className="flex items-center gap-1.5"><Droplets className="w-3.5 h-3.5" style={{ color: INK_FAINT }} />{weather.current.humidity}%</span>
              <span className="flex items-center gap-1.5"><Wind className="w-3.5 h-3.5" style={{ color: INK_FAINT }} />{weather.current.wind_speed} km/h</span>
            </div>
            <div className="w-px h-8 flex-shrink-0" style={{ background: RULE }} />
            <div className="flex gap-4 flex-shrink-0">
              {weather.daily.slice(0, 5).map((day, i) => (
                <div key={day.date} className="text-center">
                  <p className="text-[9px] font-bold uppercase tracking-wider" style={{ color: i === 0 ? INK_LIGHT : INK_FAINT }}>
                    {getDayName(day.date)}
                  </p>
                  <p className="text-base my-0.5">{getWeatherInfo(day.weather_code).icon}</p>
                  <p className="text-[10px] font-medium" style={{ color: INK_LIGHT }}>{Math.round(day.temp_max)}°/{Math.round(day.temp_min)}°</p>
                </div>
              ))}
            </div>
          </div>
        ) : <p className="text-sm" style={{ color: INK_FAINT }}>Weather unavailable</p>}
      </div>
      <Rule />

      {/* FRONT PAGE */}
      <div className={`grid grid-cols-1 lg:grid-cols-12 gap-0 transition-opacity duration-400 ${fading ? 'opacity-0' : 'opacity-100'}`}>

        {/* LEFT COLUMN: Lead story */}
        <div className="lg:col-span-7 lg:border-r lg:pr-8 py-6" style={{ borderColor: RULE }}>
          {newsLoading ? <NewsSkeleton /> : leadArticle ? (
            <a href={leadArticle.link} target="_blank" rel="noopener noreferrer" className="group block">
              <h3 className="text-[28px] sm:text-[34px] lg:text-[40px] font-bold leading-[1.08] tracking-tight transition-colors"
                  style={{ color: INK }}>
                {leadArticle.title}
              </h3>
              <Rule className="my-4" />
              {leadArticle.thumbnail && (
                <div className="relative overflow-hidden mb-4">
                  <img src={leadArticle.thumbnail} alt="" className="w-full h-[320px] sm:h-[400px] object-cover transition-all duration-700" />
                </div>
              )}
              <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider" style={{ color: INK_FAINT }}>
                {leadArticle.category && leadArticle.category !== 'General' && (
                  <span className="font-bold" style={{ color: INK_LIGHT }}>{leadArticle.category}</span>
                )}
                {leadArticle.source && <span>{leadArticle.source}</span>}
                <span>{timeAgo(leadArticle.published)}</span>
              </div>
            </a>
          ) : (
            <div className="py-12 text-center">
              <p className="text-sm" style={{ color: INK_FAINT }}>No recent stories available</p>
            </div>
          )}

          {/* Secondary stories */}
          {secondaryArticles.length > 0 && (
            <>
              <Rule className="my-5" />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-0">
                {secondaryArticles.map((article, i) => (
                  <a key={`sec-${batchIndex}-${i}`} href={article.link} target="_blank" rel="noopener noreferrer"
                    className={`group block py-3 ${i === 0 ? 'sm:pr-6 sm:border-r' : 'sm:pl-6'}`}
                    style={{ borderColor: RULE }}>
                    {article.thumbnail && (
                      <img src={article.thumbnail} alt="" className="w-full h-44 object-cover mb-3 transition-all duration-700" />
                    )}
                    <h4 className="text-[15px] font-bold leading-snug transition-colors"
                        style={{ color: INK }}>
                      {article.title}
                    </h4>
                    <div className="flex items-center gap-2 mt-2 text-[9px] uppercase tracking-wider" style={{ color: INK_FAINT }}>
                      {article.source && <span>{article.source}</span>}
                      <span>{timeAgo(article.published)}</span>
                    </div>
                  </a>
                ))}
              </div>
            </>
          )}
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="lg:col-span-5 lg:pl-8 py-6">

          {/* City portrait */}
          <div className="relative overflow-hidden mb-5">
            <img src={d.photos.hero} alt={city} className="w-full h-[200px] object-cover" />
            <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(245,240,232,0.95) 0%, rgba(245,240,232,0.3) 40%, transparent 70%)' }} />
            <div className="absolute bottom-3 left-4 right-4">
              <p className="text-[9px] uppercase tracking-[0.3em] font-bold" style={{ color: INK_FAINT }}>{d.tagline}</p>
              <h3 className="text-xl font-bold mt-0.5" style={{ color: INK }}>{city}</h3>
            </div>
          </div>

          {/* City stats box */}
          <div className="border p-4 mb-5" style={{ borderColor: RULE_DARK }}>
            <h4 className="text-[10px] uppercase tracking-[0.25em] font-bold text-center mb-3" style={{ color: INK_FAINT }}>City At A Glance</h4>
            <Rule className="mb-3" />
            <div className="grid grid-cols-3 gap-3 text-center">
              {[
                { val: d.population, label: 'Population' },
                { val: `${d.area} km²`, label: 'Area' },
                { val: d.founded, label: 'Founded' },
              ].map(s => (
                <div key={s.label}>
                  <p className="text-xl font-bold" style={{ color: INK }}>{s.val}</p>
                  <p className="text-[9px] uppercase tracking-wider mt-0.5" style={{ color: INK_FAINT }}>{s.label}</p>
                </div>
              ))}
            </div>
            <Rule className="my-3" />
            <div className="grid grid-cols-3 gap-3 text-center">
              {[
                { val: d.landmarks, label: 'Landmarks' },
                { val: `${d.parks}+`, label: 'Parks' },
                { val: `${d.techParks}+`, label: 'Tech Parks' },
              ].map(s => (
                <div key={s.label}>
                  <p className="text-lg font-bold" style={{ color: INK_LIGHT }}>{s.val}</p>
                  <p className="text-[9px] uppercase tracking-wider mt-0.5" style={{ color: INK_FAINT }}>{s.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* City History */}
          <Rule className="mb-4" />
          <h4 className="text-[10px] uppercase tracking-[0.3em] font-bold mb-3" style={{ color: INK_FAINT }}>From The Archives</h4>
          <p className="text-[14px] leading-[1.85]" style={{ color: INK_LIGHT }}>
            {d.history}
          </p>

          {/* More headlines */}
          {columnArticles.length > 0 && (
            <>
              <Rule className="my-5" />
              <h4 className="text-[10px] uppercase tracking-[0.3em] font-bold mb-4" style={{ color: INK_FAINT }}>More Headlines</h4>
              <div className="space-y-0">
                {columnArticles.map((article, i) => (
                  <a key={`col-${batchIndex}-${i}`} href={article.link} target="_blank" rel="noopener noreferrer"
                    className="group block py-3 border-b last:border-b-0" style={{ borderColor: RULE }}>
                    <div className="flex gap-3">
                      <span className="text-[28px] font-bold leading-none flex-shrink-0 mt-0.5"
                            style={{ color: 'rgba(0,0,0,0.06)' }}>
                        {String(i + 4).padStart(2, '0')}
                      </span>
                      <div className="flex-1 min-w-0">
                        <h5 className="text-[13px] font-semibold leading-snug transition-colors line-clamp-2"
                            style={{ color: INK }}>
                          {article.title}
                        </h5>
                        <div className="flex items-center gap-2 mt-1.5 text-[9px] uppercase tracking-wider" style={{ color: INK_FAINT }}>
                          {article.category && article.category !== 'General' && (
                            <span className="font-bold" style={{ color: INK_LIGHT }}>{article.category}</span>
                          )}
                          {article.source && <span>{article.source}</span>}
                          <span>{timeAgo(article.published)}</span>
                        </div>
                      </div>
                      {article.thumbnail && (
                        <img src={article.thumbnail} alt="" className="w-20 h-20 object-cover flex-shrink-0 grayscale" />
                      )}
                    </div>
                  </a>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Pagination */}
      {totalBatches > 1 && (
        <>
          <Rule />
          <div className="flex items-center justify-center gap-4 py-4">
            <span className="text-[10px] uppercase tracking-widest" style={{ color: INK_FAINT }}>Page</span>
            <div className="flex gap-2">
              {Array.from({ length: totalBatches }).map((_, i) => (
                <button key={i}
                  onClick={() => { setFading(true); setTimeout(() => { setBatchIndex(i); setFading(false); }, 400); }}
                  className="w-7 h-7 text-xs font-bold transition-all border"
                  style={{
                    color: i === batchIndex ? INK : INK_FAINT,
                    borderColor: i === batchIndex ? INK_LIGHT : 'transparent',
                    background: i === batchIndex ? 'rgba(0,0,0,0.04)' : 'transparent',
                  }}>
                  {i + 1}
                </button>
              ))}
            </div>
            <span className="text-[10px] font-mono" style={{ color: INK_FAINT }}>{batchIndex + 1} of {totalBatches}</span>
          </div>
        </>
      )}

      {/* Footer */}
      <DoubleRule className="mt-2" />
      <div className="py-3">
        <span className="text-[9px] uppercase tracking-[0.3em]" style={{ color: RULE_DARK }}>Neighborhood Score &middot; Update</span>
      </div>
    </div>
  );
}
