"use client";

import { Badge } from "@/components/ui/badge";

interface AlinhamentoBadgeProps {
  alinhamento: number;
  className?: string;
}

/**
 * Renders a coloured badge indicating alignment level (0–1 scale).
 *
 * ≥ 0.7  → green  (Alinhado)
 * ≥ 0.4  → yellow (Parcial)
 * < 0.4  → red    (Divergente)
 */
export function AlinhamentoBadge({
  alinhamento,
  className,
}: AlinhamentoBadgeProps) {
  const pct = Math.round(alinhamento * 100);

  let label: string;
  let color: string;

  if (alinhamento >= 0.7) {
    label = "Alinhado";
    color = "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
  } else if (alinhamento >= 0.4) {
    label = "Parcial";
    color =
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
  } else {
    label = "Divergente";
    color = "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  }

  return (
    <Badge variant="outline" className={`${color} ${className ?? ""}`}>
      {pct}% — {label}
    </Badge>
  );
}

interface ResultadoBadgeProps {
  resultado: "APROVADO" | "REJEITADO";
  className?: string;
}

/**
 * Renders a badge for the parliament vote result.
 */
export function ResultadoBadge({ resultado, className }: ResultadoBadgeProps) {
  const color =
    resultado === "APROVADO"
      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";

  return (
    <Badge variant="outline" className={`${color} ${className ?? ""}`}>
      {resultado === "APROVADO" ? "✓ Aprovado" : "✗ Rejeitado"}
    </Badge>
  );
}
