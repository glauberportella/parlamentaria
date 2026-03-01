"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  Code2,
  Heart,
  Building2,
  GraduationCap,
  HandHeart,
  Globe,
  GitBranch,
  TestTube,
  BookOpen,
  ShieldCheck,
  Accessibility,
  Rocket,
} from "lucide-react";

const colorStyles: Record<string, { bg: string; text: string; btnBg: string; btnHover: string }> = {
  "brand-blue": { bg: "bg-brand-blue/10", text: "text-brand-blue", btnBg: "bg-brand-blue/10", btnHover: "hover:bg-brand-blue/20" },
  "brand-green": { bg: "bg-brand-green/10", text: "text-brand-green", btnBg: "bg-brand-green/10", btnHover: "hover:bg-brand-green/20" },
  "brand-yellow-dark": { bg: "bg-brand-yellow-dark/10", text: "text-brand-yellow-dark", btnBg: "bg-brand-yellow-dark/10", btnHover: "hover:bg-brand-yellow-dark/20" },
};

const audiences = [
  {
    icon: <Code2 size={32} />,
    title: "Desenvolvedores",
    description:
      "Python, FastAPI, IA, bots, DevOps — contribua com código, testes, reviews. Stack moderna com Google ADK, Celery, SQLAlchemy async e mais.",
    details: [
      "Clone o repositório e rode testes em minutos",
      "591+ testes, 94% de cobertura — base sólida para contribuir",
      "Issues etiquetadas com 'good first issue' para começar",
    ],
    cta: "Ver issues no GitHub",
    href: "https://github.com/glauberportella/parlamentaria/issues",
    color: "brand-blue",
  },
  {
    icon: <Heart size={32} />,
    title: "Voluntários e Ativistas",
    description:
      "Teste o bot, reporte bugs, sugira melhorias, traduza conteúdo, ajude na curadoria de análises legislativas.",
    details: [
      "Use o bot e dê feedback sobre a experiência",
      "Ajude a validar análises de proposições",
      "Sugira melhorias na linguagem e acessibilidade",
    ],
    cta: "Entrar na comunidade",
    href: "https://github.com/glauberportella/parlamentaria/discussions",
    color: "brand-green",
  },
  {
    icon: <Building2 size={32} />,
    title: "ONGs e Institutos",
    description:
      "Organizações da sociedade civil podem integrar a Parlamentaria em programas de educação cívica, engajamento político e controle social.",
    details: [
      "API aberta para integração com seus sistemas",
      "Dados de votação popular para pesquisa e advocacy",
      "Parceria para alcançar comunidades vulneráveis",
    ],
    cta: "Propor parceria",
    href: "mailto:contato@parlamentaria.app?subject=Parceria%20ONG%20-%20Parlamentaria",
    color: "brand-yellow-dark",
  },
  {
    icon: <GraduationCap size={32} />,
    title: "Universidades e Pesquisadores",
    description:
      "Pesquisadores podem usar os dados abertos, contribuir com NLP em português e estudar democracia digital e participativa.",
    details: [
      "Dados estruturados da API Câmara + votação popular",
      "NLP em português: análise de textos legislativos",
      "Estudos sobre democracia participativa digital",
    ],
    cta: "Explorar dados",
    href: "https://dadosabertos.camara.leg.br",
    color: "brand-blue",
  },
  {
    icon: <HandHeart size={32} />,
    title: "Patrocinadores e Apoiadores",
    description:
      "Órgãos públicos, fundações, entidades e empresas que acreditam em transparência legislativa podem patrocinar o desenvolvimento.",
    details: [
      "Custeio de infraestrutura (servidores, APIs de IA)",
      "Financiamento de features específicas (WhatsApp, Senado)",
      "Apoio à manutenção e operação contínua",
    ],
    cta: "Fale sobre patrocínio",
    href: "mailto:contato@parlamentaria.app?subject=Patrocínio%20Parlamentaria",
    color: "brand-green",
  },
  {
    icon: <Globe size={32} />,
    title: "Cidadãos",
    description:
      "A contribuição mais poderosa é usar e compartilhar. Quanto mais gente participa, mais forte fica a voz popular.",
    details: [
      "Use o bot e vote nas proposições",
      "Compartilhe com amigos, família e colegas",
      "Quanto mais vozes, mais representativo o resultado",
    ],
    cta: "Compartilhar",
    href: "https://t.me/share/url?url=https://parlamentaria.app&text=Conhe%C3%A7a%20a%20Parlamentaria%20—%20IA%20para%20democracia%20participativa%20🏛️🇧🇷",
    color: "brand-yellow-dark",
  },
];

const contributionAreas = [
  {
    icon: <Globe size={20} />,
    title: "WhatsApp",
    description: "Homologação do adapter com a API real da Meta",
  },
  {
    icon: <GitBranch size={20} />,
    title: "Senado Federal",
    description: "Expandir para API do Senado, novos agentes",
  },
  {
    icon: <TestTube size={20} />,
    title: "Testes E2E",
    description: "Testes end-to-end com agentes reais",
  },
  {
    icon: <Rocket size={20} />,
    title: "CI/CD",
    description: "GitHub Actions completo, deploy automatizado",
  },
  {
    icon: <BookOpen size={20} />,
    title: "Documentação",
    description: "Guias, tradução para inglês, onboarding",
  },
  {
    icon: <ShieldCheck size={20} />,
    title: "Auditoria e LGPD",
    description: "Logs de auditoria, compliance e privacidade",
  },
  {
    icon: <Accessibility size={20} />,
    title: "Acessibilidade",
    description: "Áudio, linguagem simples, inclusão digital",
  },
  {
    icon: <Code2 size={20} />,
    title: "Performance",
    description: "Queries SQL, cache Redis avançado, paginação",
  },
];

export default function ContribuirPage() {
  return (
    <div className="pt-16">
      {/* Hero */}
      <section className="py-20 bg-gradient-to-br from-brand-yellow/10 via-white to-brand-green/5 pattern-bg">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl sm:text-5xl font-extrabold text-neutral-900 mb-6"
          >
            Construa a democracia
            <br />
            <span className="gradient-text">participativa conosco</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg text-neutral-600 max-w-2xl mx-auto leading-relaxed"
          >
            A Parlamentaria é um projeto open-source, apartidário e da
            comunidade. Existem muitas formas de participar — desenvolvedores,
            ONGs, pesquisadores, patrocinadores e cidadãos.
          </motion.p>
        </div>
      </section>

      {/* Audiences */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {audiences.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="flex flex-col p-8 rounded-2xl border border-neutral-100 hover:shadow-xl transition-all bg-white"
              >
                <div
                  className={`w-16 h-16 rounded-2xl ${colorStyles[item.color].bg} ${colorStyles[item.color].text} flex items-center justify-center mb-6`}
                >
                  {item.icon}
                </div>
                <h3 className="text-xl font-bold text-neutral-900 mb-3">
                  {item.title}
                </h3>
                <p className="text-neutral-500 leading-relaxed mb-4">
                  {item.description}
                </p>
                <ul className="space-y-2 mb-6 flex-1">
                  {item.details.map((d, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-neutral-600">
                      <span className="text-brand-green mt-0.5">✓</span>
                      {d}
                    </li>
                  ))}
                </ul>
                <Link
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex items-center justify-center gap-1 px-6 py-3 ${colorStyles[item.color].btnBg} ${colorStyles[item.color].text} font-semibold rounded-full ${colorStyles[item.color].btnHover} transition-colors text-sm`}
                >
                  {item.cta} →
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Contribution areas */}
      <section className="py-24 bg-neutral-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-extrabold text-neutral-900 mb-4">
              Áreas que precisam de contribuição
            </h2>
            <p className="text-neutral-600 max-w-2xl mx-auto">
              O core está construído (8 fases, 591+ testes). Essas são as áreas
              de expansão e refinamento abertas para a comunidade.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {contributionAreas.map((area, i) => (
              <motion.div
                key={area.title}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="p-5 bg-white rounded-xl border border-neutral-200 hover:shadow-md transition-all"
              >
                <div className="w-10 h-10 rounded-lg bg-brand-blue/10 text-brand-blue flex items-center justify-center mb-3">
                  {area.icon}
                </div>
                <h4 className="font-bold text-neutral-900 mb-1">
                  {area.title}
                </h4>
                <p className="text-sm text-neutral-500">{area.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How to contribute step by step */}
      <section className="py-24 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl font-extrabold text-neutral-900 mb-10 text-center"
          >
            Como contribuir com código
          </motion.h2>

          <div className="space-y-8">
            {[
              {
                step: "1",
                title: "Leia o AGENTS.md",
                description:
                  "O guia completo do projeto — arquitetura, padrões, convenções, estrutura de diretórios.",
              },
              {
                step: "2",
                title: "Escolha uma issue",
                description:
                  'Procure por labels "good first issue" ou "help wanted" no GitHub. Se tiver uma ideia nova, abra uma discussion.',
              },
              {
                step: "3",
                title: "Fork + Branch",
                description:
                  'Crie uma branch seguindo a convenção: feat/, fix/, docs/. Exemplo: feat/senado-integration.',
              },
              {
                step: "4",
                title: "Implemente com testes",
                description:
                  "Todo código novo deve vir com testes. Meta: manter cobertura ≥75%. Módulos críticos: ≥85%.",
              },
              {
                step: "5",
                title: "Abra um PR",
                description:
                  "Descreva o que fez, referencie a issue. Commits no padrão Conventional Commits (feat:, fix:, docs:).",
              },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="flex gap-6 items-start"
              >
                <div className="shrink-0 w-12 h-12 rounded-full bg-brand-green text-white font-bold flex items-center justify-center text-lg">
                  {item.step}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-neutral-900 mb-1">
                    {item.title}
                  </h3>
                  <p className="text-neutral-600">{item.description}</p>
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-12 p-6 bg-neutral-50 rounded-2xl border border-neutral-200"
          >
            <h4 className="font-bold text-neutral-900 mb-3">Quick start</h4>
            <pre className="text-sm text-neutral-700 overflow-x-auto leading-relaxed">
              {`git clone https://github.com/glauberportella/parlamentaria.git
cd parlamentaria/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v --cov=app`}
            </pre>
          </motion.div>
        </div>
      </section>

      {/* Sponsors CTA */}
      <section className="py-20 bg-gradient-to-r from-brand-blue to-brand-green text-white">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl sm:text-4xl font-extrabold mb-6">
              Quer patrocinar ou
              <br />
              apoiar institucionalmente?
            </h2>
            <p className="text-white/80 text-lg mb-8 leading-relaxed">
              Órgãos da União, fundações, entidades de classe e empresas podem
              apoiar a Parlamentaria financeiramente ou com recursos técnicos.
              Todo patrocínio é público e transparente.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href="mailto:contato@parlamentaria.app?subject=Patrocínio%20Institucional%20-%20Parlamentaria"
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-brand-blue text-lg font-bold rounded-full hover:bg-neutral-100 transition-colors shadow-lg"
              >
                📧 Falar sobre patrocínio
              </a>
              <Link
                href="https://github.com/glauberportella/parlamentaria"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-8 py-4 border-2 border-white/50 text-white text-lg font-semibold rounded-full hover:bg-white/10 transition-colors"
              >
                ⭐ Estrela no GitHub
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
