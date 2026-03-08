"use client";

import {
  FileText,
  Users,
  Vote,
  Scale,
} from "lucide-react";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { ProposicoesRanking } from "@/components/dashboard/proposicoes-ranking";
import { AlertasPanel } from "@/components/dashboard/alertas-panel";
import { TemasChart } from "@/components/dashboard/temas-chart";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "@/hooks/use-dashboard";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("pt-BR");
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[120px]" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-[320px]" />
        <Skeleton className="h-[320px]" />
      </div>
      <Skeleton className="h-[300px]" />
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) return <DashboardSkeleton />;

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-lg text-muted-foreground">
          Não foi possível carregar o dashboard.
        </p>
        <p className="text-sm text-muted-foreground">
          Verifique a conexão com o backend e tente novamente.
        </p>
      </div>
    );
  }

  const { kpis, tendencias, alertas } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Visão geral da participação popular nas proposições legislativas.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Proposições Ativas"
          value={formatNumber(kpis.total_proposicoes_ativas)}
          icon={<FileText className="h-4 w-4" />}
        />
        <KpiCard
          title="Eleitores Cadastrados"
          value={formatNumber(kpis.total_eleitores_cadastrados)}
          description={`+${tendencias.novos_eleitores_ultimos_7_dias} últimos 7 dias`}
          icon={<Users className="h-4 w-4" />}
        />
        <KpiCard
          title="Votos Populares"
          value={formatNumber(kpis.total_votos_populares)}
          description={`+${formatNumber(tendencias.votos_ultimos_7_dias)} últimos 7 dias`}
          icon={<Vote className="h-4 w-4" />}
        />
        <KpiCard
          title="Alinhamento Médio"
          value={`${(kpis.alinhamento_medio * 100).toFixed(0)}%`}
          description={`${kpis.total_comparativos} comparativos`}
          icon={<Scale className="h-4 w-4" />}
        />
      </div>

      {/* Charts + Alerts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <TemasChart temas={tendencias.temas_mais_ativos} />
        <AlertasPanel alertas={alertas} />
      </div>

      {/* Ranking */}
      <ProposicoesRanking proposicoes={tendencias.proposicoes_mais_votadas} />
    </div>
  );
}
