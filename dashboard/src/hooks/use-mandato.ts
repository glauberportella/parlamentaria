/** React Query hooks for Meu Mandato data. */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { MandatoResumo, AlinhamentoComparacao } from "@/types/api";

export function useMandatoResumo() {
  return useQuery<MandatoResumo>({
    queryKey: ["mandato", "resumo"],
    queryFn: () => api.get<MandatoResumo>("/parlamentar/meu-mandato/resumo"),
    refetchInterval: 120_000,
  });
}

export function useMandatoAlinhamento(meses: number = 12) {
  return useQuery<AlinhamentoComparacao>({
    queryKey: ["mandato", "alinhamento", meses],
    queryFn: () =>
      api.get<AlinhamentoComparacao>(
        `/parlamentar/meu-mandato/alinhamento?meses=${meses}`,
      ),
    refetchInterval: 120_000,
  });
}
