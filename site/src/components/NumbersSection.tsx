"use client";

import { motion } from "framer-motion";
import { Github } from "lucide-react";

const stats = [
  { value: "591+", label: "Testes automatizados" },
  { value: "94%", label: "Cobertura de código" },
  { value: "5", label: "Agentes de IA" },
  { value: "25+", label: "Tools do ADK" },
];

export function NumbersSection() {
  return (
    <section className="py-20 bg-gradient-to-r from-brand-blue to-brand-green text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl sm:text-4xl font-extrabold mb-4"
          >
            Construído com rigor técnico
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-white/80 text-lg max-w-2xl mx-auto"
          >
            Uma base sólida, testada e open-source. Pronta para receber
            contribuições e crescer com a comunidade.
          </motion.p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <p className="text-4xl sm:text-5xl font-extrabold mb-2">
                {stat.value}
              </p>
              <p className="text-white/70 text-sm font-medium">{stat.label}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-12"
        >
          <a
            href="https://github.com/glauberportella/parlamentaria"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white/20 backdrop-blur text-white font-semibold rounded-full hover:bg-white/30 transition-colors border border-white/30"
          >
            <Github size={20} />
            Ver no GitHub
          </a>
        </motion.div>
      </div>
    </section>
  );
}
