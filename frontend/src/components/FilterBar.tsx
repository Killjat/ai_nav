const FILTERS = [
  { label: "全部",     value: "" },
  { label: "🖼 文本生图", value: "text_to_image" },
  { label: "✏️ 图片编辑", value: "image_edit" },
  { label: "🎬 视频生成", value: "video_gen" },
];

export default function FilterBar({ current, onChange, total }: {
  current: string; onChange: (v: string) => void; total: number;
}) {
  return (
    <div className="flex items-center justify-between flex-wrap gap-3 py-4"
      style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(f => (
          <button key={f.value} onClick={() => onChange(f.value)}
            className="px-4 py-2 rounded-xl text-sm font-medium transition-all"
            style={current === f.value ? {
              background: "#7c3aed", color: "#fff",
              boxShadow: "0 4px 20px rgba(124,58,237,0.35)"
            } : {
              background: "rgba(255,255,255,0.05)", color: "#9ca3af",
              border: "1px solid rgba(255,255,255,0.06)"
            }}>
            {f.label}
          </button>
        ))}
      </div>
      <span className="text-xs" style={{ color: "#374151" }}>{total} 个结果</span>
    </div>
  );
}
