"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ComparativoListItem } from "@/types/api";
import { AlinhamentoBadge, ResultadoBadge } from "./comparativo-badges";

interface Props {
  data: ComparativoListItem[];
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

export function ComparativosTable({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhum comparativo encontrado.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Proposição</TableHead>
          <TableHead className="hidden md:table-cell">Data</TableHead>
          <TableHead className="text-center">Resultado</TableHead>
          <TableHead className="text-center">Voto Pop.</TableHead>
          <TableHead className="text-center">Voto Câmara</TableHead>
          <TableHead className="text-center">Alinhamento</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item) => {
          const totalPop =
            item.voto_popular_sim +
            item.voto_popular_nao +
            item.voto_popular_abstencao;
          const pctSim =
            totalPop > 0
              ? Math.round((item.voto_popular_sim / totalPop) * 100)
              : 0;
          const totalCamara = item.votos_camara_sim + item.votos_camara_nao;
          const pctCamaraSim =
            totalCamara > 0
              ? Math.round((item.votos_camara_sim / totalCamara) * 100)
              : 0;

          return (
            <TableRow key={item.id}>
              <TableCell>
                <div className="font-medium">
                  {item.tipo} {item.numero}/{item.ano}
                </div>
                <div className="text-sm text-muted-foreground line-clamp-1">
                  {item.ementa}
                </div>
              </TableCell>
              <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                {formatDate(item.data_geracao)}
              </TableCell>
              <TableCell className="text-center">
                <ResultadoBadge resultado={item.resultado_camara} />
              </TableCell>
              <TableCell className="text-center text-sm">
                <span className="font-semibold">{pctSim}%</span> SIM
                <br />
                <span className="text-xs text-muted-foreground">
                  ({totalPop.toLocaleString("pt-BR")} votos)
                </span>
              </TableCell>
              <TableCell className="text-center text-sm">
                <span className="font-semibold">{pctCamaraSim}%</span> SIM
                <br />
                <span className="text-xs text-muted-foreground">
                  ({totalCamara.toLocaleString("pt-BR")} votos)
                </span>
              </TableCell>
              <TableCell className="text-center">
                <AlinhamentoBadge alinhamento={item.alinhamento} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
