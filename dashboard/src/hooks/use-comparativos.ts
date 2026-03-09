/** React Query hooks for comparativos data. */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  ComparativoListItem,
  ComparativosFilters,
  EvolucaoAlinhamentoItem,
  PaginatedResponse,
} from "@/types/api";

export function useComparativos(filters: ComparativosFilters = {}) {
  const params = new URLSearchParams();
  if (filters.alinhamento_min !== undefined)
    params.set("alinhamento_min", String(filters.alinhamento_min));
  if (filters.alinhamento_max !== undefined)
    params.set("alinhamento_max", String(filters.alinhamento_max));
  if (filters.resultado) params.set("resultado", filters.resultado);
  if (filters.tema) params.set("tema", filters.tema);
  if (filters.ordenar) params.set("ordenar", filters.ordenar);
  if (filters.pagina) params.set("pagina", String(filters.pagina));
  if (filters.itens) params.set("itens", String(filters.itens));

  const qs = params.toString();
  const path = `/parlamentar/comparativos${qs ? `?${qs}` : ""}`;

  return useQuery<PaginatedResponse<ComparativoListItem>>({
    queryKey: ["comparativos", filters],
    queryFn: () => api.get<PaginatedResponse<ComparativoListItem>>(path),
    refetchInterval: 120_000,
  });
}

export function useEvolucaoAlinhamento(meses: number = 12) {
  return useQuery<EvolucaoAlinhamentoItem[]>({
    queryKey: ["comparativos", "evolucao", meses],
    queryFn: () =>
      api.get<EvolucaoAlinhamentoItem[]>(
        `/parlamentar/comparativos/evolucao?meses=${meses}`,
      ),
    refetchInterval: 120_000,
  });
}
