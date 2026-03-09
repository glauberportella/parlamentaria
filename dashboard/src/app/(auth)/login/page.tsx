"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import { Landmark, Loader2, ArrowRight, UserCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const error = searchParams.get("error");
  const [email, setEmail] = useState("");
  const [codigoConvite, setCodigoConvite] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [sent, setSent] = useState(false);
  const [errorMsg, setErrorMsg] = useState(error ? "Erro ao autenticar. Tente novamente." : "");

  useEffect(() => {
    api
      .get<{ enabled: boolean }>("/parlamentar/auth/demo-status", true)
      .then((data) => setDemoEnabled(data.enabled))
      .catch(() => setDemoEnabled(false));
  }, []);

  async function handleDemoLogin() {
    setDemoLoading(true);
    setErrorMsg("");

    try {
      const result = await signIn("demo", { redirect: false });
      if (result?.ok) {
        router.push("/dashboard");
      } else {
        setErrorMsg("Não foi possível entrar no modo demo.");
      }
    } catch {
      setErrorMsg("Não foi possível entrar no modo demo.");
    } finally {
      setDemoLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");

    try {
      await api.post(
        "/parlamentar/auth/login",
        {
          email,
          ...(codigoConvite ? { codigo_convite: codigoConvite } : {}),
        },
        true, // skipAuth
      );
      setSent(true);
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Não foi possível enviar o link de acesso.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Landmark className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>Verifique seu email</CardTitle>
          <CardDescription>
            Enviamos um link de acesso para <strong>{email}</strong>. Clique no
            link para entrar no dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-sm text-muted-foreground">
            O link expira em 15 minutos. Não recebeu?{" "}
            <button
              className="text-primary underline"
              onClick={() => setSent(false)}
            >
              Tentar novamente
            </button>
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Landmark className="h-6 w-6 text-primary" />
        </div>
        <CardTitle className="text-2xl">Parlamentaria</CardTitle>
        <CardDescription>
          Dashboard do Parlamentar — entre com seu email para receber o link de
          acesso.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="deputado@camara.leg.br"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="codigo">
              Código de convite{" "}
              <span className="text-muted-foreground">(primeiro acesso)</span>
            </Label>
            <Input
              id="codigo"
              type="text"
              placeholder="Deixe em branco se já tem conta"
              value={codigoConvite}
              onChange={(e) => setCodigoConvite(e.target.value)}
            />
          </div>

          {errorMsg && (
            <p className="text-sm text-destructive">{errorMsg}</p>
          )}

          <Button type="submit" className="w-full" disabled={loading || demoLoading}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="mr-2 h-4 w-4" />
            )}
            Enviar link de acesso
          </Button>

          {demoEnabled && (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">ou</span>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={loading || demoLoading}
                onClick={handleDemoLogin}
              >
                {demoLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <UserCircle className="mr-2 h-4 w-4" />
                )}
                Entrar como Demo
              </Button>
            </>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Landmark className="h-6 w-6 text-primary" />
            </div>
            <CardTitle className="text-2xl">Parlamentaria</CardTitle>
            <CardDescription>Carregando...</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
