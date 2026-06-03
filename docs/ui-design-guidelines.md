# UI Design Guidelines

## Design Language

Smart Installer AI follows the **CCTech corporate design system** — professional blue-based palette inspired by [cctech.co.in](https://www.cctech.co.in/).

## Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `navy_900` | `#0a1628` | Sidebar background |
| `navy_800` | `#0f2744` | Dark surfaces |
| `blue_600` | `#1e5bff` | Primary actions, links |
| `cyan_400` | `#22d3ee` | Accents, active states |
| `cyan_300` | `#67e8f9` | Highlights on dark |
| `orange_500` | `#f97316` | Warnings, attention |
| `canvas` | `#eef2f8` | Main content background |
| `surface` | `#ffffff` | Cards, panels |

Defined in `src/smartinstall/ui/theme/cctech_theme.py` as `CCTechPalette`.

## Typography

- **Primary font**: Segoe UI Variable → Segoe UI fallback
- **Page titles**: 17–18pt, weight 700
- **Section headings**: 13pt, weight 700
- **Body**: 9.5–10.5pt
- **Labels/captions**: 8–9pt

## Spacing

- Page margins: 28–32px
- Card padding: 18–24px
- Component gap: 12–16px
- Sidebar width: 272px expanded / 76px collapsed

## Components

### Cards
- Border radius: 16–18px
- Glass effect: `rgba(255,255,255,0.72)` with subtle border
- Shadow: `rgba(15, 23, 42, 0.08)`

### Buttons
- Primary: Cyan-to-blue gradient (`accent_gradient`)
- Secondary: Outlined blue border
- Ghost: Transparent with border

### Sidebar
- Collapsible with 260ms ease animation
- Active item: Left cyan border + gradient background
- Section labels: Uppercase, letter-spaced

### Floating Chatbot
- FAB: 62px circle, bottom-right, 24px margin
- Compact window: 400×540px
- Maximized: 680×720px
- Rounded corners: 16px, drop shadow

## Accessibility

- Minimum contrast ratio 4.5:1 for body text
- Focus states via cyan border on inputs
- Tooltips on icon-only controls
- Keyboard: Enter to send chat, Tab navigation

## Do's and Don'ts

**Do:**
- Use `CCTechPalette` tokens — never hardcode colors in new code
- Use `enterprise_button` helpers for consistent CTAs
- Test at 1100×680 minimum window size

**Don't:**
- Mix legacy `windows_theme.py` with CCTech theme
- Dock chat as permanent right panel (use floating widget)
- Clip content — use scroll areas for overflow
