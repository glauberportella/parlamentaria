"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import {
  User,
  Bell,
  Palette,
  Save,
  X,
  Plus,
  Loader2,
  Sun,
  Moon,
  Monitor,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useProfile, useUpdateProfile } from "@/hooks/use-profile";

/* ── Theme selector ────────────────────────── */
function ThemeSelector() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <Skeleton className="h-24 w-full" />;
  }

  const options = [
    { value: "light", label: "Claro", icon: Sun },
    { value: "dark", label: "Escuro", icon: Moon },
    { value: "system", label: "Sistema", icon: Monitor },
  ] as const;

  return (
    <div className="grid grid-cols-3 gap-3">
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors ${
            theme === value
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50"
          }`}
        >
          <Icon className="h-5 w-5" />
          <span className="text-sm font-medium">{label}</span>
        </button>
      ))}
    </div>
  );
}

/* ── Tags input ────────────────────────────── */
function TagsInput({
  tags,
  onChange,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
}) {
  const [input, setInput] = useState("");

  function addTag() {
    const value = input.trim().toLowerCase();
    if (value && !tags.includes(value)) {
      onChange([...tags, value]);
    }
    setInput("");
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          placeholder="Adicionar tema (ex: saúde, educação)…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
          className="flex-1"
        />
        <Button type="button" variant="secondary" size="sm" onClick={addTag}>
          <Plus className="mr-1 h-4 w-4" />
          Adicionar
        </Button>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 px-2 py-1">
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="ml-0.5 rounded-full hover:bg-muted-foreground/20"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Loading skeleton ──────────────────────── */
function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-80" />
      </div>
      <Skeleton className="h-[280px]" />
      <Skeleton className="h-[200px]" />
      <Skeleton className="h-[160px]" />
    </div>
  );
}

/* ── Page ────────────────────────────────────── */
export default function ConfiguracoesPage() {
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();

  const [nome, setNome] = useState("");
  const [cargo, setCargo] = useState("");
  const [temas, setTemas] = useState<string[]>([]);
  const [notificacoes, setNotificacoes] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);

  // Populate form when profile loads
  useEffect(() => {
    if (profile) {
      setNome(profile.nome ?? "");
      setCargo(profile.cargo ?? "");
      setTemas(profile.temas_acompanhados ?? []);
      setNotificacoes(profile.notificacoes_email);
      setDirty(false);
    }
  }, [profile]);

  // Track changes
  useEffect(() => {
    if (!profile) return;
    const changed =
      nome !== (profile.nome ?? "") ||
      cargo !== (profile.cargo ?? "") ||
      notificacoes !== profile.notificacoes_email ||
      JSON.stringify(temas) !== JSON.stringify(profile.temas_acompanhados ?? []);
    setDirty(changed);
    if (changed) setSaved(false);
  }, [nome, cargo, temas, notificacoes, profile]);

  async function handleSave() {
    await updateProfile.mutateAsync({
      nome: nome || undefined,
      cargo: cargo || undefined,
      temas_acompanhados: temas,
      notificacoes_email: notificacoes,
    });
    setDirty(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  if (isLoading) return <PageSkeleton />;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Configurações</h1>
        <p className="text-muted-foreground">
          Gerencie seu perfil, preferências e notificações.
        </p>
      </div>

      {/* Profile section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="h-4 w-4" />
            Perfil
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="nome">Nome</Label>
              <Input
                id="nome"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Seu nome"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cargo">Cargo</Label>
              <Input
                id="cargo"
                value={cargo}
                onChange={(e) => setCargo(e.target.value)}
                placeholder="Ex: Deputado Federal"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>E-mail</Label>
            <Input value={profile?.email ?? ""} disabled className="bg-muted" />
            <p className="text-xs text-muted-foreground">
              O e-mail não pode ser alterado.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Temas section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4" />
            Temas Acompanhados
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Escolha temas legislativos de seu interesse para acompanhar no dashboard.
          </p>
          <TagsInput tags={temas} onChange={setTemas} />

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Notificações por e-mail</Label>
              <p className="text-xs text-muted-foreground">
                Receba alertas quando houver novidades nos temas acompanhados.
              </p>
            </div>
            <Switch
              checked={notificacoes}
              onCheckedChange={setNotificacoes}
            />
          </div>
        </CardContent>
      </Card>

      {/* Theme section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette className="h-4 w-4" />
            Aparência
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ThemeSelector />
        </CardContent>
      </Card>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={!dirty || updateProfile.isPending}>
          {updateProfile.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Salvar alterações
        </Button>
        {saved && (
          <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            Salvo com sucesso!
          </span>
        )}
        {updateProfile.isError && (
          <span className="text-sm text-destructive">
            Erro ao salvar. Tente novamente.
          </span>
        )}
      </div>
    </div>
  );
}
