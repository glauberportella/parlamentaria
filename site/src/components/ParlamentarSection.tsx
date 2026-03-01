"use client";

import { motion } from "framer-motion";
import { Rss, Webhook, BarChart3, Users, TrendingUp, Shield } from "lucide-react";

const benefits = [
  {
    icon: <Rss size={28} />,
    title: "RSS Feed em tempo real",
    description:
      "Assine um feed RSS com o resultado consolidado da votação popular. Filtre por tema (saúde, educação, economia) e por UF.",
  },
  {
    icon: <Webhook size={28} />,
    title: "Webhooks para seu gabinete",
    description:
      "Receba dados estruturados direto no sistema do mandato. JSON com HMAC-SHA256, retry automático, zero fricção.",
  },
  {
    icon: <BarChart3 size={28} />,
    title: "Comparativo público",
    description:
      "Veja o alinhamento entre seu voto e a posição popular. Transparência que fortalece a confiança do eleitorado.",
  },
  {
    icon: <Users size={28} />,
    title: "Voz real dos eleitores",
    description:
      "Não é pesquisa de opinião — são eleitores que leram a análise, entenderam a proposição e fizeram sua escolha.",
  },
  {
    icon: <TrendingUp size={28} />,
    title: "Dados antes da votação",
    description:
      "Receba o termômetro popular antes de votar no plenário. Mais informação = decisões mais representativas.",
  },
  {
    icon: <Shield size={28} />,
    title: "Open source e auditável",
    description:
      "Todo o código é aberto. Nenhuma manipulação oculta. Dados rastreáveis à fonte oficial da Câmara.",
  },
];

export function ParlamentarSection() {
  return (
    <section id="para-parlamentar" className="py-24 bg-neutral-50 pattern-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <motion.span
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-blue/10 text-brand-blue text-sm font-medium rounded-full mb-4"
          >
            🏛️ Para Parlamentares
          </motion.span>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl sm:text-4xl font-extrabold text-neutral-900 mb-4"
          >
            Ouça o eleitor{" "}
            <span className="gradient-text">antes de votar</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-lg text-neutral-600 leading-relaxed"
          >
            Legislar é representar. A Parlamentaria entrega a posição real dos
            eleitores sobre cada proposição — direto no seu sistema, antes da
            votação no plenário.
          </motion.p>
        </div>

        {/* Benefits grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {benefits.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="group p-6 rounded-2xl border border-neutral-200 hover:border-brand-blue/30 hover:shadow-lg transition-all bg-white"
            >
              <div className="w-14 h-14 rounded-2xl bg-brand-blue/10 text-brand-blue flex items-center justify-center mb-5 group-hover:bg-brand-blue group-hover:text-white transition-colors">
                {item.icon}
              </div>
              <h3 className="text-lg font-bold text-neutral-900 mb-2">
                {item.title}
              </h3>
              <p className="text-neutral-500 leading-relaxed">
                {item.description}
              </p>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <a
            href="mailto:contato@parlamentaria.app?subject=Interesse%20em%20assinar%20o%20feed%20da%20Parlamentaria"
            className="inline-flex items-center gap-2 px-8 py-4 bg-brand-blue text-white text-lg font-bold rounded-full hover:bg-brand-blue-light transition-all shadow-lg hover:shadow-xl hover:scale-105"
          >
            📡 Assinar o Feed de Voto Popular
          </a>
          <p className="text-sm text-neutral-400 mt-3">
            RSS Feed gratuito • Webhooks via API • Dados abertos
          </p>
        </motion.div>
      </div>
    </section>
  );
}
