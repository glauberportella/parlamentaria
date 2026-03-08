/** React Query hooks for proposições data. */

"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  PaginatedResponse,
  ProposicaoListItem,
  ProposicaoDetalhe,
  ProposicoesFilters,
} from "@/types/api";

function buildQueryString(filters: ProposicoesFilters): string {
  const params = new URLSearchParams();
  if (filters.tema) params.set("tema", filters.tema);
  if (filters.tipo) params.set("tipo", filters.tipo);
  if (filters.ano) params.set("ano", String(filters.ano));
  if (filters.situacao) params.set("situacao", filters.situacao);
  if (filters.busca) params.set("busca", filters.busca);
  if (filters.ordenar) params.set("ordenar", filters.ordenar);
  if (filters.pagina) params.set("pagina", String(filters.pagina));
  if (filters.itens) params.set("itens", String(filters.itens));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function useProposicoes(filters: ProposicoesFilters = {}) {
  return useQuery<PaginatedResponse<ProposicaoListItem>>({
    queryKey: ["proposicoes", filters],
    queryFn: () =>
      api.get<PaginatedResponse<ProposicaoListItem>>(
        `/parlamentar/proposicoes${buildQueryString(filters)}`,
      ),
    placeholderData: keepPreviousData,
    refetchInterval: 120_000, // Poll every 2 minutes
  });
}

export function useProposicao(id: number | null) {
  return useQuery<ProposicaoDetalhe>({
    queryKey: ["proposicao", id],
    queryFn: () => api.get<ProposicaoDetalhe>(`/parlamentar/proposicoes/${id}`),
    enabled: id !== null,
  });
}
