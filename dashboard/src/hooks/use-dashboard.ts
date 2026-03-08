/** React Query hooks for dashboard data. */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { DashboardResumo } from "@/types/api";

export function useDashboard() {
  return useQuery<DashboardResumo>({
    queryKey: ["dashboard", "resumo"],
    queryFn: () => api.get<DashboardResumo>("/parlamentar/dashboard/resumo"),
    refetchInterval: 60_000, // Poll every minute
  });
}
