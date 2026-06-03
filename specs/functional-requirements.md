# Functional Requirements

## FR-001: Installation Monitoring

The system SHALL monitor Windows installer execution with pre/post snapshots, process tracking, and unified JSON report generation.

## FR-002: Installer Discovery

The system SHALL list available installers from the configured `installers/` directory via chat command `list`.

## FR-003: Guided Installation

The system SHALL support installation via:
- Chat command: `install <filename>`
- Chat command: `install` or `browse` (file picker)
- Sidebar action buttons
- Dashboard hero buttons

## FR-004: Live Monitoring

The system SHALL display real-time installation status, timeline, and logs on the Monitoring page.

## FR-005: AI Troubleshooting

When enabled, the system SHALL run local SLM/RAG diagnosis after installation and display results on the Troubleshooting page.

## FR-006: Floating Chatbot

The system SHALL provide a floating chatbot launcher (FAB) in the bottom-right corner that opens a compact chat window without consuming layout space.

## FR-007: Full Chat Workspace

The system SHALL provide a dedicated Full Chat page accessible from sidebar navigation with the same message history as the floating chatbot.

## FR-008: Chat Commands

The chat assistant SHALL support: `list`, `install`, `install <name>`, `browse`.

## FR-009: Branding

The system SHALL load company logo and application logo independently from `assets/images/`.

## FR-010: Navigation

The system SHALL provide collapsible sidebar navigation with pages: Dashboard, Monitoring, Troubleshooting, Full Chat.

## FR-011: Dashboard

The home dashboard SHALL display welcome section, overview, capabilities, KPI cards, recent activity, system status, and enterprise benefits.
