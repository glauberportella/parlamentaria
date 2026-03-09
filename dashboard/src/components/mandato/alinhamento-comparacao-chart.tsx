"use client";

import {
  Line,
  LineChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  ReferenceLine,
} from "recharts";
import type { AlinhamentoComparacao } from "@/types/api";

interface Props {
  data: AlinhamentoComparacao;
}

function formatMonth(mes: string): string {
  if (!mes) return "";
  const [y, m] = mes.split("-");
  const months = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
  ];
  return `${months[parseInt(m, 10) - 1]}/${y?.slice(2)}`;
}

export function AlinhamentoComparacaoChart({ data }: Props) {
  // Merge all three series into one unified data array keyed by month
  const monthMap = new Map<
    string,
    { mes: string; pessoal: number | null; partido: number | null; uf: number | null }
  >();

  for (const item of data.pessoal) {
    if (!monthMap.has(item.mes)) {
      monthMap.set(item.mes, { mes: item.mes, pessoal: null, partido: null, uf: null });
    }
    monthMap.get(item.mes)!.pessoal = Math.round(item.alinhamento * 100);
  }
  for (const item of data.partido) {
    if (!monthMap.has(item.mes)) {
      monthMap.set(item.mes, { mes: item.mes, pessoal: null, partido: null, uf: null });
    }
    monthMap.get(item.mes)!.partido = Math.round(item.alinhamento * 100);
  }
  for (const item of data.uf) {
    if (!monthMap.has(item.mes)) {
      monthMap.set(item.mes, { mes: item.mes, pessoal: null, partido: null, uf: null });
    }
    monthMap.get(item.mes)!.uf = Math.round(item.alinhamento * 100);
  }

  const chartData = Array.from(monthMap.values())
    .sort((a, b) => a.mes.localeCompare(b.mes))
    .map((d) => ({ ...d, mesLabel: formatMonth(d.mes) }));

  if (chartData.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhum dado de alinhamento disponível.
      </p>
    );
  }

  const partidoLabel = data.sigla_partido ?? "Partido";
  const ufLabel = data.sigla_uf ?? "UF";

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="mesLabel" className="text-xs" />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          className="text-xs"
        />
        <Tooltip
          formatter={(v: number, name: string) => [`${v}%`, name]}
          labelFormatter={(label: string) => label}
        />
        <Legend />
        <ReferenceLine
          y={50}
          strokeDasharray="4 4"
          stroke="hsl(var(--muted-foreground))"
          strokeOpacity={0.5}
        />
        <Line
          type="monotone"
          dataKey="pessoal"
          name="Pessoal"
          stroke="hsl(var(--chart-1))"
          strokeWidth={2}
          dot={{ r: 3 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="partido"
          name={partidoLabel}
          stroke="hsl(var(--chart-2))"
          strokeWidth={2}
          dot={{ r: 3 }}
          strokeDasharray="5 5"
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="uf"
          name={ufLabel}
          stroke="hsl(var(--chart-3))"
          strokeWidth={2}
          dot={{ r: 3 }}
          strokeDasharray="2 4"
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
