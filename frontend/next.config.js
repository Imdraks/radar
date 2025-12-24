/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    // In Docker production: use internal service name 'backend:8000'
    // In development: use localhost:8000
    const backendUrl = process.env.INTERNAL_API_URL || 'http://backend:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/ws/:path*',
        destination: `${backendUrl}/ws/:path*`,
      },
    ];
  },
  // Suppress hydration warnings in production
  reactStrictMode: process.env.NODE_ENV !== 'production',
};

module.exports = nextConfig;
