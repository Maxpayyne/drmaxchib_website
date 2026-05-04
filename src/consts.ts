/**
 * Site-wide configuration. Change values here, they propagate everywhere.
 */

export const SITE = {
  title: 'Maxwell O. Chibuogwu, PhD',
  shortTitle: 'Dr. Maxwell O. Chibuogwu',
  tagline: 'Plant pathologist building AI tools for African agriculture.',
  description:
    'Maxwell O. Chibuogwu, PhD — USDA postdoctoral fellow, plant pathologist, and founder of RethinkNaija. Writing on agricultural science, AI for Africa, and civic technology.',
  url: 'https://drmaxchib.com',
  author: 'Maxwell O. Chibuogwu',
  authorTitle: 'PhD, Plant Pathology',
  locale: 'en_US',
  twitterHandle: '@drmaxchib', // Add @handle when active
  // Default Open Graph image (1200x630 PNG, lives in /public/og-default.png)
  defaultOgImage: '/og-default.png',
} as const;

export const NAV: { name: string; href: string }[] = [
  { name: 'About', href: '/about' },
  { name: 'Research', href: '/research' },
  { name: 'Projects', href: '/projects' },
  { name: 'Skills', href: '/skills' },
  { name: 'Writing', href: '/blog' },
];

export const SOCIAL = {
  linkedin: 'https://www.linkedin.com/in/maxwell-o-chi/',
  github: 'https://github.com/', // Update with your username
  email: 'info@drmaxchib.com', // Set up via Cloudflare Email Routing
  scholar: 'https://scholar.google.com/citations?hl=en&user=m2kFng0AAAAJ', // Add Google Scholar profile when ready
  orcid: 'https://orcid.org/my-orcid?orcid=0000-0002-3917-5364', // Add ORCID iD when ready
} as const;

/** Categories for the writing/blog section */
export const BLOG_CATEGORIES = {
  nigeria: {
    slug: 'nigeria',
    name: 'On Nigeria',
    description:
      'Notes on Nigerian institutions, civic tech, and what it will take to build better.',
  },
  science: {
    slug: 'science',
    name: 'Science & Research',
    description:
      'Plant pathology, mycotoxins, and the practice of agricultural research.',
  },
  building: {
    slug: 'building',
    name: 'Building',
    description:
      'AI-assisted development, tools for Africa, and lessons from shipping.',
  },
  general: {
    slug: 'general',
    name: 'General',
    description: 'Essays on craft, ideas, and other interests.',
  },
} as const;

export type BlogCategory = keyof typeof BLOG_CATEGORIES;

/** Project categories — kept flat for clean URLs */
export const PROJECT_CATEGORIES = {
  research: { slug: 'research', name: 'Research' },
  civic: { slug: 'civic', name: 'Civic Tech' },
  pet: { slug: 'pet', name: 'Pet Projects' },
} as const;

export type ProjectCategory = keyof typeof PROJECT_CATEGORIES;
