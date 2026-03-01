"use client";

import { motion } from "framer-motion";
import { ChatSimulation } from "./ChatSimulation";

export function DemoSection() {
  return (
    <section className="py-24 bg-gradient-to-b from-neutral-50 to-white overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Text */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-brand-green/10 text-brand-green text-sm font-medium rounded-full mb-6">
              💬 Conversa real
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-neutral-900 mb-6 leading-tight">
              Como é usar a<br />
              <span className="gradient-text">Parlamentaria</span>
            </h2>
            <p className="text-lg text-neutral-600 leading-relaxed mb-6">
              Em breve no Telegram: encontre o bot e comece a conversar. Sem
              formulários, sem instalação — só você e a democracia.
            </p>
            <ul className="space-y-4">
              {[
                "Pergunte sobre qualquer proposição em linguagem natural",
                "Receba análise apartidária com prós e contras",
                "Vote com um toque e veja o resultado consolidado",
                "Seja notificado quando a Câmara votar de verdade",
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-brand-green/10 text-brand-green flex items-center justify-center text-sm font-bold mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-neutral-700">{item}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Chat mockup */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            <ChatSimulation />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
