/** @type {import('next').NextConfig} */
const nextConfig = {
  // FastAPI runs on :8000 — CORS is already configured there.
  // All API calls are made client-side via NEXT_PUBLIC_API_URL.
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
    ],
  },
};

export default nextConfig;
