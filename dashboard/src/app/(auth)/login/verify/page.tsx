"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import { Landmark, Loader2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }

    signIn("magic-link", {
      token,
      redirect: false,
    }).then((result) => {
      if (result?.ok) {
        setStatus("success");
        setTimeout(() => router.push("/dashboard"), 1500);
      } else {
        setStatus("error");
      }
    });
  }, [token, router]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Landmark className="h-6 w-6 text-primary" />
        </div>
        <CardTitle>Verificando acesso</CardTitle>
        <CardDescription>
          {status === "loading" && "Validando seu link de acesso..."}
          {status === "success" && "Acesso confirmado! Redirecionando..."}
          {status === "error" && "Link inválido ou expirado."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        {status === "loading" && (
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        )}
        {status === "success" && (
          <CheckCircle className="h-8 w-8 text-green-600" />
        )}
        {status === "error" && (
          <>
            <XCircle className="h-8 w-8 text-destructive" />
            <Button variant="outline" onClick={() => router.push("/login")}>
              Voltar ao login
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Landmark className="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Verificando acesso</CardTitle>
            <CardDescription>Carregando...</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}