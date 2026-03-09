/** React Query hooks for user profile management. */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { ParlamentarUser, ParlamentarUserUpdate } from "@/types/api";

export function useProfile() {
  return useQuery<ParlamentarUser>({
    queryKey: ["profile"],
    queryFn: () => api.get<ParlamentarUser>("/parlamentar/auth/me"),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ParlamentarUserUpdate) =>
      api.put<ParlamentarUser>("/parlamentar/auth/me", data),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(["profile"], updatedUser);
    },
  });
}
