# MODERN FRONTEND STANDARDS PLAYBOOK
## Production Guidelines for React, Next.js, Vue, Angular & Mobile

---

## 1. COMPONENT ARCHITECTURE & COMPOSITION
- **Smart vs. Dumb Decoupling**:
  - Keep presentation components pure (`props => JSX`). No network calls or business math.
  - Encapsulate server synchronization in custom hooks (`useOrderHistory()`) or state machines.
- **Server Components (RSC) vs. Client Components**:
  - Default to React Server Components (RSC) for initial data fetching and heavy imports.
  - Push `'use client'` down to the leaves of the DOM tree (interactive buttons, forms, dropdowns).

---

## 2. STATE MANAGEMENT STRATEGY
Do not dump everything into a global Redux/Zustand store:
1. **URL State** (Query parameters): Filters, search terms, pagination, active tabs. (Must be shareable via URL).
2. **Server Cache** (TanStack Query / SWR): Remote API responses, stale-while-revalidate, optimistic updates.
3. **Local UI State** (`useState`, `useReducer`): Modal visibility, form input buffer, hover states.
4. **Global Client State** (Zustand): User session tokens, dark mode preferences, ephemeral cart items.

---

## 3. ACCESSIBILITY (WCAG 2.1 AA/AAA)
- **Semantic HTML**: `<main>`, `<nav>`, `<article>`, `<header>`, `<footer>`. Avoid `div`-soup for interactive elements.
- **Keyboard Navigation**:
  - Every interactive element must be reachable via `Tab` with a visible focus ring (`focus-visible:ring-2`).
  - Escape closes modals and dropdowns; Enter/Space activates custom controls.
- **Screen Reader Verification**:
  - Provide `aria-label` or `aria-labelledby` on icon buttons (`<button aria-label="Close dialog">`).
  - Use `aria-live="polite"` for dynamic asynchronous updates.

---

## 4. CORE WEB VITALS & PERFORMANCE
- **LCP (Largest Contentful Paint < 2.5s)**: Preload hero images, avoid render-blocking CSS/fonts, SSR above-the-fold content.
- **INP (Interaction to Next Paint < 200ms)**: Defer heavy computations using `useTransition` or Web Workers; debounce search inputs.
- **CLS (Cumulative Layout Shift < 0.1)**: Always provide explicit `width` and `height` or `aspect-ratio` on images, embeds, and skeleton loaders.
