"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  RefreshCw,
  Brain,
  Bell,
  MessageCircle,
  Vote,
  PieChart,
  Rss,
  GitCompareArrows,
  ThumbsUp,
} from "lucide-react";
import { MermaidDiagram } from "@/components/MermaidDiagram";

const architectureChart = `graph TD
  subgraph ENTRADA["🧑 Eleitor"]
    TG["📱 Telegram"]
    WA["📱 WhatsApp"]
  end

  subgraph GATEWAY["Channel Gateway"]
    WH["Webhooks + Adapters"]
  end

  subgraph ADK["🤖 ParlamentarAgent · Google ADK + Gemini"]
    ROOT["Root Agent"]
    PA["📋 Proposição Agent<br/><small>buscar · resumir · analisar</small>"]
    VA["🗳️ Votação Agent<br/><small>votar · resultado</small>"]
    DA["🏛️ Deputado Agent<br/><small>perfil · gastos</small>"]
    EA["👤 Eleitor Agent<br/><small>cadastro · preferências</small>"]
    PUA["📡 Publicação Agent<br/><small>comparar · feedback · RSS</small>"]
  end

  subgraph INFRA["Infraestrutura"]
    PG["🐘 PostgreSQL<br/><small>dados</small>"]
    RD["⚡ Redis<br/><small>cache + filas</small>"]
    API["🏛️ API Câmara<br/><small>dados abertos</small>"]
  end

  subgraph SAIDA["📡 Saída para Parlamentares"]
    RSS["📰 RSS Feed"]
    WHK["🔗 Webhooks"]
  end

  TG --> WH
  WA --> WH
  WH --> ROOT
  ROOT --> PA
  ROOT --> VA
  ROOT --> DA
  ROOT --> EA
  ROOT --> PUA
  PA --> PG
  PA --> API
  VA --> PG
  DA --> API
  EA --> PG
  PUA --> RSS
  PUA --> WHK
  ROOT --> RD

  style ENTRADA fill:#e8f5ee,stroke:#009c3b,color:#171717
  style GATEWAY fill:#eef2ff,stroke:#002776,color:#171717
  style ADK fill:#f0fdf4,stroke:#009c3b,color:#171717
  style INFRA fill:#fff9db,stroke:#e6c900,color:#171717
  style SAIDA fill:#eef2ff,stroke:#002776,color:#171717
`;


const colorMap: Record<string, { bg: string; text: string }> = {
  "brand-blue": { bg: "bg-brand-blue/10", text: "text-brand-blue" },
  "brand-green": { bg: "bg-brand-green/10", text: "text-brand-green" },
  "brand-yellow-dark": { bg: "bg-brand-yellow-dark/10", text: "text-brand-yellow-dark" },
};

const steps = [
  {
    icon: <RefreshCw size={24} />,
    number: "01",
    title: "Sincronização",
    description:
      "O sistema monitora continuamente a API de Dados Abertos da Câmara dos Deputados. Proposições novas, votações agendadas e eventos de plenário são sincronizados automaticamente a cada 15 minutos.",
    color: "brand-blue",
  },
  {
    icon: <Brain size={24} />,
    number: "02",
    title: "Análise por IA",
    description:
      "Cada proposição é analisada por agentes de IA especializados. O texto legislativo é traduzido para linguagem acessível, com resumo dos impactos, áreas afetadas, argumentos a favor e contra.",
    color: "brand-green",
  },
  {
    icon: <Bell size={24} />,
    number: "03",
    title: "Notificação Proativa",
    description:
      "Eleitores cadastrados recebem alertas sobre proposições relevantes ao seu perfil. Você escolhe os temas — saúde, educação, economia, segurança — e a IA cuida do resto.",
    color: "brand-yellow-dark",
  },
  {
    icon: <MessageCircle size={24} />,
    number: "04",
    title: "Conversa Natural",
    description:
      'O eleitor pode perguntar sobre qualquer proposição em linguagem natural: "O que é o PL 1234?", "Como isso afeta a saúde pública?". O agente responde sem jargão político.',
    color: "brand-blue",
  },
  {
    icon: <Vote size={24} />,
    number: "05",
    title: "Voto Popular",
    description:
      "Com um toque, o eleitor registra sua posição: SIM, NÃO ou ABSTENÇÃO. O voto é registrado de forma segura e anônima, vinculado à proposição em debate.",
    color: "brand-green",
  },
  {
    icon: <PieChart size={24} />,
    number: "06",
    title: "Consolidação em Tempo Real",
    description:
      "Os votos populares são agregados em tempo real. O resultado consolidado mostra a posição da maioria, percentuais de cada opção e total de participantes.",
    color: "brand-yellow-dark",
  },
  {
    icon: <Rss size={24} />,
    number: "07",
    title: "Publicação para Parlamentares",
    description:
      "Resultados são disponibilizados via RSS Feed e Webhooks. Parlamentares assinam o feed e recebem a posição popular antes de votar no plenário.",
    color: "brand-blue",
  },
  {
    icon: <GitCompareArrows size={24} />,
    number: "08",
    title: "Comparativo Pop vs Real",
    description:
      "Quando a Câmara vota, o sistema compara o resultado parlamentar com o voto popular. Um índice de alinhamento (0-100%) mede a representatividade.",
    color: "brand-green",
  },
  {
    icon: <ThumbsUp size={24} />,
    number: "09",
    title: "Feedback ao Eleitor",
    description:
      'O eleitor recebe o resultado: "O PL 1234 foi APROVADO. 73% dos eleitores votaram SIM. Alinhamento: 95%." Transparência total do início ao fim.',
    color: "brand-yellow-dark",
  },
];

export default function ComoFuncionaPage() {
  return (
    <div className="pt-16">
      {/* Hero */}
      <section className="py-20 bg-gradient-to-br from-brand-blue/5 via-white to-brand-green/5 pattern-bg">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl sm:text-5xl font-extrabold text-neutral-900 mb-6"
          >
            Como a{" "}
            <span className="gradient-text">Parlamentaria</span>{" "}
            funciona
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg text-neutral-600 max-w-2xl mx-auto leading-relaxed"
          >
            Da proposição legislativa ao feedback final — um ciclo completo de
            democracia participativa em 9 etapas.
          </motion.p>
        </div>
      </section>

      {/* Steps */}
      <section className="py-24 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-neutral-200 hidden md:block" />

            <div className="space-y-12">
              {steps.map((step, i) => (
                <motion.div
                  key={step.number}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                  className="flex gap-6 md:gap-8 items-start"
                >
                  {/* Number circle */}
                  <div
                    className={`shrink-0 w-16 h-16 rounded-2xl ${colorMap[step.color].bg} ${colorMap[step.color].text} flex items-center justify-center relative z-10`}
                  >
                    {step.icon}
                  </div>

                  {/* Content */}
                  <div className="flex-1 pb-8">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xs font-mono text-neutral-400 bg-neutral-100 px-2 py-1 rounded">
                        {step.number}
                      </span>
                      <h3 className="text-xl font-bold text-neutral-900">
                        {step.title}
                      </h3>
                    </div>
                    <p className="text-neutral-600 leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Architecture diagram */}
      <section className="py-20 bg-neutral-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-extrabold text-neutral-900 mb-4">
              Arquitetura técnica
            </h2>
            <p className="text-neutral-600 max-w-2xl mx-auto">
              Multi-agent architecture com Google ADK, 5 agentes especializados
              e 25+ ferramentas integradas.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="bg-white rounded-2xl border border-neutral-200 p-6 sm:p-8"
          >
            <MermaidDiagram chart={architectureChart} />
          </motion.div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl font-extrabold text-neutral-900 mb-10 text-center"
          >
            Stack tecnológica
          </motion.h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { name: "Python 3.12", desc: "Backend" },
              { name: "FastAPI", desc: "API async" },
              { name: "Google ADK", desc: "Agentes IA" },
              { name: "Gemini", desc: "LLM" },
              { name: "PostgreSQL 16", desc: "Banco de dados" },
              { name: "Redis", desc: "Cache + filas" },
              { name: "Celery", desc: "Jobs async" },
              { name: "Docker", desc: "Containers" },
              { name: "Telegram", desc: "Canal primário" },
              { name: "WhatsApp", desc: "Canal secundário" },
              { name: "pytest", desc: "591+ testes" },
              { name: "Ruff", desc: "Linting" },
            ].map((tech, i) => (
              <motion.div
                key={tech.name}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="text-center p-4 rounded-xl border border-neutral-100 hover:shadow-md transition-shadow"
              >
                <p className="font-bold text-neutral-900">{tech.name}</p>
                <p className="text-sm text-neutral-400">{tech.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-gradient-to-r from-brand-blue to-brand-green text-white text-center">
        <div className="max-w-3xl mx-auto px-4">
          <h2 className="text-3xl sm:text-4xl font-extrabold mb-6">
            Quer ver o código?
          </h2>
          <p className="text-white/80 text-lg mb-8">
            Todo o projeto é open-source. Explore, contribua e ajude a
            construir o futuro da democracia participativa.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="https://github.com/glauberportella/parlamentaria"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-brand-blue text-lg font-bold rounded-full hover:bg-neutral-100 transition-colors shadow-lg"
            >
              Ver no GitHub
            </Link>
            <Link
              href="https://t.me/parlamentariasocial_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 border-2 border-white/50 text-white text-lg font-semibold rounded-full hover:bg-white/10 transition-colors"
            >
              💬 Testar no Telegram
              <span className="text-xs font-normal opacity-75 ml-1">(em breve)</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
