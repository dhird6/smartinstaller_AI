# UI Specifications

## Application Shell

| Property | Value |
|----------|-------|
| Framework | PySide6 |
| Theme | CCTechPalette |
| Min size | 1100 × 680 |
| Default size | 1480 × 920 |

## Layout Structure

```
┌──────────┬─────────────────────────────────────┐
│ Sidebar  │ TopHeader                           │
│ (272/76) ├─────────────────────────────────────┤
│          │                                     │
│          │         Page Content (Stack)        │
│          │                                     │
│          │                    ┌──────────────┐ │
│          │                    │ Floating Chat│ │
│          │                    │  (overlay)   │ │
│          │                    └──────────────┘ │
│          │                              [FAB]  │
└──────────┴─────────────────────────────────────┘
```

## Pages

| Index | Page | Route |
|-------|------|-------|
| 0 | Home Dashboard | Sidebar: Dashboard |
| 1 | Live Monitoring | Sidebar: Monitoring |
| 2 | Troubleshooting | Sidebar: Troubleshooting |
| 3 | Full Chat | Sidebar: Full Chat |

## Sidebar Specification

- **Expanded width**: 272px
- **Collapsed width**: 76px
- **Animation**: 260ms InOutCubic
- **Sections**: MAIN (nav items), ACTIONS (Launch, Browse)
- **Active indicator**: 3px left cyan border + gradient background
- **Collapse control**: Bottom of sidebar with label "Collapse"

## Header Specification

- **Height**: 72px
- **Content**: Company logo, app logo, CCTech name, product name, breadcrumb, page title

## Dashboard Sections

1. Hero — welcome, CTA buttons, dual logos
2. Smart Installer overview
3. Key capabilities (2×2 feature cards)
4. KPI stat cards (2×2 grid)
5. Recent activity + system status + AI highlights (3 columns)
6. Enterprise benefits (2×2 grid)

## Responsive Behavior

- Scroll areas on dashboard and chat for overflow
- Floating chat repositions on window resize
- Sidebar icons remain visible when collapsed
