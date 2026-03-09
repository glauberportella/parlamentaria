"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import type { VotosPorUF } from "@/types/api";

interface Props {
  data: VotosPorUF[];
}

export function VotosPorUFChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhum dado de votação por estado disponível.
      </p>
    );
  }

  const chartData = data
    .sort((a, b) => b.total_votos - a.total_votos)
    .map((d) => ({
      uf: d.uf,
      SIM: d.sim,
      NÃO: d.nao,
      Abstenção: d.abstencao,
    }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(350, chartData.length * 28)}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 5, right: 10 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" />
        <YAxis
          type="category"
          dataKey="uf"
          width={40}
          tick={{ fontSize: 12 }}
        />
        <Tooltip
          formatter={(value: number, name: string) => [
            value.toLocaleString("pt-BR"),
            name,
          ]}
        />
        <Legend />
        <Bar dataKey="SIM" stackId="a" fill="hsl(var(--chart-1))" />
        <Bar dataKey="NÃO" stackId="a" fill="hsl(var(--chart-2))" />
        <Bar dataKey="Abstenção" stackId="a" fill="hsl(var(--chart-3))" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
