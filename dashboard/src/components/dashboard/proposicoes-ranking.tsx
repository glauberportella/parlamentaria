"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProposicaoRanking } from "@/types/api";

interface Props {
  proposicoes: ProposicaoRanking[];
}

export function ProposicoesRanking({ proposicoes }: Props) {
  if (!proposicoes.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Proposições Mais Votadas</CardTitle>
          <CardDescription>Nenhuma votação popular registrada ainda.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Proposições Mais Votadas</CardTitle>
        <CardDescription>
          Rankings baseados no total de votos populares
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {proposicoes.map((p) => (
            <div
              key={p.proposicao_id}
              className="flex items-center justify-between gap-4"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">
                  {p.tipo} {p.numero}/{p.ano}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {p.ementa}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="whitespace-nowrap">
                  {p.total_votos} votos
                </Badge>
                <div className="w-20 text-right">
                  <span className="text-sm font-medium text-green-600">
                    {p.percentual_sim.toFixed(0)}%
                  </span>
                  <span className="text-muted-foreground"> / </span>
                  <span className="text-sm font-medium text-red-600">
                    {p.percentual_nao.toFixed(0)}%
                  </span>
                </div>
                {p.alinhamento !== null && (
                  <div className="w-8">
                    <div className="h-2 w-full rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-primary"
                        style={{ width: `${p.alinhamento * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
