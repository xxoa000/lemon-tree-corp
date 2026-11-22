const backend = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export default {
  experimental: { proxyTimeout: 130_000 },
  async rewrites() {
    return [
      { source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` },
    ];
  },
};
