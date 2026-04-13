export default function Header({ stats }: { stats: any }) {
  return (
    <header style={{ background: "rgba(7,7,15,0.85)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      className="sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🎨</span>
          <span className="font-bold text-white text-sm tracking-tight">AI生图导航</span>
        </div>
        {stats && (
          <div className="flex items-center gap-2 text-xs" style={{ color: "#6b7280" }}>
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: "#34d399" }} />
            收录 <span className="text-white font-medium mx-1">{stats.total}</span> 个站点
          </div>
        )}
      </div>
    </header>
  );
}
