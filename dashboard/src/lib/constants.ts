/** Constants — URLs, enums, temas, UFs. */

export const TEMAS = [
  "Administração Pública",
  "Agricultura",
  "Ciência e Tecnologia",
  "Comunicações",
  "Consumidor",
  "Cultura",
  "Direitos Humanos",
  "Economia",
  "Educação",
  "Energia",
  "Esporte",
  "Indústria",
  "Meio Ambiente",
  "Política e Administração Pública",
  "Previdência e Assistência Social",
  "Saúde",
  "Segurança",
  "Trabalho e Emprego",
  "Transporte e Trânsito",
  "Turismo",
] as const;

export const UFS = [
  "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
  "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
  "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
] as const;

export const TIPOS_PROPOSICAO = [
  "PL", "PEC", "PLP", "MPV", "PDL", "PRC", "REQ",
] as const;

export const VOTO_LABELS: Record<string, string> = {
  SIM: "A Favor",
  NAO: "Contra",
  ABSTENCAO: "Abstenção",
};

export const VOTO_COLORS: Record<string, string> = {
  SIM: "hsl(var(--chart-1))",
  NAO: "hsl(var(--chart-2))",
  ABSTENCAO: "hsl(var(--chart-3))",
};

export const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Proposições", href: "/proposicoes", icon: "FileText" },
  { label: "Votação Popular", href: "/votacao-popular", icon: "Vote" },
  { label: "Comparativos", href: "/comparativos", icon: "Scale" },
  { label: "Meu Mandato", href: "/meu-mandato", icon: "User" },
  { label: "Configurações", href: "/configuracoes", icon: "Settings" },
] as const;
