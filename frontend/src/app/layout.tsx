import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 生图导航 — 发现最好用的 AI 创作工具",
  description: "精选 AI 文本生图、图片编辑、视频生成平台，持续更新可用站点",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
