"use client";

import { use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Brain,
  Calendar,
  CheckCircle2,
  ExternalLink,
  Scale,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useProposicao } from "@/hooks/use-proposicoes";

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-[200px]" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-[300px]" />
        <Skeleton className="h-[300px]" />
      </div>
    </div>
  );
}

function VoteChart({
  total,
  sim,
  nao,
  abstencao,
  percentual_sim,
  percentual_nao,
  percentual_abstencao,
}: {
  total: number;
  sim: number;
  nao: number;
  abstencao: number;
  percentual_sim: number;
  percentual_nao: number;
  percentual_abstencao: number;
}) {
  if (total === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        Nenhum voto popular registrado ainda.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-center">
        <span className="text-3xl font-bold">{total}</span>
        <span className="ml-1 text-sm text-muted-foreground">votos populares</span>
      </div>

      {/* Progress bar */}
      <div className="flex h-4 w-full overflow-hidden rounded-full">
        <div
          className="bg-green-500 transition-all"
          style={{ width: `${percentual_sim}%` }}
        />
        <div
          className="bg-red-500 transition-all"
          style={{ width: `${percentual_nao}%` }}
        />
        <div
          className="bg-zinc-400 transition-all"
          style={{ width: `${percentual_abstencao}%` }}
        />
      </div>

      {/* Breakdown */}
      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="flex items-center justify-center gap-1 text-green-600">
            <ThumbsUp className="h-4 w-4" />
            <span className="text-lg font-bold">{sim}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            SIM ({percentual_sim.toFixed(1)}%)
          </p>
        </div>
        <div>
          <div className="flex items-center justify-center gap-1 text-red-600">
            <ThumbsDown className="h-4 w-4" />
            <span className="text-lg font-bold">{nao}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            NÃO ({percentual_nao.toFixed(1)}%)
          </p>
        </div>
        <div>
          <div className="flex items-center justify-center gap-1 text-zinc-500">
            <span className="text-lg font-bold">{abstencao}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Abstenção ({percentual_abstencao.toFixed(1)}%)
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ProposicaoDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const proposicaoId = Number(resolvedParams.id);
  const { data, isLoading, error } = useProposicao(
    isNaN(proposicaoId) ? null : proposicaoId,
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" render={<Link href="/proposicoes" />}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Voltar
        </Button>
        <DetailSkeleton />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" render={<Link href="/proposicoes" />}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Voltar
        </Button>
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <p className="text-lg text-muted-foreground">
            Proposição não encontrada.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Button variant="ghost" size="sm" render={<Link href="/proposicoes" />}>
        <ArrowLeft className="mr-1 h-4 w-4" /> Voltar às proposições
      </Button>

      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">
            {data.tipo} {data.numero}/{data.ano}
          </h1>
          {data.situacao && (
            <Badge variant="secondary">{data.situacao}</Badge>
          )}
          {data.analise && (
            <Badge variant="outline" className="gap-1">
              <Brain className="h-3 w-3" /> Análise IA
            </Badge>
          )}
          {data.comparativo && (
            <Badge variant="outline" className="gap-1">
              <Scale className="h-3 w-3" /> Comparativo
            </Badge>
          )}
        </div>
        {data.temas && data.temas.length > 0 && (
          <div className="mt-2 flex gap-1">
            {data.temas.map((tema) => (
              <Badge key={tema} variant="outline">
                {tema}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Main info card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ementa</CardTitle>
          {data.data_apresentacao && (
            <CardDescription className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              Apresentada em{" "}
              {new Date(data.data_apresentacao).toLocaleDateString("pt-BR")}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-relaxed">{data.ementa}</p>
          {data.texto_completo_url && (
            <Button
              variant="outline"
              size="sm"
              render={<a href={data.texto_completo_url} target="_blank" rel="noopener noreferrer" />}
            >
              <ExternalLink className="mr-1 h-4 w-4" /> Texto completo
            </Button>
          )}
          {data.autores && data.autores.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Autores</p>
              <div className="flex flex-wrap gap-1">
                {data.autores.map((autor, i) => (
                  <Badge key={i} variant="outline" className="text-[10px]">
                    {String(autor.nome ?? autor.uri ?? `Autor ${i + 1}`)}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Vote + Comparativo grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Votos populares */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Votação Popular</CardTitle>
            <CardDescription>
              Resultado consolidado dos votos do eleitorado
            </CardDescription>
          </CardHeader>
          <CardContent>
            <VoteChart {...data.votos} />
          </CardContent>
        </Card>

        {/* Comparativo pop vs real */}
        {data.comparativo ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Scale className="h-4 w-4" /> Comparativo Pop. vs Real
              </CardTitle>
              <CardDescription>
                Alinhamento entre voto popular e votação parlamentar
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Resultado Câmara</span>
                <Badge
                  variant={
                    data.comparativo.resultado_camara === "APROVADO"
                      ? "default"
                      : "destructive"
                  }
                  className="gap-1"
                >
                  {data.comparativo.resultado_camara === "APROVADO" ? (
                    <CheckCircle2 className="h-3 w-3" />
                  ) : (
                    <XCircle className="h-3 w-3" />
                  )}
                  {data.comparativo.resultado_camara}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <span className="text-lg font-bold text-green-600">
                    {data.comparativo.votos_camara_sim}
                  </span>
                  <p className="text-xs text-muted-foreground">Votos SIM</p>
                </div>
                <div>
                  <span className="text-lg font-bold text-red-600">
                    {data.comparativo.votos_camara_nao}
                  </span>
                  <p className="text-xs text-muted-foreground">Votos NÃO</p>
                </div>
              </div>

              <Separator />

              <div className="text-center">
                <p className="text-xs text-muted-foreground">Alinhamento</p>
                <span className="text-2xl font-bold">
                  {(data.comparativo.alinhamento * 100).toFixed(0)}%
                </span>
                <div className="mx-auto mt-2 h-3 w-full max-w-[200px] overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{
                      width: `${data.comparativo.alinhamento * 100}%`,
                    }}
                  />
                </div>
              </div>

              {data.comparativo.resumo_ia && (
                <>
                  <Separator />
                  <p className="text-sm text-muted-foreground">
                    {data.comparativo.resumo_ia}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Scale className="h-4 w-4" /> Comparativo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="py-8 text-center text-sm text-muted-foreground">
                Comparativo não disponível — aguardando votação na Câmara.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* AI Analysis */}
      {data.analise && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4 text-blue-500" /> Análise IA
              <Badge variant="outline" className="ml-auto text-[10px]">
                v{data.analise.versao}
              </Badge>
            </CardTitle>
            <CardDescription>
              Análise gerada por inteligência artificial para facilitar a compreensão
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Resumo leigo */}
            <div>
              <h3 className="mb-2 text-sm font-semibold">Resumo acessível</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {data.analise.resumo_leigo}
              </p>
            </div>

            {/* Impacto */}
            <div>
              <h3 className="mb-2 text-sm font-semibold">Impacto esperado</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {data.analise.impacto_esperado}
              </p>
            </div>

            {/* Áreas afetadas */}
            {data.analise.areas_afetadas.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold">Áreas afetadas</h3>
                <div className="flex flex-wrap gap-1">
                  {data.analise.areas_afetadas.map((area) => (
                    <Badge key={area} variant="secondary">
                      {area}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Argumentos */}
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-green-600">
                  <ThumbsUp className="h-3.5 w-3.5" /> A favor
                </h3>
                <ul className="space-y-1">
                  {data.analise.argumentos_favor.map((arg, i) => (
                    <li
                      key={i}
                      className="text-sm text-muted-foreground before:mr-2 before:content-['•']"
                    >
                      {arg}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-red-600">
                  <ThumbsDown className="h-3.5 w-3.5" /> Contra
                </h3>
                <ul className="space-y-1">
                  {data.analise.argumentos_contra.map((arg, i) => (
                    <li
                      key={i}
                      className="text-sm text-muted-foreground before:mr-2 before:content-['•']"
                    >
                      {arg}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resumo IA simples (quando não há análise completa) */}
      {!data.analise && data.resumo_ia && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resumo IA</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {data.resumo_ia}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
