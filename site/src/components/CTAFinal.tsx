"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export function CTAFinal() {
  return (
    <section className="py-24 bg-neutral-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl sm:text-5xl font-extrabold text-neutral-900 mb-6 leading-tight">
            A democracia não acontece
            <br />
            <span className="gradient-text">a cada 4 anos</span>
          </h2>
          <p className="text-lg text-neutral-600 max-w-2xl mx-auto mb-10 leading-relaxed">
            Acontece todos os dias — em cada proposição votada, em cada decisão
            que impacta sua vida. A Parlamentaria existe para que sua voz nunca
            seja silenciada entre as eleições.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="https://t.me/Parlamentaria"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-brand-green text-white text-lg font-bold rounded-full hover:bg-brand-green-dark transition-all shadow-lg hover:shadow-xl hover:scale-105"
            >
              💬 Começar agora no Telegram
              <span className="text-xs font-normal opacity-75 ml-1">(em breve)</span>
            </Link>
            <Link
              href="https://github.com/glauberportella/parlamentaria"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 border-2 border-neutral-300 text-neutral-700 text-lg font-semibold rounded-full hover:border-brand-blue hover:text-brand-blue transition-colors"
            >
              ⭐ Dar uma estrela no GitHub
            </Link>
          </div>

          <p className="text-neutral-400 text-sm mt-8">
            Open source • MIT License • Feito pela comunidade, para a comunidade
          </p>
        </motion.div>
      </div>
    </section>
  );
}
