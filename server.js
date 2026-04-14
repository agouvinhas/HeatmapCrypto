#!/usr/bin/env node
/**
 * server.js — Proxy CORS para o Crypto Board
 *
 * Resolve bloqueios de CORS ao fazer chamadas à API do Mercado Bitcoin
 * diretamente do browser. Este servidor:
 *  - Serve o index.html na raiz (/)
 *  - Faz proxy de /api/v4/* → https://api.mercadobitcoin.net/api/v4/*
 *
 * Não requer nenhuma dependência npm — usa apenas módulos nativos do Node.js.
 *
 * Uso:
 *   node server.js
 *   # Acesse http://localhost:3000
 *   # Modo kiosk: google-chrome --kiosk http://localhost:3000
 */

'use strict';

const http  = require('http');
const https = require('https');
const fs    = require('fs');
const path  = require('path');
const url   = require('url');

const PORT    = parseInt(process.env.PORT || '3000', 10);
const MB_HOST = 'api.mercadobitcoin.net';
const MB_BASE = `/api/v4`;
const STATIC  = path.join(__dirname, 'index.html');

// ── MIME types simples ────────────────────────────────────────────────────────
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
};

// ── Cabeçalhos CORS ───────────────────────────────────────────────────────────
function setCORSHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin',  '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// ── Proxy → Mercado Bitcoin ───────────────────────────────────────────────────
function proxyToMB(req, res, mbPath) {
  const options = {
    hostname: MB_HOST,
    port:     443,
    path:     mbPath,
    method:   'GET',
    headers: {
      'User-Agent': 'CryptoBoard-Proxy/1.0',
      'Accept':     'application/json',
    },
    timeout: 8000,
  };

  const proxyReq = https.request(options, (mbRes) => {
    setCORSHeaders(res);
    res.writeHead(mbRes.statusCode, {
      'Content-Type': mbRes.headers['content-type'] || 'application/json',
    });
    mbRes.pipe(res, { end: true });
  });

  proxyReq.on('timeout', () => {
    proxyReq.destroy();
    if (!res.headersSent) {
      setCORSHeaders(res);
      res.writeHead(504);
      res.end(JSON.stringify({ error: 'Gateway timeout' }));
    }
  });

  proxyReq.on('error', (err) => {
    console.error(`[proxy] Erro ao conectar ao MB API: ${err.message}`);
    if (!res.headersSent) {
      setCORSHeaders(res);
      res.writeHead(502);
      res.end(JSON.stringify({ error: 'Bad gateway', detail: err.message }));
    }
  });

  proxyReq.end();
}

// ── Servidor HTTP ─────────────────────────────────────────────────────────────
const server = http.createServer((req, res) => {
  const parsed   = url.parse(req.url);
  const pathname = parsed.pathname;

  // Preflight CORS
  if (req.method === 'OPTIONS') {
    setCORSHeaders(res);
    res.writeHead(204);
    res.end();
    return;
  }

  // Proxy da API do MB
  if (pathname.startsWith('/api/v4/')) {
    const mbPath = pathname + (parsed.search || '');
    console.log(`[proxy] GET ${mbPath}`);
    proxyToMB(req, res, mbPath);
    return;
  }

  // Proxy genérico para RSS/JSON externos — com redirect-following (max 5 hops)
  if (pathname === '/proxy') {
    const urlParam = new URLSearchParams(parsed.search || '').get('url');
    if (!urlParam) {
      setCORSHeaders(res); res.writeHead(400);
      res.end('{"error":"Missing url"}'); return;
    }
    let startUrl;
    try { startUrl = new URL(urlParam); } catch {
      setCORSHeaders(res); res.writeHead(400);
      res.end('{"error":"Invalid URL"}'); return;
    }

    function doRequest(targetUrl, hopsLeft) {
      const lib  = targetUrl.protocol === 'https:' ? https : http;
      const port = targetUrl.protocol === 'https:' ? 443 : 80;
      const req  = lib.request({
        hostname: targetUrl.hostname,
        port,
        path:    (targetUrl.pathname || '/') + (targetUrl.search || ''),
        method:  'GET',
        headers: { 'User-Agent': 'CryptoBoard-Proxy/1.0', 'Accept': '*/*' },
        timeout: 9000,
        rejectUnauthorized: false,
      }, (remote) => {
        const loc = remote.headers['location'];
        if ([301,302,303,307,308].includes(remote.statusCode) && loc && hopsLeft > 0) {
          remote.resume(); // discard body
          try { doRequest(new URL(loc, targetUrl.href), hopsLeft - 1); }
          catch { setCORSHeaders(res); res.writeHead(502); res.end('{"error":"bad redirect"}'); }
          return;
        }
        setCORSHeaders(res);
        res.writeHead(remote.statusCode, {
          'Content-Type': remote.headers['content-type'] || 'text/plain',
        });
        remote.pipe(res, { end: true });
      });
      req.on('timeout', () => {
        req.destroy();
        if (!res.headersSent) { setCORSHeaders(res); res.writeHead(504); res.end('{"error":"timeout"}'); }
      });
      req.on('error', (err) => {
        if (!res.headersSent) { setCORSHeaders(res); res.writeHead(502); res.end(`{"error":"${err.message}"}`); }
      });
      req.end();
    }
    doRequest(startUrl, 5);
    return;
  }

  // Servir index.html na raiz
  if (pathname === '/' || pathname === '/index.html') {
    fs.readFile(STATIC, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('index.html não encontrado — certifique-se de rodar node server.js na mesma pasta.');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(data);
    });
    return;
  }

  // Outros arquivos estáticos (ícones, etc.)
  const filePath = path.join(__dirname, pathname);
  // Impede path traversal
  if (!filePath.startsWith(__dirname)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    const ext  = path.extname(filePath);
    const mime = MIME[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log('');
  console.log('  ╔════════════════════════════════════════╗');
  console.log('  ║   Crypto Board — Proxy CORS ativo      ║');
  console.log(`  ║   http://localhost:${PORT}                  ║`);
  console.log('  ╚════════════════════════════════════════╝');
  console.log('');
  console.log('  Modo kiosk:');
  console.log(`  google-chrome --kiosk http://localhost:${PORT}`);
  console.log('');
  console.log('  Pressione Ctrl+C para parar.');
  console.log('');
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\nErro: porta ${PORT} já está em uso.`);
    console.error(`Tente: PORT=3001 node server.js\n`);
  } else {
    console.error('Erro no servidor:', err);
  }
  process.exit(1);
});
