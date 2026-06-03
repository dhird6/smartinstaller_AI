# Chatbot Specifications

## Overview

Smart Installer provides two chat experiences sharing a single message history:

1. **Floating Chatbot** — Website-style overlay (default)
2. **Full Chat Page** — Dedicated workspace (sidebar navigation)

## Floating Chatbot

### Launcher (FAB)

| Property | Value |
|----------|-------|
| Size | 62 × 62 px |
| Position | Bottom-right, 24px margin |
| Icon | chatbot.svg |
| Style | Accent gradient, drop shadow |
| Default state | Visible when chat closed |

### Chat Window — Compact Mode

| Property | Value |
|----------|-------|
| Size | 400 × 540 px |
| Position | Bottom-right, above FAB area |
| Border radius | 16px |
| Background | assistant_panel_bg gradient |

### Chat Window — Maximized Mode

| Property | Value |
|----------|-------|
| Size | 680 × 720 px |
| Position | Bottom-right anchored |
| Restore | Returns to compact dimensions |

### Header Controls

| Button | Action |
|--------|--------|
| − (Minimize) | Close to FAB |
| □ (Maximize) | Toggle maximized/compact |
| × (Close) | Close to FAB |

### Header Content

- App logo (32px)
- Title: "SmartInstall AI"
- Subtitle: "CCTech Enterprise Assistant"
- Context line: session/installer status

### Animations

- Open: 280ms opacity fade (OutCubic)
- FAB hide/show on state change

## Full Chat Page

- Hero banner with dual logos and description
- Session context bar
- Full-width chat panel (light variant)
- Accessible via sidebar "Full Chat" item

## Chat Panel Features

- Welcome screen with suggested prompts
- Quick action chips: Install, List, Help
- User/assistant/system message bubbles
- Typing indicator during processing
- Auto-scroll to latest message
- Timestamps on messages
- Rich sections for SLM diagnosis output

## Suggested Prompts

- `install mingw-get-setup.exe`
- `list available installers`
- `What can Smart Installer do?`
- `How does AI troubleshooting work?`

## State Management

- Single `ChatPanel` instance reparented between floating and full page
- Switching to Full Chat: floating chat closes, panel moves to full page
- Switching away: panel returns to floating widget (closed state, FAB visible)

## Branding

- Floating header: app logo
- Floating footer: company logo + "CCTech • Private local AI"
- Welcome screen: app logo
