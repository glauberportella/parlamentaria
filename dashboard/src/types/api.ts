/** TypeScript types for the Parlamentaria API responses. */

// ─── Auth ──────────────────────────────────────────

export interface ParlamentarUser {
  id: string;
  deputado_id: number;
  email: string;
  nome: string;
  cargo: string;
  tipo: TipoParlamentarUser;
  ativo: boolean;
  temas_acompanhados: string[] | null;
  notificacoes_email: boolean;
  ultimo_login: string | null;
  created_at: string;
}

export type TipoParlamentarUser = "DEPUTADO" | "ASSESSOR" | "LIDERANCA";

export interface LoginRequest {
  email: string;
  codigo_convite?: string;
}

export interface VerifyRequest {
  token: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshRequest {
  refresh_token: string;
}

// ─── Proposição ────────────────────────────────────

export interface Proposicao {
  id: number;
  tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  texto_completo_url: string | null;
  data_apresentacao: string;
  situacao: string | null;
  temas: string[] | null;
  autores: Record<string, unknown>[] | null;
  resumo_ia: string | null;
  ultima_sincronizacao: string | null;
  created_at: string;
  updated_at: string;
}

export interface VotoPopularResumo {
  total: number;
  sim: number;
  nao: number;
  abstencao: number;
  percentual_sim: number;
  percentual_nao: number;
  percentual_abstencao: number;
}

export interface AnaliseIAResumo {
  id: string;
  resumo_leigo: string;
  impacto_esperado: string;
  areas_afetadas: string[];
  argumentos_favor: string[];
  argumentos_contra: string[];
  data_geracao: string;
  versao: number;
}

export interface ComparativoResumo {
  id: string;
  resultado_camara: "APROVADO" | "REJEITADO";
  votos_camara_sim: number;
  votos_camara_nao: number;
  alinhamento: number;
  resumo_ia: string | null;
  data_geracao: string;
}

export interface ProposicaoListItem {
  id: number;
  tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  situacao: string | null;
  temas: string[] | null;
  data_apresentacao: string | null;
  resumo_ia: string | null;
  votos: VotoPopularResumo;
  tem_analise: boolean;
  tem_comparativo: boolean;
}

export interface ProposicaoDetalhe {
  id: number;
  tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  texto_completo_url: string | null;
  situacao: string | null;
  temas: string[] | null;
  autores: Record<string, unknown>[] | null;
  data_apresentacao: string | null;
  resumo_ia: string | null;
  ultima_sincronizacao: string | null;
  votos: VotoPopularResumo;
  analise: AnaliseIAResumo | null;
  comparativo: ComparativoResumo | null;
}

export interface ProposicoesFilters {
  tema?: string;
  tipo?: string;
  ano?: number;
  situacao?: string;
  busca?: string;
  ordenar?: "recentes" | "votos_desc" | "votos_asc" | "ano_desc";
  pagina?: number;
  itens?: number;
}

export interface AnaliseIA {
  id: string;
  proposicao_id: number;
  resumo_leigo: string;
  impacto_esperado: string;
  areas_afetadas: string[];
  argumentos_favor: string[];
  argumentos_contra: string[];
  provedor_llm: string;
  modelo: string;
  data_geracao: string;
  versao: number;
}

// ─── Votação Popular ───────────────────────────────

export interface ResultadoVotacao {
  proposicao_id: number;
  total: number;
  SIM: number;
  NAO: number;
  ABSTENCAO: number;
  percentual_sim: number;
  percentual_nao: number;
  percentual_abstencao: number;
}

export interface ResultadoCompleto {
  oficial: ResultadoVotacao;
  consultivo: ResultadoVotacao;
}

// ─── Comparativo ───────────────────────────────────

export interface Comparativo {
  id: string;
  proposicao_id: number;
  votacao_camara_id: number;
  voto_popular_sim: number;
  voto_popular_nao: number;
  voto_popular_abstencao: number;
  resultado_camara: "APROVADO" | "REJEITADO";
  votos_camara_sim: number;
  votos_camara_nao: number;
  alinhamento: number;
  resumo_ia: string | null;
  data_geracao: string;
}

// ─── Deputado ──────────────────────────────────────

export interface Deputado {
  id: number;
  nome: string;
  nome_civil: string | null;
  sigla_partido: string | null;
  sigla_uf: string | null;
  foto_url: string | null;
  email: string | null;
  situacao: string | null;
}

// ─── Dashboard ─────────────────────────────────────

export interface DashboardKPIs {
  total_proposicoes_ativas: number;
  total_eleitores_cadastrados: number;
  total_votos_populares: number;
  total_comparativos: number;
  alinhamento_medio: number;
  taxa_participacao: number;
}

export interface DashboardTendencias {
  votos_ultimos_7_dias: number;
  novos_eleitores_ultimos_7_dias: number;
  proposicoes_mais_votadas: ProposicaoRanking[];
  temas_mais_ativos: TemaAtivo[];
}

export interface ProposicaoRanking {
  proposicao_id: number;
  tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  total_votos: number;
  percentual_sim: number;
  percentual_nao: number;
  alinhamento: number | null;
}

export interface TemaAtivo {
  tema: string;
  total_votos: number;
  total_proposicoes: number;
}

export interface DashboardAlerta {
  tipo: string;
  mensagem: string;
  urgencia: "alta" | "media" | "baixa";
}

export interface DashboardResumo {
  kpis: DashboardKPIs;
  tendencias: DashboardTendencias;
  alertas: DashboardAlerta[];
}

// ─── Votos Analíticos ──────────────────────────────

export interface VotosPorTema {
  tema: string;
  total_votos: number;
  sim: number;
  nao: number;
  abstencao: number;
}

export interface VotosPorUF {
  uf: string;
  total_votos: number;
  sim: number;
  nao: number;
  abstencao: number;
}

export interface VotosTimeline {
  data: string;
  total_votos: number;
  sim: number;
  nao: number;
  abstencao: number;
}

// ─── Paginação ─────────────────────────────────────

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
  pagina: number;
  itens_por_pagina: number;
}

// ─── Comparativos (Fase 4) ─────────────────────────

export interface ComparativoListItem {
  id: string;
  proposicao_id: number;
  tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  temas: string[] | null;
  resultado_camara: "APROVADO" | "REJEITADO";
  voto_popular_sim: number;
  voto_popular_nao: number;
  voto_popular_abstencao: number;
  votos_camara_sim: number;
  votos_camara_nao: number;
  alinhamento: number;
  resumo_ia: string | null;
  data_geracao: string | null;
}

export interface EvolucaoAlinhamentoItem {
  mes: string;
  alinhamento_medio: number;
  total_comparativos: number;
}

export interface ComparativosFilters {
  alinhamento_min?: number;
  alinhamento_max?: number;
  resultado?: "APROVADO" | "REJEITADO";
  tema?: string;
  ordenar?: "recentes" | "alinhamento_asc" | "alinhamento_desc";
  pagina?: number;
  itens?: number;
}

// ─── Meu Mandato (Fase 4) ─────────────────────────

export interface DeputadoInfo {
  id: number;
  nome: string;
  sigla_partido: string | null;
  sigla_uf: string | null;
  foto_url: string | null;
}

export interface MandatoResumo {
  deputado: DeputadoInfo | null;
  total_comparativos: number;
  alinhamento_medio: number;
  total_votos_populares_recebidos: number;
  proposicoes_acompanhadas: number;
  comparativos_alinhados: number;
  comparativos_divergentes: number;
  temas_acompanhados: string[] | null;
}

export interface AlinhamentoSerieItem {
  mes: string;
  alinhamento: number;
  total: number;
}

export interface AlinhamentoComparacao {
  pessoal: AlinhamentoSerieItem[];
  partido: AlinhamentoSerieItem[];
  uf: AlinhamentoSerieItem[];
  alinhamento_medio_pessoal: number;
  alinhamento_medio_partido: number;
  alinhamento_medio_uf: number;
  sigla_partido: string | null;
  sigla_uf: string | null;
}

// ─── API Response wrapper ──────────────────────────

export interface ApiError {
  detail: string;
}

// ─── Profile Update (Fase 5) ──────────────────────

export interface ParlamentarUserUpdate {
  nome?: string;
  cargo?: string;
  temas_acompanhados?: string[];
  notificacoes_email?: boolean;
}
