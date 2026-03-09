"use client";

import { useState } from "react";
import {
  GitCompareArrows,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Download,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { useComparativos, useEvolucaoAlinhamento } from "@/hooks/use-comparativos";
import { AlinhamentoEvolucaoChart } from "@/components/comparativos/alinhamento-evolucao-chart";
import { ComparativosTable } from "@/components/comparativos/comparativos-table";
import { downloadCSV } from "@/lib/export";
import type { ComparativosFilters } from "@/types/api";

/* ── skeleton ──────────────────────────────────── */
function PageSkeleton() {
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

/* ── KPI card ──────────────────────────────────── */
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

/* ── Filters bar ───────────────────────────────── */
function Filters({
  filters,
  onChange,
}: {
  filters: ComparativosFilters;
  onChange: (f: ComparativosFilters) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        value={filters.resultado ?? ""}
        onChange={(e) =>
          onChange({
            ...filters,
            resultado: (e.target.value || undefined) as ComparativosFilters["resultado"],
            pagina: 1,
          })
        }
      >
        <option value="">Todos os resultados</option>
        <option value="APROVADO">Aprovado</option>
        <option value="REJEITADO">Rejeitado</option>
      </select>

      <select
        className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        value={filters.ordenar ?? "recentes"}
        onChange={(e) =>
          onChange({
            ...filters,
            ordenar: e.target.value as ComparativosFilters["ordenar"],
            pagina: 1,
          })
        }
      >
        <option value="recentes">Mais recentes</option>
        <option value="alinhamento_desc">Maior alinhamento</option>
        <option value="alinhamento_asc">Menor alinhamento</option>
      </select>

      <Input
        placeholder="Filtrar por tema…"
        className="h-9 w-44"
        value={filters.tema ?? ""}
        onChange={(e) =>
          onChange({ ...filters, tema: e.target.value || undefined, pagina: 1 })
        }
      />
    </div>
  );
}

/* ── Page ───────────────────────────────────────── */
export default function ComparativosPage() {
  const [filters, setFilters] = useState<ComparativosFilters>({
    ordenar: "recentes",
    itens: 20,
  });

  const { data: comparativos, isLoading: loadingList } = useComparativos(filters);
  const { data: evolucao, isLoading: loadingEvo } = useEvolucaoAlinhamento(12);

  if (loadingList && loadingEvo) return <PageSkeleton />;

  const items = comparativos?.items ?? [];
  const total = comparativos?.total ?? 0;
  const evoData = evolucao ?? [];

  // Compute KPIs
  const alinhMedio =
    items.length > 0
      ? items.reduce((s, c) => s + c.alinhamento, 0) / items.length
      : 0;
  const aprovados = items.filter((c) => c.resultado_camara === "APROVADO").length;
  const rejeitados = items.filter((c) => c.resultado_camara === "REJEITADO").length;

  // Pagination
  const pagina = filters.pagina ?? 1;
  const itens = filters.itens ?? 20;
  const totalPages = Math.max(1, Math.ceil(total / itens));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Comparativos</h1>
          <p className="text-muted-foreground">
            Comparações entre voto popular e votação real na Câmara.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const params = filters.resultado ? `?resultado=${filters.resultado}` : "";
            downloadCSV(
              `/parlamentar/exportar/comparativos${params}`,
              "comparativos.csv",
            );
          }}
        >
          <Download className="h-4 w-4 md:mr-2" />
          <span className="hidden md:inline">Exportar CSV</span>
        </Button>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiMini
          title="Total de Comparativos"
          value={total.toLocaleString("pt-BR")}
          icon={<GitCompareArrows className="h-5 w-5" />}
        />
        <KpiMini
          title="Alinhamento Médio"
          value={`${Math.round(alinhMedio * 100)}%`}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <KpiMini
          title="Aprovados"
          value={String(aprovados)}
          icon={<CheckCircle2 className="h-5 w-5" />}
        />
        <KpiMini
          title="Rejeitados"
          value={String(rejeitados)}
          icon={<XCircle className="h-5 w-5" />}
        />
      </div>

      {/* Tabbed content */}
      <Tabs defaultValue="lista" className="w-full">
        <TabsList>
          <TabsTrigger value="lista">Lista</TabsTrigger>
          <TabsTrigger value="evolucao">Evolução</TabsTrigger>
        </TabsList>

        <TabsContent value="lista" className="mt-4 space-y-4">
          <Filters filters={filters} onChange={setFilters} />

          <Card>
            <CardContent className="p-0">
              {loadingList ? (
                <div className="p-6">
                  <Skeleton className="h-[300px]" />
                </div>
              ) : (
                <ComparativosTable data={items} />
              )}
            </CardContent>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                disabled={pagina <= 1}
                onClick={() => setFilters({ ...filters, pagina: pagina - 1 })}
              >
                Anterior
              </button>
              <span className="text-sm text-muted-foreground">
                Página {pagina} de {totalPages}
              </span>
              <button
                className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                disabled={pagina >= totalPages}
                onClick={() => setFilters({ ...filters, pagina: pagina + 1 })}
              >
                Próxima
              </button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="evolucao" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Evolução do Alinhamento (últimos 12 meses)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingEvo ? (
                <Skeleton className="h-[350px]" />
              ) : (
                <AlinhamentoEvolucaoChart data={evoData} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
