# Dashboard — Backlog de Melhorias

> Itens identificados durante a implementação do Dashboard Parlamentar (ADR-001)
> que foram priorizados para implementação futura.

---

## 1. Exportação PDF

**Prioridade**: Média  
**Complexidade**: Média

Implementar exportação de relatórios em PDF a partir das páginas do dashboard.

### Abordagem sugerida
- Usar **`@react-pdf/renderer`** (client-side) ou **WeasyPrint** (server-side via API)
- Relatórios candidatos:
  - Resumo de votação popular (panorama + gráficos)
  - Comparativo voto popular vs real (com gráfico de evolução)
  - Relatório do mandato (alinhamento, votos divergentes/alinhados)
- Botão "Exportar PDF" ao lado do botão CSV já existente
- Template com cabeçalho Parlamentaria, data de geração, filtros aplicados

### Critérios de aceite
- [ ] Botão de exportação PDF nas páginas: Votação Popular, Comparativos, Meu Mandato
- [ ] PDF inclui gráficos renderizados (como imagem ou SVG)
- [ ] PDF inclui metadados (data, filtros, período)
- [ ] Funciona em todos os navegadores modernos

---

## 2. Testes E2E com Playwright

**Prioridade**: Alta  
**Complexidade**: Média-Alta

Implementar testes end-to-end cobrindo os fluxos críticos do dashboard.

### Fluxos a cobrir
1. **Login → Dashboard** — Autenticação e redirect para `/dashboard`
2. **Dashboard → Proposições** — Navegação, tabela com paginação
3. **Votação Popular** — Visualização de gráficos, troca de tabs, navegação para sub-páginas
4. **Comparativos** — Filtros, tabela, paginação, evolução
5. **Meu Mandato** — Card do deputado, KPIs, gráfico de alinhamento
6. **Configurações** — Alteração de tema (dark/light), salvamento de preferências
7. **Exportação CSV** — Download funcional em cada página que oferece export

### Setup sugerido
```bash
npm install -D @playwright/test
npx playwright install
```

### Configuração CI
```yaml
# .github/workflows/e2e.yml
- name: Run Playwright tests
  run: npx playwright test
  env:
    BASE_URL: http://localhost:3000
```

### Critérios de aceite
- [ ] Suite Playwright configurada com fixtures de auth
- [ ] Mínimo 7 cenários E2E (1 por fluxo acima)
- [ ] CI pipeline executa testes E2E em PR
- [ ] Screenshots de falha salvos como artefatos
- [ ] Testes usam mock de API (MSW ou intercept Playwright)

---

## 3. Real-time com WebSockets / SSE

**Prioridade**: Baixa  
**Complexidade**: Alta

Substituir o polling atual (TanStack Query `refetchInterval: 120s`) por atualizações em tempo real.

### Estado atual
- Polling a cada 2 minutos em todas as queries
- Funciona bem para o volume atual de dados
- Sem necessidade imediata de real-time

### Abordagem sugerida
- **SSE (Server-Sent Events)** no backend FastAPI — mais simples que WebSockets
- Endpoint: `GET /parlamentar/events/stream` com `text/event-stream`
- Eventos: `nova_proposicao`, `voto_registrado`, `comparativo_gerado`
- No frontend: `EventSource` API + invalidação de queries TanStack via `queryClient.invalidateQueries()`
- Fallback: manter polling como fallback se SSE desconectar

### Critérios de aceite
- [ ] Endpoint SSE no backend com eventos tipados
- [ ] Hook `useSSE()` no frontend que invalida queries relevantes
- [ ] Fallback automático para polling se SSE não disponível
- [ ] Reconexão automática com backoff exponencial
- [ ] Sem impacto em performance quando muitos clientes conectados

---

## 4. Prefetch em Hover/Focus de Links

**Prioridade**: Baixa  
**Complexidade**: Baixa

Prefetch de dados quando o usuário passa o mouse sobre links de navegação na sidebar.

### Abordagem sugerida
- Usar `queryClient.prefetchQuery()` do TanStack Query
- No componente `AppSidebar`, adicionar `onMouseEnter` nos links
- Prefetch das queries principais de cada página:
  - `/proposicoes` → prefetch lista de proposições
  - `/votacao-popular` → prefetch votos por tema, por UF
  - `/comparativos` → prefetch lista de comparativos
  - `/meu-mandato` → prefetch resumo do mandato
- Debounce de 200ms para evitar prefetch em mouse passando rápido

### Critérios de aceite
- [ ] Prefetch implementado nos links da sidebar
- [ ] Debounce para evitar requests desnecessários
- [ ] Dados aparecem instantaneamente ao navegar após hover
- [ ] Sem impacto negativo em rate limiting da API

---

## Notas

- A ordem de prioridade sugerida é: **2 (E2E)** > **1 (PDF)** > **4 (Prefetch)** > **3 (Real-time)**
- Os testes E2E são os mais valiosos para garantir estabilidade em futuras mudanças
- Real-time pode ser adiado indefinidamente — polling atende bem o uso atual
