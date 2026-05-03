// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

import cloudflare from '@astrojs/cloudflare';

// https://astro.build/config
export default defineConfig({
  // CRITICAL for SEO: canonical URL used by sitemap, RSS, and SEO component
  site: 'https://drmaxchib.com',

  trailingSlash: 'never',

  integrations: [
    mdx(),
    sitemap({
      filter: (page) => !page.includes('/draft/'),
      changefreq: 'weekly',
      priority: 0.7,
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },

  image: {
    responsiveStyles: true,
  },

  build: {
    inlineStylesheets: 'auto',
  },

  // Prefetch links on hover for instant navigation
  prefetch: {
    prefetchAll: false,
    defaultStrategy: 'hover',
  },

  adapter: cloudflare(),
});