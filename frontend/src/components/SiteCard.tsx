"use client";
import { useState } from "react";

const FEATURES: Record<string, { label: string; bg: string; color: string }> = {
  text_to_image: { label: "文本生图", bg: "rgba(124,58,237,0.15)", color: "#a78bfa" },
  image_edit:    { label: "图片编辑", bg: "rgba(37,99,235,0.15)",  color: "#60a5fa" },
  video_gen:     { label: "视频生成", bg: "rgba(219,39,119,0.15)", color: "#f472b6" },
};

function getDomain(url: string) {
  try { return new URL(url).hostname; } catch { return url; }
}

export default function SiteCard({ site }: { site: any }) {
  const [hovered, setHovered] = useState(false);
  const features = Object.entries(site.features).filter(([, v]) => v).map(([k]) => FEATURES[k]).filter(Boolean);
  const domain = getDomain(site.url);

  return (
    <a href={site.url} target="_blank" rel="noopener noreferrer"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", flexDirection: "column", borderRadius: "16px", overflow: "hidden",
        background: hovered ? "rgba(124,58,237,0.07)" : "rgba(255,255,255,0.03)",
        border: `1px solid ${hovered ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.07)"}`,
        transform: hovered ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hovered ? "0 8px 40px rgba(124,58,237,0.2), 0 2px 8px rgba(0,0,0,0.4)" : "none",
        transition: "all 0.25s ease", textDecoration: "none",
      }}>

      {/* 预览区 */}
      <div style={{
        height: "130px", position: "relative", overflow: "hidden",
        background: "linear-gradient(135deg, rgba(124,58,237,0.08) 0%, rgba(37,99,235,0.05) 100%)",
        display: "flex", alignItems: "center", justifyContent: "center",
        borderBottom: "1px solid rgba(255,255,255,0.05)"
      }}>
        {/* favicon 大图 */}
        <div style={{
          width: "56px", height: "56px", borderRadius: "14px",
          background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
          display: "flex", alignItems: "center", justifyContent: "center"
        }}>
          <img
            src={`https://www.google.com/s2/favicons?sz=64&domain=${domain}`}
            alt="" style={{ width: "32px", height: "32px" }}
            onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
        {site.is_free && (
          <span style={{
            position: "absolute", top: "10px", right: "10px",
            background: "rgba(16,185,129,0.15)", color: "#34d399",
            border: "1px solid rgba(16,185,129,0.3)",
            padding: "2px 8px", borderRadius: "999px", fontSize: "11px", fontWeight: 500
          }}>免费</span>
        )}
      </div>

      {/* 内容 */}
      <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <img src={`https://www.google.com/s2/favicons?sz=16&domain=${domain}`}
            alt="" style={{ width: "14px", height: "14px", opacity: 0.6, flexShrink: 0 }}
            onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
          <span style={{
            fontSize: "13px", fontWeight: 600, color: hovered ? "#c4b5fd" : "#f1f5f9",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            transition: "color 0.2s"
          }}>
            {site.title || domain}
          </span>
        </div>

        <p style={{
          fontSize: "11px", color: "#4b5563", lineHeight: "1.5",
          overflow: "hidden", display: "-webkit-box",
          WebkitLineClamp: 2, WebkitBoxOrient: "vertical"
        }}>
          {site.description || domain}
        </p>

        {/* 标签 */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "auto", paddingTop: "6px" }}>
          {features.map((f, i) => f && (
            <span key={i} style={{
              fontSize: "11px", fontWeight: 500, padding: "2px 8px", borderRadius: "999px",
              background: f.bg, color: f.color
            }}>{f.label}</span>
          ))}
        </div>
      </div>
    </a>
  );
}
