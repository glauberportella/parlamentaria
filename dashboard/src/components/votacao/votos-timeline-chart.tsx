"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import type { VotosTimeline } from "@/types/api";

interface Props {
  data: VotosTimeline[];
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const parts = iso.split("-");
  if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
  return iso;
}

export function VotosTimelineChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhum dado de votação no período.
      </p>
    );
  }

  const chartData = data.map((d) => ({
    data: formatDate(d.data),
    SIM: d.sim,
    NÃO: d.nao,
    Abstenção: d.abstencao,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <AreaChart data={chartData} margin={{ left: 0, right: 10, top: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="data" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value: number, name: string) => [
            value.toLocaleString("pt-BR"),
            name,
          ]}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="SIM"
          stackId="1"
          fill="hsl(var(--chart-1))"
          stroke="hsl(var(--chart-1))"
          fillOpacity={0.6}
        />
        <Area
          type="monotone"
          dataKey="NÃO"
          stackId="1"
          fill="hsl(var(--chart-2))"
          stroke="hsl(var(--chart-2))"
          fillOpacity={0.6}
        />
        <Area
          type="monotone"
          dataKey="Abstenção"
          stackId="1"
          fill="hsl(var(--chart-3))"
          stroke="hsl(var(--chart-3))"
          fillOpacity={0.6}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
