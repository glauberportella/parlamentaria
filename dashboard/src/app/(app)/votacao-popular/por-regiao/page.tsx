"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useVotosPorUF } from "@/hooks/use-votos";
import { VotosPorUFChart } from "@/components/votacao/votos-por-uf-chart";

export default function VotosPorRegiaoPage() {
  const { data, isLoading } = useVotosPorUF();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Votos por Estado
        </h1>
        <p className="text-muted-foreground">
          Distribuição geográfica dos votos populares por Unidade Federativa.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Votos por UF</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[400px]" />
          ) : (
            <VotosPorUFChart data={data ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
