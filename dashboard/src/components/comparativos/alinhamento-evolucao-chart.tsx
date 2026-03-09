"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import type { EvolucaoAlinhamentoItem } from "@/types/api";

interface Props {
  data: EvolucaoAlinhamentoItem[];
}

function formatMonth(mes: string): string {
  if (!mes) return "";
  const [y, m] = mes.split("-");
  const months = [
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
  ];
  return `${months[parseInt(m, 10) - 1]}/${y?.slice(2)}`;
}

export function AlinhamentoEvolucaoChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhum dado de evolução disponível.
      </p>
    );
  }

  const chartData = data.map((d) => ({
    mes: formatMonth(d.mes),
    alinhamento: Math.round(d.alinhamento_medio * 100),
    comparativos: d.total_comparativos,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <AreaChart data={chartData} margin={{ left: 0, right: 10, top: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12 }}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === "alinhamento") return [`${value}%`, "Alinhamento"];
            return [value, name];
          }}
          labelFormatter={(label: string) => `Mês: ${label}`}
        />
        <ReferenceLine
          y={50}
          stroke="hsl(var(--muted-foreground))"
          strokeDasharray="3 3"
          label={{ value: "50%", position: "right", fontSize: 10 }}
        />
        <Area
          type="monotone"
          dataKey="alinhamento"
          fill="hsl(var(--chart-1))"
          stroke="hsl(var(--chart-1))"
          fillOpacity={0.3}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
