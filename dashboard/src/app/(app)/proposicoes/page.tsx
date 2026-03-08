"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText, Search, Brain, Scale, ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useProposicoes } from "@/hooks/use-proposicoes";
import type { ProposicoesFilters } from "@/types/api";

const TIPOS = ["PL", "PEC", "MPV", "PLP"] as const;
const ORDENACOES = [
  { value: "recentes", label: "Mais recentes" },
  { value: "votos_desc", label: "Mais votadas" },
  { value: "votos_asc", label: "Menos votadas" },
  { value: "ano_desc", label: "Por ano" },
] as const;

const ITEMS_PER_PAGE = 20;

function ProposicoesListSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-28" />
        ))}
      </div>
      <Skeleton className="h-[500px]" />
    </div>
  );
}

function VoteBar({ sim, nao }: { sim: number; nao: number }) {
  if (sim === 0 && nao === 0) {
    return <span className="text-xs text-muted-foreground">Sem votos</span>;
  }
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex h-2 w-16 overflow-hidden rounded-full bg-muted">
        <div className="bg-green-500" style={{ width: `${sim}%` }} />
        <div className="bg-red-500" style={{ width: `${nao}%` }} />
      </div>
      <span className="text-xs tabular-nums text-green-600">{sim.toFixed(0)}%</span>
      <span className="text-xs text-muted-foreground">/</span>
      <span className="text-xs tabular-nums text-red-600">{nao.toFixed(0)}%</span>
    </div>
  );
}

export default function ProposicoesPage() {
  const [filters, setFilters] = useState<ProposicoesFilters>({
    ordenar: "recentes",
    pagina: 1,
    itens: ITEMS_PER_PAGE,
  });
  const [searchInput, setSearchInput] = useState("");

  const { data, isLoading, error } = useProposicoes(filters);

  const handleSearch = () => {
    setFilters((f) => ({ ...f, busca: searchInput || undefined, pagina: 1 }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const setFilter = (key: keyof ProposicoesFilters, value: string | number | undefined) => {
    setFilters((f) => ({ ...f, [key]: value, pagina: 1 }));
  };

  const totalPages = data ? Math.ceil(data.total / (filters.itens ?? ITEMS_PER_PAGE)) : 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Proposições</h1>
          <p className="text-muted-foreground">
            Proposições legislativas com votação popular e análise IA.
          </p>
        </div>
        <ProposicoesListSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-lg text-muted-foreground">
          Não foi possível carregar as proposições.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Proposições</h1>
        <p className="text-muted-foreground">
          Proposições legislativas com votação popular e análise IA.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-1 items-center gap-2 sm:min-w-[280px] sm:max-w-sm">
          <Input
            placeholder="Buscar na ementa..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <Button variant="outline" size="icon" onClick={handleSearch}>
            <Search className="h-4 w-4" />
          </Button>
        </div>

        {/* Tipo filter buttons */}
        <div className="flex gap-1">
          <Button
            variant={!filters.tipo ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("tipo", undefined)}
          >
            Todos
          </Button>
          {TIPOS.map((t) => (
            <Button
              key={t}
              variant={filters.tipo === t ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter("tipo", filters.tipo === t ? undefined : t)}
            >
              {t}
            </Button>
          ))}
        </div>

        {/* Ordering */}
        <div className="flex gap-1">
          {ORDENACOES.map((ord) => (
            <Button
              key={ord.value}
              variant={filters.ordenar === ord.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setFilter("ordenar", ord.value)}
            >
              {ord.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Results */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {data?.total ?? 0} proposições encontradas
          </CardTitle>
          {filters.busca && (
            <CardDescription>
              Resultados para &quot;{filters.busca}&quot;
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {data && data.items.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px]">Proposição</TableHead>
                  <TableHead>Ementa</TableHead>
                  <TableHead className="w-[100px]">Situação</TableHead>
                  <TableHead className="w-[160px]">Votos Populares</TableHead>
                  <TableHead className="w-[80px] text-center">IA</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <Link
                        href={`/proposicoes/${p.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {p.tipo} {p.numero}/{p.ano}
                      </Link>
                      {p.temas?.slice(0, 2).map((tema) => (
                        <Badge key={tema} variant="outline" className="ml-1 text-[10px]">
                          {tema}
                        </Badge>
                      ))}
                    </TableCell>
                    <TableCell className="max-w-[400px]">
                      <p className="line-clamp-2 text-sm text-muted-foreground">
                        {p.ementa}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-[10px]">
                        {p.situacao ?? "—"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-0.5">
                        <span className="text-sm font-medium">{p.votos.total} votos</span>
                        <VoteBar sim={p.votos.percentual_sim} nao={p.votos.percentual_nao} />
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex justify-center gap-1">
                        {p.tem_analise && (
                          <span title="Análise IA disponível">
                            <Brain className="h-4 w-4 text-blue-500" />
                          </span>
                        )}
                        {p.tem_comparativo && (
                          <span title="Comparativo disponível">
                            <Scale className="h-4 w-4 text-amber-500" />
                          </span>
                        )}
                        {!p.tem_analise && !p.tem_comparativo && (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Nenhuma proposição encontrada
                {filters.busca ? ` para "${filters.busca}"` : ""}.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Página {filters.pagina ?? 1} de {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={(filters.pagina ?? 1) <= 1}
              onClick={() => setFilters((f) => ({ ...f, pagina: (f.pagina ?? 1) - 1 }))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={(filters.pagina ?? 1) >= totalPages}
              onClick={() => setFilters((f) => ({ ...f, pagina: (f.pagina ?? 1) + 1 }))}
            >
              Próxima <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
