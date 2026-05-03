# drmaxchib.com

Personal site of Maxwell O. Chibuogwu, PhD — plant pathologist, USDA postdoctoral
fellow, and builder of AI tools for African agriculture.

Built with Astro 6 + Tailwind v4. Deployed on Cloudflare Pages.

## Quick start

```bash
npm install     # one-time
npm run dev     # http://localhost:4321
npm run build   # production build into ./dist
npm run preview # preview the production build locally
```

## Adding content

- **Blog post** — drop a `.md` or `.mdx` file in `src/content/blog/`.
- **Project** — drop a `.md` or `.mdx` file in `src/content/projects/`.

Both have type-safe schemas in `src/content.config.ts` — the build will fail
with a helpful error if a required frontmatter field is missing.

## Deployment

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for the full step-by-step
walkthrough of deploying to Cloudflare Pages and connecting `drmaxchib.com`.

## Architecture notes

- **`src/consts.ts`** — single source of truth for site title, nav, social
  links. Change once, propagates everywhere.
- **`src/components/BaseHead.astro`** — handles every meta tag, OG card,
  Twitter card, JSON-LD structured data, and theme initialization. Pages don't
  worry about SEO — they just pass `title` and `description` to the layout.
- **`src/styles/global.css`** — Tailwind v4 with custom design tokens
  (forest green + cream, dark mode via `[data-theme="dark"]`). All colors are
  CSS custom properties — change them in one place to re-theme the entire site.
- **No bullet-point dumping in content** — write in prose. The styling
  rewards real writing, not skimmable lists.

## License

Code: MIT. Content: © Maxwell O. Chibuogwu.
