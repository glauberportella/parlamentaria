"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvolucaoAlinhamento } from "@/hooks/use-comparativos";
import { AlinhamentoEvolucaoChart } from "@/components/comparativos/alinhamento-evolucao-chart";

export default function ComparativosEvolucaoPage() {
  const { data, isLoading } = useEvolucaoAlinhamento(12);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Evolução do Alinhamento
        </h1>
        <p className="text-muted-foreground">
          Série temporal do índice médio de alinhamento entre voto popular e votação na Câmara.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Alinhamento Médio (últimos 12 meses)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[400px]" />
          ) : (
            <AlinhamentoEvolucaoChart data={data ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
