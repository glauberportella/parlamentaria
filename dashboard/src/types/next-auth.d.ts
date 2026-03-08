/** Extend NextAuth types for custom JWT + session fields. */

import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    accessToken?: string;
    refreshToken?: string;
    deputadoId?: number;
    cargo?: string;
  }

  interface Session {
    accessToken: string;
    user: {
      id: string;
      name: string;
      email: string;
      deputadoId: number;
      cargo: string;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    deputadoId?: number;
    cargo?: string;
  }
}
