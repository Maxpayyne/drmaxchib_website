import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * BLOG collection
 * Frontmatter schema for posts. All blog posts in src/content/blog/*.{md,mdx}
 * must conform to this shape, which Astro will type-check at build time.
 */
const blog = defineCollection({
  loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
  schema: ({ image }) =>
    z.object({
      // Core SEO fields
      title: z.string().max(70, 'Keep titles under 70 chars for SEO'),
      description: z.string().min(50).max(160, 'Meta descriptions ideally 150-160 chars'),

      // Authorship & dates
      author: z.string().default('Maxwell O. Chibuogwu'),
      pubDate: z.coerce.date(),
      updatedDate: z.coerce.date().optional(),

      // Discovery & taxonomy
      tags: z.array(z.string()).default([]),
      category: z
        .enum(['nigeria', 'science', 'building', 'general'])
        .default('general'),

      // Visuals
      heroImage: image().optional(),
      heroImageAlt: z.string().optional(),
      ogImage: z.string().optional(), // Override the auto-generated OG image

      // Status flags
      draft: z.boolean().default(false),
      featured: z.boolean().default(false),

      // Reading metadata (auto-calculated would be ideal; manual override here)
      readingTime: z.string().optional(),

      // Canonical URL — set if cross-posted to Medium/Substack/etc.
      canonicalURL: z.string().url().optional(),
    }),
});

/**
 * PROJECTS collection
 * Each project becomes a page at /projects/[slug] — better for SEO than
 * just linking out to GitHub. The repo URL is stored as a field.
 */
const projects = defineCollection({
  loader: glob({ base: './src/content/projects', pattern: '**/*.{md,mdx}' }),
  schema: ({ image }) =>
    z.object({
      title: z.string().max(70),
      description: z.string().min(50).max(160),
      pubDate: z.coerce.date(),
      updatedDate: z.coerce.date().optional(),

      // Project-specific
      category: z.enum(['research', 'civic', 'pet']).default('research'),
      status: z
        .enum(['concept', 'in-progress', 'shipped', 'archived'])
        .default('in-progress'),
      stack: z.array(z.string()).default([]),
      tags: z.array(z.string()).default([]),

      // External links
      repoUrl: z.string().url().optional(),
      demoUrl: z.string().url().optional(),
      paperUrl: z.string().url().optional(),

      // Visuals
      heroImage: image().optional(),
      heroImageAlt: z.string().optional(),
      ogImage: z.string().optional(),

      // Display
      featured: z.boolean().default(false),
      draft: z.boolean().default(false),
      order: z.number().default(0), // Lower = shown first
    }),
});

export const collections = { blog, projects };
