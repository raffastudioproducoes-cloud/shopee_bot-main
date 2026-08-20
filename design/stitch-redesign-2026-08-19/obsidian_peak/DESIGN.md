---
name: Obsidian Peak
colors:
  surface: '#12131a'
  surface-dim: '#12131a'
  surface-bright: '#383940'
  surface-container-lowest: '#0c0e14'
  surface-container-low: '#1a1b22'
  surface-container: '#1e1f26'
  surface-container-high: '#282a31'
  surface-container-highest: '#33343c'
  on-surface: '#e2e1eb'
  on-surface-variant: '#e5beb6'
  inverse-surface: '#e2e1eb'
  inverse-on-surface: '#2f3037'
  outline: '#ac8981'
  outline-variant: '#5c403a'
  surface-tint: '#ffb4a5'
  primary: '#ffb4a5'
  on-primary: '#650b00'
  primary-container: '#ff5637'
  on-primary-container: '#580800'
  inverse-primary: '#ba1d00'
  secondary: '#c8c6c8'
  on-secondary: '#303032'
  secondary-container: '#474649'
  on-secondary-container: '#b7b4b7'
  tertiary: '#c8c6c9'
  on-tertiary: '#303033'
  tertiary-container: '#919094'
  on-tertiary-container: '#29292c'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad3'
  primary-fixed-dim: '#ffb4a5'
  on-primary-fixed: '#3e0400'
  on-primary-fixed-variant: '#8e1400'
  secondary-fixed: '#e4e2e4'
  secondary-fixed-dim: '#c8c6c8'
  on-secondary-fixed: '#1b1b1d'
  on-secondary-fixed-variant: '#474649'
  tertiary-fixed: '#e4e1e5'
  tertiary-fixed-dim: '#c8c6c9'
  on-tertiary-fixed: '#1b1b1e'
  on-tertiary-fixed-variant: '#47464a'
  background: '#12131a'
  on-background: '#e2e1eb'
  surface-variant: '#33343c'
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base-unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  bento-gap: 16px
---

## Brand & Style

The design system is centered on "Dark Luxury"—a high-end, high-performance aesthetic tailored for e-commerce automation. It targets professionals who value precision, speed, and status. The emotional response should be one of quiet confidence and technical superiority.

The style is a fusion of **Minimalism** and **Glassmorphism**. It utilizes a "Dark Mode First" philosophy where depth is not created by light, but by varying degrees of charcoal translucency and high-precision 1px borders. The interface remains intentionally monochromatic to allow the vibrant orange accent to command immediate attention for critical actions and performance metrics.

**Key Visual Principles:**
- **Restraint:** Color is a tool for utility, not just decoration.
- **Precision:** Elements are aligned to a strict grid with hair-line strokes.
- **Atmosphere:** Deep background blurs create a sense of physical space behind the UI.

## Colors

This design system uses a curated dark palette to prevent eye strain while maintaining a premium feel. Pure black is avoided in favor of a deep charcoal (#0a0a0b) to allow for subtle shadow depth.

- **Primary (Accent):** `#ff4d2d` (Vibrant Orange). Use this exclusively for the main Call-to-Action (CTA), active states, and critical success indicators.
- **Surface Tiers:** 
  - `Base`: #0a0a0b (Main background)
  - `Surface`: #161618 (Cards, containers)
  - `Elevated`: #242427 (Hover states, modals)
- **Borders:** Use a consistent `rgba(255, 255, 255, 0.08)` for all internal borders to create a "etched" look.
- **Typography:** Use white (#ffffff) for headings, Gray-400 (#a1a1aa) for body text, and Gray-600 (#52525b) for disabled/placeholder states.

## Typography

The typography system pairs the geometric, technical character of **Sora** for headings with the utilitarian clarity of **Inter** for UI elements and data.

- **Headings:** Use Sora with tight letter-spacing to create a bold, "tech-luxury" display effect. 
- **Body:** Inter is used for all functional text to ensure high legibility against dark backgrounds.
- **Micro-copy:** Use `label-caps` for section headers and category tags to differentiate them from interactive data.
- **Mobile Scaling:** For mobile viewports, `display-lg` should scale down to `headline-lg` (32px) to maintain balance.

## Layout & Spacing

This design system utilizes a **Bento-grid** philosophy, particularly for dashboard views. Content is organized into modular containers of varying sizes that fit into a rigid 12-column grid.

- **Grid:** 12-column system on desktop, 4-column on mobile.
- **Bento Logic:** Containers should use a standard gap of 16px (`bento-gap`). Larger dashboard layouts should prioritize visual balance, with high-priority metrics occupying 2/3 or full width.
- **Whitespace:** Use generous padding (32px+) inside containers to allow data to "breathe." Luxury is often defined by what is *not* there; avoid crowding elements.
- **Breakpoints:** 
  - Mobile: < 768px (Single column stacked)
  - Tablet: 768px - 1024px (2-column layout)
  - Desktop: > 1024px (Full 12-column bento)

## Elevation & Depth

In a dark UI, elevation is communicated through **Tonal Layering** and **Glassmorphism**, rather than traditional heavy shadows.

- **Surface Levels:** The background is the lowest point. Each subsequent layer (cards, then modals) becomes slightly lighter in color.
- **Glassmorphism:** Use a `backdrop-filter: blur(12px)` and `background: rgba(22, 22, 24, 0.7)` for navigation bars and dropdown menus to create a sense of transparency.
- **The Glow:** For the primary orange buttons, use a soft, localized outer glow (`box-shadow: 0 0 20px rgba(255, 77, 45, 0.15)`) to make them appear self-illuminated.
- **Stroke Depth:** Every container must have a 1px border. On the top edge, use a slightly lighter stroke (`rgba(255,255,255,0.12)`) to simulate a subtle top-down light source.

## Shapes

The shape language is refined and professional, opting for "Rounded" corners that provide a modern feel without being overly "bubbly" or informal.

- **Containers:** 0.5rem (8px) for standard cards and bento boxes.
- **Interactive Elements:** 0.5rem for buttons and input fields to maintain consistency with containers.
- **Large Surfaces:** Modals and large dashboard sections use 1rem (16px) to soften the overall interface.
- **Status Indicators:** Use full pill-shapes (rounded-full) for tags and badges.

## Components

All components are built to feel tactile and responsive, leveraging CSS-first animations for a premium experience.

- **Primary Button:** Solid #ff4d2d background, white text. On hover, apply a `transform: translateY(-1px)` and increase the glow intensity.
- **Secondary Button:** Transparent background with the 1px white border. On hover, the border opacity increases and the background shifts to a subtle white tint (`0.04`).
- **Bento Cards:** Background #161618. 1px border. Use `transition: transform 0.2s ease` to slightly scale up (1.01x) on hover.
- **Input Fields:** Dark background (#0a0a0b) with an internal border. The border should transition to the Primary Orange (#ff4d2d) only when focused.
- **Chips/Badges:** Small, all-caps text with a low-opacity version of the status color (e.g., Orange text on `rgba(255, 77, 45, 0.1)` background).
- **Progress Bars:** Use a thin 4px track. The filled portion should be a solid Primary Orange gradient for a "laser" effect.
- **Data Tables:** Row-based with no vertical borders. Use a subtle hover highlight on the entire row to assist tracking.