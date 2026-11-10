/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so the backend can serve the built site from
  // frontend/out (see backend/Dockerfile and app/main.py). All pages are
  // client components that fetch the API at runtime.
  output: "export",
  trailingSlash: true,
};
module.exports = nextConfig;
