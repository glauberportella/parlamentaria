"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TemaAtivo } from "@/types/api";

interface Props {
  temas: TemaAtivo[];
}

export function TemasChart({ temas }: Props) {
  const data = temas.slice(0, 8).map((t) => ({
    name: t.tema.length > 15 ? t.tema.slice(0, 15) + "…" : t.tema,
    votos: t.total_votos,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Votos por Tema (últimos 30 dias)</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sem dados de votação por tema.</p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data} layout="vertical" margin={{ left: 10, right: 10 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={{ fontSize: 12 }}
              />
              <Tooltip
                formatter={(value: number) => [
                  `${value.toLocaleString("pt-BR")} votos`,
                  "Total",
                ]}
              />
              <Bar dataKey="votos" fill="hsl(var(--chart-1))" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
