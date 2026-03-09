"use client";

import {
  GitCompareArrows,
  TrendingUp,
  Vote,
  FileText,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useMandatoResumo, useMandatoAlinhamento } from "@/hooks/use-mandato";
import { AlinhamentoComparacaoChart } from "@/components/mandato/alinhamento-comparacao-chart";

/* ── Skeleton ─────────────────────────────────── */
function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-24" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[100px]" />
        ))}
      </div>
      <Skeleton className="h-[400px]" />
    </div>
  );
}

/* ── KPI card ─────────────────────────────────── */
function KpiMini({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-xl font-bold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Page ──────────────────────────────────────── */
export default function MeuMandatoPage() {
  const { data: resumo, isLoading: loadingResumo } = useMandatoResumo();
  const { data: alinhamento, isLoading: loadingAlinh } = useMandatoAlinhamento(12);

  if (loadingResumo && loadingAlinh) return <PageSkeleton />;

  const r = resumo ?? {
    deputado: null,
    total_comparativos: 0,
    alinhamento_medio: 0,
    total_votos_populares_recebidos: 0,
    proposicoes_acompanhadas: 0,
    comparativos_alinhados: 0,
    comparativos_divergentes: 0,
    temas_acompanhados: [],
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Meu Mandato</h1>
        <p className="text-muted-foreground">
          Dados do seu mandato e alinhamento com o voto popular.
        </p>
      </div>

      {/* Deputy card */}
      {r.deputado && (
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            {r.deputado.foto_url ? (
              <img
                src={r.deputado.foto_url}
                alt={r.deputado.nome}
                className="h-16 w-16 rounded-full object-cover border"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted text-lg font-bold">
                {r.deputado.nome?.[0] ?? "?"}
              </div>
            )}
            <div>
              <p className="text-lg font-semibold">{r.deputado.nome}</p>
              <p className="text-sm text-muted-foreground">
                {[r.deputado.sigla_partido, r.deputado.sigla_uf]
                  .filter(Boolean)
                  .join(" — ")}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiMini
          title="Alinhamento Médio"
          value={`${Math.round(r.alinhamento_medio * 100)}%`}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <KpiMini
          title="Comparativos"
          value={r.total_comparativos.toLocaleString("pt-BR")}
          icon={<GitCompareArrows className="h-5 w-5" />}
        />
        <KpiMini
          title="Votos Populares"
          value={r.total_votos_populares_recebidos.toLocaleString("pt-BR")}
          icon={<Vote className="h-5 w-5" />}
        />
        <KpiMini
          title="Proposições"
          value={r.proposicoes_acompanhadas.toLocaleString("pt-BR")}
          icon={<FileText className="h-5 w-5" />}
        />
      </div>

      {/* Aligned vs Divergent */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Alinhados</p>
              <p className="text-xl font-bold">{r.comparativos_alinhados}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              <XCircle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Divergentes</p>
              <p className="text-xl font-bold">{r.comparativos_divergentes}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Topics */}
      {r.temas_acompanhados && r.temas_acompanhados.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Temas Acompanhados</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {r.temas_acompanhados.map((tema) => (
              <Badge key={tema} variant="secondary">
                {tema}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Alignment comparison chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Evolução do Alinhamento (últimos 12 meses)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingAlinh ? (
            <Skeleton className="h-[350px]" />
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
            <p className="text-sm text-muted-foreground py-10 text-center">
              Nenhum dado de alinhamento disponível.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
