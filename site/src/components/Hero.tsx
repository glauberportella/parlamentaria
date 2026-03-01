"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, MessageCircle, Vote, BarChart3 } from "lucide-react";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-brand-blue/5 via-white to-brand-green/5 pattern-bg" />

      {/* Floating accents */}
      <div className="absolute top-32 left-10 w-64 h-64 bg-brand-green/10 rounded-full blur-3xl" />
      <div className="absolute bottom-32 right-10 w-80 h-80 bg-brand-blue/10 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-brand-blue/10 text-brand-blue text-sm font-medium rounded-full mb-8">
              🇧🇷 Democracia Participativa • Open Source
            </span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-tight mb-6"
          >
            Sua voz no{" "}
            <span className="gradient-text">Congresso</span>
            <br />
            <span className="text-neutral-500 text-4xl sm:text-5xl lg:text-6xl">
              todos os dias
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg sm:text-xl text-neutral-600 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            Um assistente de IA no seu Telegram que explica proposições em
            linguagem simples, coleta seu voto e mostra se o Congresso ouviu
            a voz popular.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link
              href="https://t.me/parlamentariasocial_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 bg-brand-green text-white text-lg font-bold rounded-full hover:bg-brand-green-dark transition-all shadow-lg hover:shadow-xl hover:scale-105"
            >
              💬 Conversar no Telegram
              <span className="text-xs font-normal opacity-75">(em breve)</span>
              <ArrowRight size={20} />
            </Link>
            <Link
              href="/como-funciona"
              className="inline-flex items-center gap-2 px-8 py-4 border-2 border-neutral-300 text-neutral-700 text-lg font-semibold rounded-full hover:border-brand-blue hover:text-brand-blue transition-colors"
            >
              Como funciona
            </Link>
          </motion.div>
        </div>

        {/* Feature pills */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-20 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto"
        >
          <FeaturePill
            icon={<MessageCircle className="text-brand-green" size={24} />}
            title="Pergunte"
            description="Converse sobre qualquer proposição em linguagem simples"
          />
          <FeaturePill
            icon={<Vote className="text-brand-blue" size={24} />}
            title="Vote"
            description="Registre sua posição com um toque: SIM, NÃO ou ABSTENÇÃO"
          />
          <FeaturePill
            icon={<BarChart3 className="text-brand-yellow-dark" size={24} />}
            title="Acompanhe"
            description="Veja se o Congresso votou como a maioria popular queria"
          />
        </motion.div>
      </div>
    </section>
  );
}

function FeaturePill({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-4 p-5 bg-white rounded-2xl shadow-sm border border-neutral-100 hover:shadow-md transition-shadow">
      <div className="shrink-0 w-12 h-12 rounded-xl bg-neutral-50 flex items-center justify-center">
        {icon}
      </div>
      <div>
        <h3 className="font-bold text-neutral-900">{title}</h3>
        <p className="text-sm text-neutral-500 mt-1">{description}</p>
      </div>
    </div>
  );
}
