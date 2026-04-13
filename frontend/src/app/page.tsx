"use client";
import { useEffect, useState, useMemo } from "react";
import SiteCard from "@/components/SiteCard";
import Header from "@/components/Header";
import Hero from "@/components/Hero";
import FilterBar from "@/components/FilterBar";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [sites, setSites] = useState<any[]>([]);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/api/stats`).then(r => r.json()).then(setStats);
  }, []);

  useEffect(() => {
    const url = filter ? `${API}/api/sites?feature=${filter}` : `${API}/api/sites`;
    setLoading(true);
    fetch(url).then(r => r.json()).then(d => { setSites(d); setLoading(false); });
  }, [filter]);

  const filtered = useMemo(() => {
    if (!search.trim()) return sites;
    const q = search.toLowerCase();
    return sites.filter(s =>
      s.title?.toLowerCase().includes(q) ||
      s.url?.toLowerCase().includes(q) ||
      s.description?.toLowerCase().includes(q)
    );
  }, [sites, search]);

  return (
    <div style={{ minHeight: "100vh", background: "#07070f" }}>
      {/* 全局背景网格 */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        backgroundImage: "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
        backgroundSize: "40px 40px"
      }} />

      <div style={{ position: "relative", zIndex: 1 }}>
        <Header stats={stats} />
        <Hero search={search} onSearch={setSearch} stats={stats} />

        <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px 80px" }}>
          <FilterBar current={filter} onChange={setFilter} total={filtered.length} />

          {loading ? (
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: "16px", marginTop: "24px"
            }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{
                  height: "220px", borderRadius: "16px",
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  animation: "pulse 1.5s ease-in-out infinite"
                }} />
              ))}
            </div>
          ) : (
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: "16px", marginTop: "24px"
            }}>
              {filtered.map(s => <SiteCard key={s.id} site={s} />)}
              {filtered.length === 0 && (
                <div style={{ gridColumn: "1/-1", textAlign: "center", padding: "80px 0", color: "#374151" }}>
                  <div style={{ fontSize: "48px", marginBottom: "12px" }}>🔍</div>
                  <p>没有找到匹配的站点</p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
