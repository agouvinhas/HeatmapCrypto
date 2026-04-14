# Crypto Board — Heatmap em Tempo Real

Aplicação web de heatmap de criptomoedas do **Mercado Bitcoin**, exibindo preços em BRL e variações 24h em um treemap visual. Ideal para exibição em tela de escritório ou TV em modo kiosk.

---

## Como funciona

- Busca todos os símbolos cripto do Mercado Bitcoin (filtra Renda Fixa Digital automaticamente)
- Exibe blocos coloridos proporcionais ao volume financeiro 24h (R$)
- Atualiza automaticamente a cada **30 segundos** sem recarregar a página
- Agrupa por categoria: **Large Cap** (BTC, ETH, BNB, SOL, XRP) · **Mid Cap** (> R$ 100k/24h) · **Small Cap**

### Escala de cores

| Cor | Variação 24h |
|-----|-------------|
| Verde escuro | > +5% |
| Verde médio | 0% a +5% |
| Vermelho médio | -5% a 0% |
| Vermelho escuro | < -5% |
| Cinza | Dados indisponíveis |

---

## Opção 1 — Abrir direto no Chrome (sem instalar nada)

Desativa as restrições de CORS do browser para acesso local a arquivos:

```bash
google-chrome --kiosk --disable-web-security --user-data-dir=/tmp/chrome-kiosk index.html
```

No macOS, substitua `google-chrome` pelo caminho completo:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --kiosk --disable-web-security --user-data-dir=/tmp/chrome-kiosk index.html
```

---

## Opção 2 — Servidor Node.js com proxy CORS (recomendado)

Não requer nenhum `npm install` — usa apenas módulos nativos do Node.js (v14+).

### 1. Iniciar o servidor

```bash
node server.js
```

Saída esperada:

```
  ╔════════════════════════════════════════╗
  ║   Crypto Board — Proxy CORS ativo      ║
  ║   http://localhost:3000                ║
  ╚════════════════════════════════════════╝
```

### 2. Abrir no browser

```bash
# Browser normal
open http://localhost:3000

# Modo kiosk (TV / escritório)
google-chrome --kiosk http://localhost:3000
```

No macOS:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --kiosk http://localhost:3000
```

### Porta alternativa

```bash
PORT=8080 node server.js
```

---

## Sair do modo kiosk

Pressione `F11` ou `Alt+F4` (Windows/Linux) · `Cmd+Q` (macOS).

---

## Comportamento esperado

Ao abrir a aplicação:

1. Tela escura com indicador laranja piscante e mensagem "Buscando dados…"
2. Após ~5–15 segundos, o treemap aparece preenchendo toda a tela
3. **BTC** ocupa o maior bloco (maior volume financeiro do mercado)
4. Cada bloco exibe: símbolo em destaque, preço em R$, variação % com seta ▲▼
5. Blocos menores exibem apenas símbolo + variação
6. No canto superior direito: horário da última atualização + indicador verde (● ok) ou vermelho (● erro)
7. A cada 30s os dados são atualizados silenciosamente (sem flash ou reload)

---

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `index.html` | Aplicação completa (HTML + CSS + JS, zero dependências de build) |
| `server.js` | Proxy CORS em Node.js puro (sem npm install) |
| `README.md` | Esta documentação |

---

## Requisitos

- **Browser**: Chrome / Edge / Firefox moderno
- **Node.js**: v14 ou superior (apenas para `server.js`)
- **Internet**: acesso à API pública `api.mercadobitcoin.net`
