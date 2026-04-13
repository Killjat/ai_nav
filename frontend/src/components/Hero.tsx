export default function Hero({ search, onSearch, stats }: {
  search: string; onSearch: (v: string) => void; stats: any;
}) {
  return (
    <section className="relative text-center px-6 pt-20 pb-14 max-w-6xl mx-auto">
      {/* 背景光晕 */}
      <div style={{
        position: "absolute", top: "-100px", left: "50%", transform: "translateX(-50%)",
        width: "600px", height: "300px", pointerEvents: "none",
        background: "radial-gradient(ellipse, rgba(124,58,237,0.18) 0%, transparent 70%)"
      }} />

      {/* badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mb-6"
        style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.3)", color: "#a78bfa" }}>
        <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "#a78bfa" }} />
        持续更新可用站点
      </div>

      {/* 标题 */}
      <h1 className="text-5xl font-bold tracking-tight mb-3 leading-tight text-white">
        发现最好用的
      </h1>
      <h1 className="text-5xl font-bold tracking-tight mb-6 leading-tight" style={{
        background: "linear-gradient(135deg, #a78bfa 0%, #60a5fa 50%, #34d399 100%)",
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
      }}>
        AI 创作工具
      </h1>

      <p className="text-lg mb-10 max-w-lg mx-auto" style={{ color: "#6b7280" }}>
        精选文本生图、图片编辑、视频生成平台，全部真实可访问
      </p>

      {/* 搜索框 */}
      <div className="relative max-w-lg mx-auto" style={{
        background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: "14px", transition: "box-shadow 0.2s"
      }}>
        <span className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "#4b5563", fontSize: "16px" }}>🔍</span>
        <input
          type="text" value={search} onChange={e => onSearch(e.target.value)}
          placeholder="搜索站点名称、功能..."
          className="w-full pl-11 pr-10 py-4 text-sm text-white outline-none"
          style={{ background: "transparent", borderRadius: "14px", caretColor: "#a78bfa" }}
        />
        {search && (
          <button onClick={() => onSearch("")}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-xl"
            style={{ color: "#4b5563" }}>×</button>
        )}
      </div>

      {/* 统计 */}
      {stats && (
        <div className="flex justify-center gap-10 mt-10">
          {[
            { label: "文本生图", value: stats.text_to_image, color: "#a78bfa" },
            { label: "图片编辑", value: stats.image_edit,    color: "#60a5fa" },
            { label: "视频生成", value: stats.video_gen,     color: "#f472b6" },
          ].map(item => (
            <div key={item.label} className="text-center">
              <div className="text-3xl font-bold" style={{ color: item.color }}>{item.value}</div>
              <div className="text-xs mt-1" style={{ color: "#4b5563" }}>{item.label}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
