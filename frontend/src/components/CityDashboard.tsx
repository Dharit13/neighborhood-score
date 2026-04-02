import { useState, useEffect } from 'react';
import { Droplets, Wind, Thermometer, ExternalLink } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

// WMO Weather Code mapping to description + icon
const WMO_CODES: Record<number, { desc: string; icon: string }> = {
  0: { desc: 'Clear sky', icon: '☀️' },
  1: { desc: 'Mainly clear', icon: '🌤️' },
  2: { desc: 'Partly cloudy', icon: '⛅' },
  3: { desc: 'Overcast', icon: '☁️' },
  45: { desc: 'Foggy', icon: '🌫️' },
  48: { desc: 'Rime fog', icon: '🌫️' },
  51: { desc: 'Light drizzle', icon: '🌦️' },
  53: { desc: 'Drizzle', icon: '🌦️' },
  55: { desc: 'Dense drizzle', icon: '🌧️' },
  61: { desc: 'Light rain', icon: '🌦️' },
  63: { desc: 'Rain', icon: '🌧️' },
  65: { desc: 'Heavy rain', icon: '🌧️' },
  71: { desc: 'Light snow', icon: '❄️' },
  73: { desc: 'Snow', icon: '❄️' },
  75: { desc: 'Heavy snow', icon: '❄️' },
  80: { desc: 'Rain showers', icon: '🌧️' },
  81: { desc: 'Moderate showers', icon: '🌧️' },
  82: { desc: 'Violent showers', icon: '⛈️' },
  95: { desc: 'Thunderstorm', icon: '⛈️' },
  96: { desc: 'Thunderstorm + hail', icon: '⛈️' },
  99: { desc: 'Thunderstorm + heavy hail', icon: '⛈️' },
};

function getWeatherInfo(code: number) {
  return WMO_CODES[code] ?? { desc: 'Unknown', icon: '🌡️' };
}

function timeAgo(dateStr: string): string {
  if (!dateStr) return '';
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.max(0, now - then);
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function getDayName(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (d.getTime() === today.getTime()) return 'Today';
  return d.toLocaleDateString('en-US', { weekday: 'short' });
}

interface WeatherData {
  city: string;
  current: {
    temperature: number;
    apparent_temperature: number;
    humidity: number;
    wind_speed: number;
    weather_code: number;
  };
  daily: Array<{
    date: string;
    weather_code: number;
    temp_max: number;
    temp_min: number;
  }>;
}

interface NewsArticle {
  title: string;
  source: string;
  published: string;
  link: string;
  thumbnail: string;
}

interface NewsData {
  city: string;
  articles: NewsArticle[];
}

// Skeleton loader
function WeatherSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-16 bg-white/[0.06] rounded-lg" />
      <div className="flex gap-4">
        <div className="h-8 w-24 bg-white/[0.06] rounded" />
        <div className="h-8 w-24 bg-white/[0.06] rounded" />
        <div className="h-8 w-24 bg-white/[0.06] rounded" />
      </div>
      <div className="flex gap-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-20 flex-1 bg-white/[0.06] rounded" />
        ))}
      </div>
    </div>
  );
}

function NewsSkeleton() {
  return (
    <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-24 bg-white/[0.06] rounded-lg" />
      ))}
    </div>
  );
}

export default function CityDashboard() {
  const { selectedCity } = useAuth();
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [news, setNews] = useState<NewsData | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(true);
  const [newsLoading, setNewsLoading] = useState(true);

  const city = selectedCity ?? 'Bengaluru';

  useEffect(() => {
    let cancelled = false;

    async function fetchWeather() {
      setWeatherLoading(true);
      try {
        const resp = await apiFetch(`/api/weather?city=${encodeURIComponent(city)}`);
        if (!resp.ok) throw new Error('Weather fetch failed');
        const data = await resp.json();
        if (!cancelled) setWeather(data);
      } catch (err) {
        console.error('Weather fetch error:', err);
      } finally {
        if (!cancelled) setWeatherLoading(false);
      }
    }

    async function fetchNews() {
      setNewsLoading(true);
      try {
        const resp = await apiFetch(`/api/news?city=${encodeURIComponent(city)}`);
        if (!resp.ok) throw new Error('News fetch failed');
        const data = await resp.json();
        if (!cancelled) setNews(data);
      } catch (err) {
        console.error('News fetch error:', err);
      } finally {
        if (!cancelled) setNewsLoading(false);
      }
    }

    fetchWeather();
    fetchNews();

    return () => { cancelled = true; };
  }, [city]);

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* Weather Card — left 40% */}
      <div className="lg:w-[40%] bg-white/[0.03] backdrop-blur-sm rounded-2xl border border-white/[0.08] p-6">
        {weatherLoading ? (
          <WeatherSkeleton />
        ) : weather ? (
          <div className="space-y-5">
            {/* Current weather */}
            <div className="flex items-start justify-between">
              <div>
                <span className="text-6xl font-bold text-white">
                  {Math.round(weather.current.temperature)}°
                </span>
                <p className="text-white/60 text-sm mt-1">
                  {getWeatherInfo(weather.current.weather_code).desc}
                </p>
              </div>
              <span className="text-5xl">
                {getWeatherInfo(weather.current.weather_code).icon}
              </span>
            </div>

            {/* Stats row */}
            <div className="flex gap-4 text-sm text-white/70">
              <div className="flex items-center gap-1.5">
                <Thermometer className="w-4 h-4 text-brand-9" />
                <span>Feels {Math.round(weather.current.apparent_temperature)}°</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Droplets className="w-4 h-4 text-brand-9" />
                <span>{weather.current.humidity}%</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Wind className="w-4 h-4 text-brand-9" />
                <span>{weather.current.wind_speed} km/h</span>
              </div>
            </div>

            {/* 5-day forecast strip */}
            <div className="flex gap-2">
              {weather.daily.map((day) => (
                <div
                  key={day.date}
                  className="flex-1 bg-white/[0.04] rounded-lg p-2 text-center"
                >
                  <p className="text-xs text-white/50 font-medium">
                    {getDayName(day.date)}
                  </p>
                  <p className="text-lg my-1">
                    {getWeatherInfo(day.weather_code).icon}
                  </p>
                  <p className="text-xs text-white/80">
                    {Math.round(day.temp_max)}°
                  </p>
                  <p className="text-xs text-white/40">
                    {Math.round(day.temp_min)}°
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-white/40 text-sm">Weather data unavailable</p>
        )}
      </div>

      {/* News Grid — right 60% */}
      <div className="lg:w-[60%]">
        {newsLoading ? (
          <NewsSkeleton />
        ) : news && news.articles.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {news.articles.map((article, i) => (
              <a
                key={i}
                href={article.link}
                target="_blank"
                rel="noopener noreferrer"
                className="group bg-white/[0.03] backdrop-blur-sm rounded-xl border border-white/[0.08] p-4 hover:bg-white/[0.06] transition-colors"
              >
                <div className="flex gap-3">
                  {article.thumbnail && (
                    <img
                      src={article.thumbnail}
                      alt=""
                      className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm text-white font-medium line-clamp-2 group-hover:text-brand-9 transition-colors">
                      {article.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-2">
                      {article.source && (
                        <span className="text-xs bg-white/[0.08] text-white/60 px-2 py-0.5 rounded-full">
                          {article.source}
                        </span>
                      )}
                      <span className="text-xs text-white/40">
                        {timeAgo(article.published)}
                      </span>
                    </div>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-white/20 group-hover:text-white/50 flex-shrink-0 mt-1 transition-colors" />
                </div>
              </a>
            ))}
          </div>
        ) : (
          <p className="text-white/40 text-sm">No news articles available</p>
        )}
      </div>
    </div>
  );
}
