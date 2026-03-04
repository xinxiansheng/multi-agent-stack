#!/usr/bin/env node

const http = require('http');
const https = require('https');
const { URL } = require('url');

const PORT = 18820;
const TARGET = 'https://newapi.sms88.info';

const server = http.createServer((req, res) => {
  const targetUrl = new URL(req.url, TARGET);

  const options = {
    hostname: targetUrl.hostname,
    port: targetUrl.port || 443,
    path: targetUrl.pathname + targetUrl.search,
    method: req.method,
    headers: {
      ...req.headers,
      host: targetUrl.hostname,
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
  };

  const proxyReq = https.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    console.error('Proxy error:', err);
    res.writeHead(502);
    res.end('Bad Gateway');
  });

  req.pipe(proxyReq);
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`NewAPI proxy listening on http://127.0.0.1:${PORT}`);
  console.log(`Forwarding to ${TARGET}`);
});
