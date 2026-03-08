/** NextAuth.js v5 configuration — Magic Link + JWT auth with backend. */

import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import type { NextAuthConfig } from "next-auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const authConfig: NextAuthConfig = {
  providers: [
    Credentials({
      id: "magic-link",
      name: "Magic Link",
      credentials: {
        token: { label: "Token", type: "text" },
      },
      async authorize(credentials) {
        if (!credentials?.token) return null;

        try {
          const res = await fetch(`${API_URL}/parlamentar/auth/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: credentials.token }),
          });

          if (!res.ok) return null;

          const data = await res.json();
          return {
            id: data.user.id,
            name: data.user.nome,
            email: data.user.email,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            deputadoId: data.user.deputado_id,
            cargo: data.user.cargo,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.deputadoId = user.deputadoId;
        token.cargo = user.cargo;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.user.id = token.sub!;
      session.user.deputadoId = token.deputadoId as number;
      session.user.cargo = token.cargo as string;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // 7 days
  },
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
