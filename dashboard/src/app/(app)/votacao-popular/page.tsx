"use client";

import { Vote, TrendingUp, Users, BarChart3, Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useVotosPorTema,
  useVotosPorUF,
  useVotosTimeline,
  useVotosRanking,
} from "@/hooks/use-votos";
import { VotosPorTemaChart } from "@/components/votacao/votos-por-tema-chart";
import { VotosPorUFChart } from "@/components/votacao/votos-por-uf-chart";
import { VotosTimelineChart } from "@/components/votacao/votos-timeline-chart";
import { VotosRankingTable } from "@/components/votacao/votos-ranking-table";
import { downloadCSV } from "@/lib/export";

function PanoramaSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[100px]" />
        ))}
      </div>
      <Skeleton className="h-[400px]" />
    </div>
  );
}

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

export default function VotacaoPopularPage() {
  const porTema = useVotosPorTema();
  const porUF = useVotosPorUF();
  const timeline = useVotosTimeline(30);
  const ranking = useVotosRanking(10);

  const isLoading =
    porTema.isLoading || porUF.isLoading || timeline.isLoading || ranking.isLoading;

  if (isLoading) return <PanoramaSkeleton />;

  const porTemaData = porTema.data ?? [];
  const porUFData = porUF.data ?? [];
  const timelineData = timeline.data ?? [];
  const rankingData = ranking.data ?? [];

  // Compute summary KPIs
  const totalVotos = porUFData.reduce((s, d) => s + d.total_votos, 0);
  const totalSim = porUFData.reduce((s, d) => s + d.sim, 0);
  const nUFs = porUFData.length;
  const nTemas = porTemaData.length;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Votação Popular
          </h1>
          <p className="text-muted-foreground">
            Panorama geral da participação popular nas votações legislativas.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => downloadCSV("/parlamentar/exportar/votos", "votos-populares.csv")}
        >
          <Download className="h-4 w-4 md:mr-2" />
          <span className="hidden md:inline">Exportar CSV</span>
        </Button>
      </div>

      {/* KPI mini cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiMini
          title="Total de Votos"
          value={totalVotos.toLocaleString("pt-BR")}
          icon={<Vote className="h-5 w-5" />}
        />
        <KpiMini
          title="Votos SIM"
          value={
            totalVotos > 0
              ? `${((totalSim / totalVotos) * 100).toFixed(0)}% (${totalSim.toLocaleString("pt-BR")})`
              : "0"
          }
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <KpiMini
          title="Estados Participantes"
          value={String(nUFs)}
          icon={<Users className="h-5 w-5" />}
        />
        <KpiMini
          title="Temas Votados"
          value={String(nTemas)}
          icon={<BarChart3 className="h-5 w-5" />}
        />
      </div>

      {/* Tabbed content */}
      <Tabs defaultValue="timeline" className="w-full">
        <TabsList>
          <TabsTrigger value="timeline">Evolução</TabsTrigger>
          <TabsTrigger value="temas">Por Tema</TabsTrigger>
          <TabsTrigger value="uf">Por Estado</TabsTrigger>
          <TabsTrigger value="ranking">Ranking</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Evolução de Votos (últimos 30 dias)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <VotosTimelineChart data={timelineData} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="temas" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Votos por Tema
              </CardTitle>
            </CardHeader>
            <CardContent>
              <VotosPorTemaChart data={porTemaData} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="uf" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Votos por Estado
              </CardTitle>
            </CardHeader>
            <CardContent>
              <VotosPorUFChart data={porUFData} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ranking" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Proposições Mais Votadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <VotosRankingTable data={rankingData} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
