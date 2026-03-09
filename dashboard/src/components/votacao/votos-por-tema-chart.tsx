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
import type { VotosPorTema } from "@/types/api";

interface Props {
  data: VotosPorTema[];
}

export function VotosPorTemaChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhum dado de votação por tema disponível.
      </p>
    );
  }

  const chartData = data.slice(0, 12).map((d) => ({
    tema: d.tema.length > 18 ? d.tema.slice(0, 18) + "…" : d.tema,
    SIM: d.sim,
    NÃO: d.nao,
    Abstenção: d.abstencao,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 10 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" />
        <YAxis
          type="category"
          dataKey="tema"
          width={140}
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
