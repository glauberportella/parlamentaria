"use client";

import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { VotosRankingItem } from "@/hooks/use-votos";

interface Props {
  data: VotosRankingItem[];
}

function VoteBar({
  sim,
  nao,
  abstencao,
}: {
  sim: number;
  nao: number;
  abstencao: number;
}) {
  const total = sim + nao + abstencao;
  if (total === 0) return <span className="text-xs text-muted-foreground">—</span>;

  const pSim = (sim / total) * 100;
  const pNao = (nao / total) * 100;

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-muted flex">
        <div
          className="h-full bg-[hsl(var(--chart-1))]"
          style={{ width: `${pSim}%` }}
        />
        <div
          className="h-full bg-[hsl(var(--chart-2))]"
          style={{ width: `${pNao}%` }}
        />
        <div className="h-full bg-[hsl(var(--chart-3))] flex-1" />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">
        {total.toLocaleString("pt-BR")}
      </span>
    </div>
  );
}

export function VotosRankingTable({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        Nenhuma proposição com votos populares.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10">#</TableHead>
          <TableHead>Proposição</TableHead>
          <TableHead className="hidden md:table-cell">Ementa</TableHead>
          <TableHead>Votos</TableHead>
          <TableHead className="text-right">SIM %</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item, idx) => (
          <TableRow key={item.proposicao_id}>
            <TableCell className="font-medium text-muted-foreground">
              {idx + 1}
            </TableCell>
            <TableCell>
              <Link
                href={`/proposicoes/${item.proposicao_id}`}
                className="font-medium text-primary hover:underline"
              >
                {item.tipo} {item.numero}/{item.ano}
              </Link>
            </TableCell>
            <TableCell className="hidden md:table-cell text-sm text-muted-foreground max-w-[300px] truncate">
              {item.ementa}
            </TableCell>
            <TableCell>
              <VoteBar
                sim={item.sim}
                nao={item.nao}
                abstencao={item.abstencao}
              />
            </TableCell>
            <TableCell className="text-right">
              <Badge variant="outline">{item.percentual_sim.toFixed(0)}%</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
