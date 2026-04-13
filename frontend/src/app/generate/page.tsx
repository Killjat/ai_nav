"use client";
import { useState, useRef } from "react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8001";

type Status = "idle" | "pending" | "processing" | "done" | "failed";

export default function GeneratePage() {
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [imageUrl, setImageUrl] = useState("");
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [mode, setMode] = useState("image");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startTimer = () => {
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const pollTask = async (taskId: string) => {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 2000));
      const res = await fetch(`${GATEWAY}/task/${taskId}`);
      const data = await res.json();
      if (data.status === "done") {
        stopTimer();
        setStatus("done");
        setImageUrl(data.image_url);
        return;
      }
      if (data.status === "failed") {
        stopTimer();
        setStatus("failed");
        setError(data.error || "生成失败");
        return;
      }
    }
    stopTimer();
    setStatus("failed");
    setError("超时，请重试");
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setStatus("pending");
    setImageUrl("");
    setError("");
    startTimer();

    try {
      const res = await fetch(`${GATEWAY}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, mode }),
      });
      const data = await res.json();
      setStatus("processing");
      await pollTask(data.task_id);
    } catch (e) {
      stopTimer();
      setStatus("failed");
      setError("网络错误，请检查网关是否启动");
    }
  };

  const isLoading = status === "pending" || status === "processing";

  return (
    <div style={{ minHeight: "100vh", background: "#07070f", display: "flex", flexDirection: "column" }}>
      {/* 背景网格 */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none",
        backgroundImage: "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
        backgroundSize: "40px 40px"
      }} />

      {/* 顶部导航 */}
      <header style={{ background: "rgba(7,7,15,0.85)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(255,255,255,0.06)", position: "sticky", top: 0, zIndex: 50 }}>
        <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "0 24px", height: "56px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <a href="/" style={{ display: "flex", alignItems: "center", gap: "8px", textDecoration: "none" }}>
            <span style={{ fontSize: "20px" }}>🎨</span>
            <span style={{ fontWeight: 700, color: "white", fontSize: "14px" }}>AI生图导航</span>
          </a>
          <span style={{ fontSize: "13px", padding: "4px 12px", borderRadius: "999px", background: "rgba(124,58,237,0.15)", color: "#a78bfa", border: "1px solid rgba(124,58,237,0.3)" }}>
            ✦ AI 生图
          </span>
        </div>
      </header>

      {/* 主体 */}
      <main style={{ flex: 1, maxWidth: "800px", width: "100%", margin: "0 auto", padding: "48px 24px", position: "relative", zIndex: 1 }}>

        {/* 标题 */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <h1 style={{ fontSize: "36px", fontWeight: 700, color: "white", marginBottom: "8px" }}>
            输入描述，
            <span style={{ background: "linear-gradient(135deg, #a78bfa, #60a5fa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              AI 帮你生图
            </span>
          </h1>
          <p style={{ color: "#4b5563", fontSize: "15px" }}>免费调用，无需注册，生成约需 30-40 秒</p>
        </div>

        {/* 模式选择 */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "20px", justifyContent: "center" }}>
          {[
            { value: "image",        label: "🖼 文生图",   color: "#7c3aed" },
            { value: "jimeng_video", label: "🎬 即梦视频", color: "#db2777" },
            { value: "veo_video",    label: "🎥 Veo视频",  color: "#0891b2" },
            { value: "wan_video",    label: "📹 Wan视频",  color: "#059669" },
            { value: "tts",          label: "🔊 文本转语音", color: "#d97706" },
          ].map(m => (
            <button key={m.value} onClick={() => setMode(m.value)}
              style={{
                padding: "8px 18px", borderRadius: "999px", fontSize: "13px", fontWeight: 600,
                cursor: "pointer", border: "none", transition: "all 0.2s",
                background: mode === m.value ? m.color : "rgba(255,255,255,0.06)",
                color: mode === m.value ? "white" : "#6b7280",
                boxShadow: mode === m.value ? `0 4px 16px ${m.color}55` : "none",
              }}>
              {m.label}
            </button>
          ))}
        </div>

        {/* 输入区 */}
        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "24px" }}>
          <label style={{ display: "block", fontSize: "13px", color: "#6b7280", marginBottom: "10px", fontWeight: 500 }}>
            描述你想要的图片（支持中英文）
          </label>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="例如：一只可爱的橘猫坐在木桌上，柔和的光线，写实风格，4K画质"
            disabled={isLoading}
            rows={4}
            style={{
              width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "12px", padding: "14px 16px", color: "white", fontSize: "14px",
              resize: "none", outline: "none", lineHeight: "1.6", boxSizing: "border-box",
              opacity: isLoading ? 0.5 : 1,
            }}
          />

          {/* 示例 prompt */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px" }}>
            {["赛博朋克城市夜景", "水墨风山水画", "可爱的柴犬，动漫风格", "未来感宇宙飞船"].map(ex => (
              <button key={ex} onClick={() => setPrompt(ex)}
                disabled={isLoading}
                style={{ fontSize: "12px", padding: "4px 10px", borderRadius: "999px", background: "rgba(255,255,255,0.05)", color: "#6b7280", border: "1px solid rgba(255,255,255,0.08)", cursor: "pointer" }}>
                {ex}
              </button>
            ))}
          </div>

          {/* 生成按钮 */}
          <button
            onClick={handleGenerate}
            disabled={isLoading || !prompt.trim()}
            style={{
              marginTop: "16px", width: "100%", padding: "14px",
              borderRadius: "12px", fontSize: "15px", fontWeight: 600,
              cursor: isLoading || !prompt.trim() ? "not-allowed" : "pointer",
              background: isLoading || !prompt.trim()
                ? "rgba(124,58,237,0.3)"
                : "linear-gradient(135deg, #7c3aed, #4f46e5)",
              color: "white", border: "none",
              boxShadow: isLoading ? "none" : "0 4px 20px rgba(124,58,237,0.4)",
              transition: "all 0.2s",
            }}>
            {isLoading ? `⏳ 生成中... ${elapsed}s` : "✨ 立即生成"}
          </button>
        </div>

        {/* 结果区 */}
        {status !== "idle" && (
          <div style={{ marginTop: "32px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "24px", textAlign: "center" }}>

            {isLoading && (
              <div>
                <div style={{ fontSize: "48px", marginBottom: "16px" }}>
                  {status === "pending" ? "🔄" : "🎨"}
                </div>
                <p style={{ color: "#a78bfa", fontWeight: 600, marginBottom: "6px" }}>
                  {status === "pending" ? "正在分配站点..." : "AI 正在创作中..."}
                </p>
                <p style={{ color: "#374151", fontSize: "13px" }}>已等待 {elapsed} 秒，预计需要 30-40 秒</p>
                {/* 进度条 */}
                <div style={{ marginTop: "16px", height: "3px", background: "rgba(255,255,255,0.05)", borderRadius: "999px", overflow: "hidden" }}>
                  <div style={{
                    height: "100%", borderRadius: "999px",
                    background: "linear-gradient(90deg, #7c3aed, #60a5fa)",
                    width: `${Math.min((elapsed / 40) * 100, 95)}%`,
                    transition: "width 1s linear"
                  }} />
                </div>
              </div>
            )}

            {status === "done" && imageUrl && (
              <div>
                <p style={{ color: "#34d399", fontWeight: 600, marginBottom: "16px" }}>✅ 生成成功</p>
                {mode === "tts" ? (
                  <audio controls src={imageUrl} style={{ width: "100%", marginBottom: "16px" }} />
                ) : mode.includes("video") ? (
                  <video controls src={imageUrl} style={{ maxWidth: "100%", borderRadius: "12px", marginBottom: "16px" }} />
                ) : (
                  <img src={imageUrl} alt={prompt}
                    style={{ maxWidth: "100%", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.1)" }} />
                )}
                <div style={{ marginTop: "16px", display: "flex", gap: "12px", justifyContent: "center" }}>
                  <a href={imageUrl} download target="_blank" rel="noopener noreferrer"
                    style={{ padding: "10px 24px", borderRadius: "10px", background: "rgba(52,211,153,0.15)", color: "#34d399", border: "1px solid rgba(52,211,153,0.3)", textDecoration: "none", fontSize: "14px" }}>
                    ⬇ 下载图片
                  </a>
                  <button onClick={() => { setStatus("idle"); setImageUrl(""); setPrompt(""); }}
                    style={{ padding: "10px 24px", borderRadius: "10px", background: "rgba(124,58,237,0.15)", color: "#a78bfa", border: "1px solid rgba(124,58,237,0.3)", cursor: "pointer", fontSize: "14px" }}>
                    🔄 再生成一张
                  </button>
                </div>
              </div>
            )}

            {status === "failed" && (
              <div>
                <div style={{ fontSize: "48px", marginBottom: "12px" }}>❌</div>
                <p style={{ color: "#f87171", fontWeight: 600, marginBottom: "6px" }}>生成失败</p>
                <p style={{ color: "#374151", fontSize: "13px", marginBottom: "16px" }}>{error}</p>
                <button onClick={() => setStatus("idle")}
                  style={{ padding: "10px 24px", borderRadius: "10px", background: "rgba(248,113,113,0.15)", color: "#f87171", border: "1px solid rgba(248,113,113,0.3)", cursor: "pointer", fontSize: "14px" }}>
                  重试
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
