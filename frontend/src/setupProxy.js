const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = (app) => {
  // Auth service proxy
  app.use(
    '/api/v1/auth',
    createProxyMiddleware({
      target: 'http://localhost:5001',
      changeOrigin: true,
    })
  );
  
  // Meeting service proxy
  app.use(
    '/api/v1/meetings',
    createProxyMiddleware({
      target: 'http://localhost:5002',
      changeOrigin: true,
    })
  );
  
  // Chat service proxy (for REST endpoints, not Socket.IO)
  app.use(
    '/api/v1/chat',
    createProxyMiddleware({
      target: 'http://localhost:5003',
      changeOrigin: true,
    })
  );
}; 