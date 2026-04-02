---
name: build-website
description: Build premium static websites using the PRISM framework (6-phase process). Use when asked to build, design, or create a website or landing page. For interactive apps with databases and auth, use build-app instead.
model: opus
context: fork
user-invocable: true
---

# Build Website — PRISM Framework

Build premium static websites that look custom-designed, not template-generated.

## When to Use

- Landing pages
- Portfolio sites
- Business websites
- Marketing pages
- Product launch pages

**NOT for:** Apps with databases, user auth, dashboards → use `build-app` instead.

## The PRISM Framework

### Phase 1: Position

Establish message, audience, and goal clarity before touching code.

**Ask the user:**
1. What is this website for? (product, service, portfolio, event)
2. Who is the primary audience?
3. What's the single most important action a visitor should take? (CTA)
4. What tone should it convey? (professional, creative, technical, playful)
5. Are there any websites you admire or want to reference?

**Read:** `context/my-business.md` and `context/my-voice.md` for brand context.

**Output:** Clear creative brief with: audience, goal, CTA, tone, references.

### Phase 2: Rough

Structure and hierarchy planning. No code yet.

1. Define the page sections (hero, features, testimonials, CTA, footer)
2. Write the copy for each section (headlines, body, CTAs)
3. Plan the visual hierarchy (what draws the eye first, second, third)
4. Map the user journey (land → scan → engage → convert)

**Output:** Section-by-section wireframe in markdown with copy.

### Phase 3: Identity

Design system definition.

1. **Typography** — Choose 2 fonts: heading (personality) + body (readability)
2. **Colors** — Primary, secondary, accent. Dark/light modes.
3. **Spacing** — Consistent scale (4px base, 8, 16, 24, 32, 48, 64, 96)
4. **Components** — Button styles, card styles, section patterns
5. **Design tokens** — Define as CSS custom properties

**Output:** Design system as CSS variables and component specifications.

### Phase 4: Sensation

The "wow" layer that separates premium from template.

1. **Micro-interactions** — Button hovers, scroll reveals, focus states
2. **Scroll animations** — GSAP ScrollTrigger for section entrances
3. **Visual effects** — Glassmorphism, gradients, grain textures, shadows
4. **Typography animation** — Text reveals, counter animations
5. **Performance budget** — Keep FCP under 1.5s, LCP under 2.5s

**Rules:**
- Every animation must serve a purpose (guide attention, provide feedback)
- Never animate just because you can
- Always provide `prefers-reduced-motion` fallback

### Phase 5: Make

Build the website.

**Stack:**
- Astro (static site generator)
- Tailwind CSS (utility-first styling)
- GSAP (animations)
- Vanilla JS (no heavy frameworks for static sites)

**Build order:**
1. Scaffold Astro project
2. Implement design tokens as Tailwind config
3. Build sections top-to-bottom (hero first)
4. Add interactions and animations
5. Responsive design (mobile → tablet → desktop)
6. Dark mode (if specified)

### Phase +Measure

Quality assurance.

1. **Performance** — Lighthouse score > 90 on all metrics
2. **Accessibility** — WCAG 2.1 AA compliance, keyboard navigation, screen reader testing
3. **SEO** — Meta tags, Open Graph, structured data, sitemap
4. **Responsive** — Test at 320px, 768px, 1024px, 1440px
5. **Cross-browser** — Chrome, Firefox, Safari minimum
6. **CTA effectiveness** — Is the primary action obvious and easy?

## Rules

- Never use stock placeholder content — write real copy or ask for it
- Every section must earn its place — if it doesn't serve the user journey, cut it
- Mobile-first responsive design
- Performance is non-negotiable — no heavy libraries for simple effects
- Prefer CSS animations over JS where possible (GPU-accelerated)
