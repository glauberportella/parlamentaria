"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X } from "lucide-react";

const navLinks = [
  { href: "/#para-eleitor", label: "Para Eleitores" },
  { href: "/#para-parlamentar", label: "Para Parlamentares" },
  { href: "/como-funciona", label: "Como Funciona" },
  { href: "/contribuir", label: "Contribuir" },
];

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-md border-b border-neutral-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🏛️</span>
            <span className="text-xl font-bold gradient-text">
              Parlamentaria
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-neutral-600 hover:text-brand-blue transition-colors"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="https://t.me/parlamentariasocial_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-green text-white text-sm font-semibold rounded-full hover:bg-brand-green-dark transition-colors shadow-sm"
            >
              💬 Começar no Telegram
              <span className="text-[10px] font-normal opacity-75 ml-1">(em breve)</span>
            </Link>
          </nav>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 text-neutral-600"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-neutral-200">
          <nav className="flex flex-col px-4 py-4 gap-3">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="text-base font-medium text-neutral-700 hover:text-brand-blue py-2"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="https://t.me/parlamentariasocial_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-brand-green text-white font-semibold rounded-full hover:bg-brand-green-dark transition-colors mt-2"
            >
              💬 Começar no Telegram
              <span className="text-[10px] font-normal opacity-75 ml-1">(em breve)</span>
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
