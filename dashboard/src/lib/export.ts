/** CSV export download helper. */

import { API_BASE_URL } from "@/lib/api-client";

/**
 * Triggers a CSV file download from the backend export endpoints.
 * Fetches with auth token and creates a temporary link to download.
 */
export async function downloadCSV(path: string, filename: string) {
  // Get token from session
  const sessionRes = await fetch("/api/auth/session");
  const session = await sessionRes.json();
  const token = session?.accessToken;

  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    throw new Error("Falha ao exportar dados");
  }

  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}
