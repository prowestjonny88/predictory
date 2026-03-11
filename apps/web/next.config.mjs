/** @type {import('next').NextConfig} */
const nextConfig = {
  // FastAPI runs on :8000 — CORS is already configured there.
  // All API calls are made client-side via NEXT_PUBLIC_API_URL.
};

export default nextConfig;
