"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";

interface Message {
  sender: "user" | "bot";
  text: string;
}

const conversation: Message[] = [
  { sender: "user", text: "O que é o PL 1234/2026?" },
  {
    sender: "bot",
    text: "📋 O PL 1234/2026 propõe a reforma do sistema tributário brasileiro, simplificando impostos e criando o IVA dual.\n\n✅ A favor: simplificação, fim da guerra fiscal\n❌ Contra: possível aumento de carga em serviços\n\nDeseja votar nesta proposição?",
  },
  { sender: "user", text: "Sim, quero votar" },
  {
    sender: "bot",
    text: "🗳️ Como você vota no PL 1234/2026?\n\n[  SIM  ]  [  NÃO  ]  [  ABSTENÇÃO  ]",
  },
  { sender: "user", text: "SIM" },
  {
    sender: "bot",
    text: "✅ Voto registrado!\n\n📊 Resultado parcial:\n• SIM: 73% (1.247 votos)\n• NÃO: 21% (362 votos)\n• Abstenção: 6% (98 votos)\n\nVocê será notificado quando a Câmara votar!",
  },
];

export function ChatSimulation() {
  const [visibleMessages, setVisibleMessages] = useState<number>(0);

  useEffect(() => {
    if (visibleMessages < conversation.length) {
      const delay = conversation[visibleMessages]?.sender === "bot" ? 1500 : 800;
      const timer = setTimeout(() => {
        setVisibleMessages((prev) => prev + 1);
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [visibleMessages]);

  return (
    <div className="w-full max-w-sm mx-auto">
      {/* Phone frame */}
      <div className="bg-neutral-900 rounded-[2.5rem] p-3 shadow-2xl">
        {/* Screen */}
        <div className="bg-white rounded-[2rem] overflow-hidden">
          {/* Status bar */}
          <div className="bg-brand-blue px-6 py-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-white text-lg">
              🏛️
            </div>
            <div>
              <p className="text-white font-semibold text-sm">
                Parlamentaria
              </p>
              <p className="text-white/60 text-xs">online</p>
            </div>
          </div>

          {/* Messages */}
          <div className="h-[420px] overflow-y-auto p-4 space-y-3 bg-neutral-50">
            {conversation.slice(0, visibleMessages).map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.3 }}
                className={`flex ${
                  msg.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm whitespace-pre-line leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-brand-green text-white rounded-br-md"
                      : "bg-white text-neutral-800 shadow-sm border border-neutral-100 rounded-bl-md"
                  }`}
                >
                  {msg.text}
                </div>
              </motion.div>
            ))}
            {visibleMessages < conversation.length && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="bg-white px-4 py-3 rounded-2xl shadow-sm border border-neutral-100 rounded-bl-md">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-neutral-300 rounded-full animate-bounce" />
                    <span
                      className="w-2 h-2 bg-neutral-300 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    />
                    <span
                      className="w-2 h-2 bg-neutral-300 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Input bar */}
          <div className="px-4 py-3 border-t border-neutral-200 flex items-center gap-2 bg-white">
            <div className="flex-1 bg-neutral-100 rounded-full px-4 py-2 text-sm text-neutral-400">
              Digite uma mensagem...
            </div>
            <div className="w-9 h-9 rounded-full bg-brand-green flex items-center justify-center text-white text-sm">
              ▶
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
