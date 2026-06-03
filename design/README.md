# Design References

This folder contains UI/UX design references for Smart Installer AI.

## Design Language

- **Primary reference**: [CCTech website](https://www.cctech.co.in/) — professional blue palette, clean enterprise aesthetic
- **Inspiration**: Modern SaaS dashboards (Linear, Vercel, Stripe-style card layouts)

## Design Tokens

Canonical tokens are defined in code:

```
src/smartinstall/ui/theme/cctech_theme.py → CCTechPalette
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Floating chatbot vs docked panel | Website-style UX; maximizes content area |
| Collapsible sidebar | Enterprise dashboard standard; space efficiency |
| Dual logo support | Company (CCTech) vs product (Smart Installer) branding |
| Glass-morphism cards | Modern SaaS aesthetic on dashboard |
| Dark chat / light full page | Contrast appropriate to container background |

## Asset Placement

Place design exports and branded assets in:

```
assets/images/company_logo.svg
assets/images/app_logo.svg
```

## Mockup Guidelines

When adding mockups to this folder:
- Name files descriptively: `dashboard-v2.png`, `chatbot-compact.png`
- Include resolution and date in filename if iterating
- Reference corresponding spec in `specs/ui-specifications.md`
