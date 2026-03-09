"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useVotosPorTema } from "@/hooks/use-votos";
import { VotosPorTemaChart } from "@/components/votacao/votos-por-tema-chart";

export default function VotosPorTemaPage() {
  const { data, isLoading } = useVotosPorTema();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Votos por Tema
        </h1>
        <p className="text-muted-foreground">
          Distribuição dos votos populares agrupados por área temática legislativa.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Votos por Tema</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[400px]" />
          ) : (
            <VotosPorTemaChart data={data ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
