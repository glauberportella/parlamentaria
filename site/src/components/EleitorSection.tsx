"use client";

import { motion } from "framer-motion";
import {
  MessageSquareText,
  ShieldCheck,
  Bell,
  Eye,
  Zap,
  Lock,
} from "lucide-react";

const benefits = [
  {
    icon: <MessageSquareText size={28} />,
    title: "Sem juridiquês",
    description:
      "A IA traduz proposições legislativas para linguagem que qualquer pessoa entende. Nada de jargão — só clareza.",
  },
  {
    icon: <ShieldCheck size={28} />,
    title: "Apartidário",
    description:
      "Análises equilibradas com prós e contras. Sem viés político, sem propaganda. Apenas fatos e informação.",
  },
  {
    icon: <Bell size={28} />,
    title: "Alertas personalizados",
    description:
      "Receba notificações sobre proposições dos temas que mais importam para você: saúde, educação, economia, segurança.",
  },
  {
    icon: <Eye size={28} />,
    title: "Transparência total",
    description:
      "Veja como cada deputado votou. Compare com o voto popular. Descubra quem realmente representa você.",
  },
  {
    icon: <Zap size={28} />,
    title: "Um toque para votar",
    description:
      "Vote SIM, NÃO ou ABSTENÇÃO em qualquer proposição diretamente no Telegram. Sua voz registrada em segundos.",
  },
  {
    icon: <Lock size={28} />,
    title: "Privacidade respeitada",
    description:
      "Dados mínimos, sem rastreamento, sem venda de informações. O voto é seu e a privacidade também.",
  },
];

export function EleitorSection() {
  return (
    <section id="para-eleitor" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <motion.span
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-green/10 text-brand-green text-sm font-medium rounded-full mb-4"
          >
            🧑‍💼 Para o Cidadão
          </motion.span>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl sm:text-4xl font-extrabold text-neutral-900 mb-4"
          >
            Sua voz merece ser ouvida{" "}
            <span className="gradient-text">entre as eleições</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-lg text-neutral-600 leading-relaxed"
          >
            Você trabalha, estuda, cuida da família — e não tem tempo de ler
            diários oficiais. Mas as leis afetam sua vida, seu bolso, sua saúde.
            A Parlamentaria coloca a informação na palma da sua mão.
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
              className="group p-6 rounded-2xl border border-neutral-100 hover:border-brand-green/30 hover:shadow-lg transition-all bg-white"
            >
              <div className="w-14 h-14 rounded-2xl bg-brand-green/10 text-brand-green flex items-center justify-center mb-5 group-hover:bg-brand-green group-hover:text-white transition-colors">
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
            href="https://t.me/Parlamentaria"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-8 py-4 bg-brand-green text-white text-lg font-bold rounded-full hover:bg-brand-green-dark transition-all shadow-lg hover:shadow-xl hover:scale-105"
          >
            💬 Experimentar agora no Telegram
          </a>
          <p className="text-sm text-neutral-400 mt-3">
            Gratuito, sem cadastro em site, sem instalar app
          </p>
        </motion.div>
      </div>
    </section>
  );
}
