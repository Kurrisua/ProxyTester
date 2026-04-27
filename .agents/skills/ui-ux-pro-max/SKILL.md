---
name: ui-ux-pro-max
description: UI/UX design intelligence for building, redesigning, reviewing, and polishing web and mobile interfaces. Use when creating or improving front-end UI for pages, dashboards, apps, components, charts, forms, navigation, responsive layouts, accessibility, typography, color systems, motion, visual hierarchy, design systems, shadcn/ui, Tailwind, React, Next.js, Vue, Svelte, HTML/CSS, React Native, Flutter, SwiftUI, or when the user asks for beautiful, professional, modern, high-quality UI/UX design.
---

# UI/UX Pro Max

Use this skill to turn vague UI requests into a concrete design direction, then implement or review the interface with strong visual quality, accessibility, and interaction polish.

## Core Workflow

1. Identify the product type, target user, platform, stack, density, tone, and any brand constraints.
2. Resolve the skill directory from the loaded `SKILL.md`, then generate a design system recommendation before making broad UI decisions:

```bash
python "<skill-dir>/scripts/search.py" "<product type> <industry> <tone> <stack>" --design-system -p "<Project Name>"
```

3. Use targeted searches when the work needs a sharper answer:

```bash
python "<skill-dir>/scripts/search.py" "<query>" --domain <domain>
python "<skill-dir>/scripts/search.py" "<query>" --stack <stack>
```

4. Apply the results in code using the repo's existing framework, component patterns, tokens, and styling conventions.
5. Verify the UI on small mobile and desktop widths. Check accessibility, contrast, touch targets, responsive behavior, layout stability, loading states, and reduced motion.

## Search Domains

- `product`: product archetypes and screen patterns.
- `style`: visual styles, effects, mood, and anti-patterns.
- `color`: palette choices by product category and tone.
- `typography`: font pairing and type hierarchy.
- `landing`: landing page structure and conversion sections.
- `chart`: chart type and data visualization guidance.
- `ux`: accessibility, interaction, forms, motion, layout, feedback, and mobile usability.
- `react`: React and Next.js performance and implementation patterns.
- `web`: app interface guidance for touch, safe areas, accessibility labels, and platform conventions.
- `prompt`: concise style keywords and image/UI generation prompts.
- `google-fonts`: individual font lookup and pairing support.

## Stack Searches

Use `--stack` when implementation details matter. Available stack CSVs may include `react`, `nextjs`, `vue`, `svelte`, `html-tailwind`, `shadcn`, `astro`, `nuxtjs`, `nuxt-ui`, `react-native`, `flutter`, `swiftui`, and `jetpack-compose`.

Example:

```bash
python "<skill-dir>/scripts/search.py" "dashboard cards forms responsive accessibility" --stack react
```

## Persistent Design Systems

When a project will have multiple screens, persist the design system:

```bash
python "<skill-dir>/scripts/search.py" "<query>" --design-system --persist -p "<Project Name>"
```

For page-specific overrides:

```bash
python "<skill-dir>/scripts/search.py" "<query>" --design-system --persist -p "<Project Name>" --page "<Page Name>"
```

When continuing work later, read `design-system/<project-slug>/MASTER.md` first, then read `design-system/<project-slug>/pages/<page-name>.md` if it exists.

## Design Standards

- Start the actual product experience immediately for apps, tools, games, dashboards, and utilities. Do not default to a marketing landing page.
- Use images or meaningful visual assets for websites unless the task is purely component-level or the repo's design language clearly avoids imagery.
- Keep layouts stable as state changes. Define dimensions, grid tracks, aspect ratios, and responsive constraints for fixed-format UI.
- Avoid cards inside cards. Reserve card treatment for repeated items, modals, and functional panels.
- Keep border radius at 8px or less for cards and buttons unless an existing design system says otherwise.
- Avoid one-note palettes. Do not let the UI become dominated by a single hue family.
- Do not use structural emoji icons. Use SVG/icon libraries or repo-native icon components.
- Use semantic tokens where possible instead of scattering raw color values across components.
- Make primary actions obvious, secondary actions calmer, and destructive actions visually distinct.

## Accessibility And UX Checks

- Text contrast: at least 4.5:1 for normal text and 3:1 for large text.
- Touch targets: at least 44x44 px/pt with enough spacing.
- Keyboard: visible focus states and predictable tab order.
- Forms: visible labels, inline validation, useful error messages, and focus management.
- Motion: 150-300 ms for common interactions, transform/opacity for animations, and `prefers-reduced-motion` support.
- Responsive: no horizontal scroll, no clipped text, no disabled zoom, readable line lengths, and content visible under fixed headers/footers.
- Media: reserve image/video dimensions to prevent layout shift; lazy-load non-critical media.

## Pre-Delivery Pass

Before finalizing UI work:

1. Run at least one `--domain ux` search for the relevant risk area, such as `accessibility forms responsive navigation animation`.
2. Test the changed UI at mobile and desktop widths.
3. Check the CSS for palette drift, oversized radii, unstable layout, clipped text, decorative-only motion, and missing focus states.
4. If using charts, verify legends, labels, accessible color choices, and a text summary or clear key insight.
