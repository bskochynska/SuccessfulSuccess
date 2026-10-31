import type { NextConfig } from "next";

const isExport = process.env.NEXT_OUTPUT === "export" || true; // Примусово для S3/CloudFront

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
