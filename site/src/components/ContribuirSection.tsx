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
} from "lucide-react";

const audiences = [
  {
    icon: <Code2 size={28} />,
    title: "Desenvolvedores",
    description:
      "Python, FastAPI, IA, bots, DevOps — contribua com código, testes, reviews. Stack moderna com Google ADK, Celery e mais.",
    cta: "Ver issues no GitHub",
    href: "https://github.com/glauberportella/parlamentaria/issues",
  },
  {
    icon: <Heart size={28} />,
    title: "Voluntários e Ativistas",
    description:
      "Teste o bot, reporte bugs, sugira melhorias, traduza conteúdo, ajude na curadoria e revisão de análises legislativas.",
    cta: "Entrar na comunidade",
    href: "https://github.com/glauberportella/parlamentaria/discussions",
  },
  {
    icon: <Building2 size={28} />,
    title: "ONGs e Institutos",
    description:
      "Organizações da sociedade civil podem integrar a Parlamentaria em seus programas de educação cívica e engajamento político.",
    cta: "Fale conosco",
    href: "mailto:contato@parlamentaria.app?subject=Parceria%20ONG",
  },
  {
    icon: <GraduationCap size={28} />,
    title: "Universidades",
    description:
      "Pesquisadores e acadêmicos podem usar os dados abertos, contribuir com NLP em português e estudar democracia digital.",
    cta: "Explorar dados",
    href: "https://dadosabertos.camara.leg.br",
  },
  {
    icon: <HandHeart size={28} />,
    title: "Patrocinadores",
    description:
      "Órgãos públicos, fundações e empresas que acreditam em transparência legislativa podem patrocinar o desenvolvimento.",
    cta: "Patrocinar o projeto",
    href: "mailto:contato@parlamentaria.app?subject=Patrocínio%20Parlamentaria",
  },
  {
    icon: <Globe size={28} />,
    title: "Cidadãos Comuns",
    description:
      "A contribuição mais poderosa é usar e compartilhar. Convide amigos, familiares e colegas. A democracia precisa de todos.",
    cta: "Compartilhar no Telegram",
    href: "https://t.me/share/url?url=https://parlamentaria.app&text=Conhe%C3%A7a%20a%20Parlamentaria%20%E2%80%94%20IA%20para%20democracia%20participativa",
  },
];

export function ContribuirSection() {
  return (
    <section id="contribuir" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <motion.span
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-yellow/30 text-neutral-800 text-sm font-medium rounded-full mb-4"
          >
            🤝 Faça Parte
          </motion.span>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl sm:text-4xl font-extrabold text-neutral-900 mb-4"
          >
            Democracia participativa
            <br />
            <span className="gradient-text">se constrói em conjunto</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-lg text-neutral-600 leading-relaxed"
          >
            A Parlamentaria é open-source e da comunidade. Existem muitas formas
            de participar — cada uma importa.
          </motion.p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {audiences.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="group flex flex-col p-6 rounded-2xl border border-neutral-100 hover:shadow-lg transition-all bg-white"
            >
              <div className="w-14 h-14 rounded-2xl bg-brand-yellow/20 text-neutral-800 flex items-center justify-center mb-5">
                {item.icon}
              </div>
              <h3 className="text-lg font-bold text-neutral-900 mb-2">
                {item.title}
              </h3>
              <p className="text-neutral-500 leading-relaxed flex-1">
                {item.description}
              </p>
              <Link
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-brand-blue font-semibold text-sm mt-4 hover:underline"
              >
                {item.cta} →
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
