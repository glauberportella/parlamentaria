/** React Query hooks for votos analíticos data. */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { VotosPorTema, VotosPorUF, VotosTimeline } from "@/types/api";

/** Rankings use this type matching the backend VotosRankingItem */
export interface VotosRankingItem {
  proposicao_id: number;
  tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  total_votos: number;
  sim: number;
  nao: number;
  abstencao: number;
  percentual_sim: number;
  percentual_nao: number;
}

export function useVotosPorTema() {
  return useQuery<VotosPorTema[]>({
    queryKey: ["votos", "por-tema"],
    queryFn: () => api.get<VotosPorTema[]>("/parlamentar/votos/por-tema"),
    refetchInterval: 120_000,
  });
}

export function useVotosPorUF() {
  return useQuery<VotosPorUF[]>({
    queryKey: ["votos", "por-uf"],
    queryFn: () => api.get<VotosPorUF[]>("/parlamentar/votos/por-uf"),
    refetchInterval: 120_000,
  });
}

export function useVotosTimeline(dias: number = 30) {
  return useQuery<VotosTimeline[]>({
    queryKey: ["votos", "timeline", dias],
    queryFn: () =>
      api.get<VotosTimeline[]>(`/parlamentar/votos/timeline?dias=${dias}`),
    refetchInterval: 120_000,
  });
}

export function useVotosRanking(limite: number = 10) {
  return useQuery<VotosRankingItem[]>({
    queryKey: ["votos", "ranking", limite],
    queryFn: () =>
      api.get<VotosRankingItem[]>(
        `/parlamentar/votos/ranking?limite=${limite}`,
      ),
    refetchInterval: 120_000,
  });
}
