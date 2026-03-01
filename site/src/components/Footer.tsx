import Link from "next/link";
import { Github, Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-neutral-900 text-neutral-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Brand */}
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <span className="text-2xl">🏛️</span>
              <span className="text-xl font-bold text-white">
                Parlamentaria
              </span>
            </Link>
            <p className="text-sm text-neutral-400 leading-relaxed">
              Plataforma open-source de democracia participativa.
              Conectando eleitores e parlamentares através de IA conversacional.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Plataforma</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/#para-eleitor" className="hover:text-white transition-colors">
                  Para Eleitores
                </Link>
              </li>
              <li>
                <Link href="/#para-parlamentar" className="hover:text-white transition-colors">
                  Para Parlamentares
                </Link>
              </li>
              <li>
                <Link href="/como-funciona" className="hover:text-white transition-colors">
                  Como Funciona
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4">Comunidade</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/contribuir" className="hover:text-white transition-colors">
                  Contribuir
                </Link>
              </li>
              <li>
                <Link
                  href="https://github.com/glauberportella/parlamentaria"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors inline-flex items-center gap-1"
                >
                  <Github size={14} /> GitHub
                </Link>
              </li>
              <li>
                <Link
                  href="https://github.com/glauberportella/parlamentaria/discussions"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  Discussões
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4">Dados Públicos</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  href="https://dadosabertos.camara.leg.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  API Câmara dos Deputados
                </Link>
              </li>
              <li>
                <Link
                  href="https://www.camara.leg.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  Câmara dos Deputados
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-8 border-t border-neutral-800 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-neutral-500">
            © {new Date().getFullYear()} Parlamentaria. Código aberto sob licença MIT.
          </p>
          <p className="text-sm text-neutral-500 flex items-center gap-1">
            Feito com <Heart size={14} className="text-red-500" /> pela comunidade
          </p>
        </div>
      </div>
    </footer>
  );
}
