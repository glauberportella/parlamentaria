"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMandatoAlinhamento } from "@/hooks/use-mandato";
import { AlinhamentoComparacaoChart } from "@/components/mandato/alinhamento-comparacao-chart";

export default function MeuMandatoAlinhamentoPage() {
  const { data: alinhamento, isLoading } = useMandatoAlinhamento(12);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Alinhamento com Voto Popular
        </h1>
        <p className="text-muted-foreground">
          Evolução do seu alinhamento pessoal comparado ao partido e UF.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Evolução do Alinhamento (últimos 12 meses)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[400px]" />
          ) : alinhamento ? (
            <>
              <div className="mb-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
                <span>
                  Pessoal:{" "}
                  <strong className="text-foreground">
                    {Math.round(alinhamento.alinhamento_medio_pessoal * 100)}%
                  </strong>
                </span>
                {alinhamento.sigla_partido && (
                  <span>
                    {alinhamento.sigla_partido}:{" "}
                    <strong className="text-foreground">
                      {Math.round(alinhamento.alinhamento_medio_partido * 100)}%
                    </strong>
                  </span>
                )}
                {alinhamento.sigla_uf && (
                  <span>
                    {alinhamento.sigla_uf}:{" "}
                    <strong className="text-foreground">
                      {Math.round(alinhamento.alinhamento_medio_uf * 100)}%
                    </strong>
                  </span>
                )}
              </div>
              <AlinhamentoComparacaoChart data={alinhamento} />
            </>
          ) : (
            <p className="py-10 text-center text-sm text-muted-foreground">
              Nenhum dado de alinhamento disponível.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
