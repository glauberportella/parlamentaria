"use client";

import { Bell, AlertTriangle, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardAlerta } from "@/types/api";

interface Props {
  alertas: DashboardAlerta[];
}

const urgenciaIcon = {
  alta: <AlertTriangle className="h-4 w-4 text-destructive" />,
  media: <Bell className="h-4 w-4 text-yellow-500" />,
  baixa: <Info className="h-4 w-4 text-muted-foreground" />,
};

export function AlertasPanel({ alertas }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Alertas</CardTitle>
      </CardHeader>
      <CardContent>
        {alertas.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum alerta no momento.</p>
        ) : (
          <div className="space-y-3">
            {alertas.map((alerta, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="mt-0.5">{urgenciaIcon[alerta.urgencia]}</div>
                <p className="text-sm">{alerta.mensagem}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
