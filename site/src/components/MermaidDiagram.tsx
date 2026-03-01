"use client";

import { useEffect, useRef, useState } from "react";

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

export function MermaidDiagram({ chart, className = "" }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function renderChart() {
      const mermaid = (await import("mermaid")).default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "base",
        themeVariables: {
          primaryColor: "#e8f5ee",
          primaryTextColor: "#171717",
          primaryBorderColor: "#009c3b",
          secondaryColor: "#eef2ff",
          secondaryTextColor: "#171717",
          secondaryBorderColor: "#002776",
          tertiaryColor: "#fff9db",
          tertiaryTextColor: "#171717",
          tertiaryBorderColor: "#e6c900",
          lineColor: "#a3a3a3",
          fontFamily: "var(--font-geist-sans), Arial, sans-serif",
          fontSize: "14px",
          nodeTextColor: "#171717",
        },
        flowchart: {
          htmlLabels: true,
          curve: "basis",
          padding: 16,
          nodeSpacing: 30,
          rankSpacing: 50,
          useMaxWidth: true,
        },
      });

      const id = `mermaid-${Date.now()}`;
      try {
        const { svg: rendered } = await mermaid.render(id, chart);
        if (!cancelled) {
          setSvg(rendered);
        }
      } catch (err) {
        console.error("Mermaid render error:", err);
      }
    }

    renderChart();
    return () => {
      cancelled = true;
    };
  }, [chart]);

  if (!svg) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="w-8 h-8 border-2 border-brand-green border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex justify-center overflow-x-auto ${className}`}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
