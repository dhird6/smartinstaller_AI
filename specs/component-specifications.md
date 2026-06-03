# Component Specifications

## Shell Components

### SidebarNav
- **File**: `ui/shell/sidebar_nav.py`
- **Signals**: `page_selected(int)`, `install_clicked`, `browse_clicked`, `collapsed_changed(bool)`
- **States**: expanded (272px), collapsed (76px)

### TopHeader
- **File**: `ui/shell/top_header.py`
- **API**: `set_page_title(str)`

### FloatingChatWidget
- **File**: `ui/shell/floating_chat_widget.py`
- **API**: `attach_chat`, `detach_chat`, `open_compact`, `maximize`, `restore`, `minimize`, `close_chat`, `set_context`, `reposition`
- **States**: CLOSED, COMPACT, MAXIMIZED

### SplashScreen
- **File**: `ui/shell/splash_screen.py`
- **API**: `set_status(str)`, `finish_after(callback, ms=1400)`

## Page Components

### DashboardPage
- **Signals**: `install_requested`, `browse_requested`
- **API**: `refresh(DashboardStats)`

### MonitoringPage
- **API**: `set_idle`, `set_busy`, `set_success`, `set_error`, `append_log`, `apply_run_result`

### TroubleshootingPage
- **API**: `apply_run_result(result, slm_answer, slm_sources)`

### FullChatPage
- **API**: `attach_chat`, `detach_chat`, `set_context`

## Reusable Components

### StatCard
- KPI display: title, value, subtitle, accent color

### FeatureCard
- Icon + title + description with accent border

### Enterprise Buttons
- `primary_button`, `secondary_button`, `ghost_button` — factory functions

### InstallVisualizer
- 3D-style orb for monitoring page progress

### AnimatedBackground
- Subtle canvas animation behind content area

## Widget Components

### ChatPanel
- **Signals**: `message_submitted(str)`, `prompt_chosen(str)`
- **API**: `append_message`, `show_typing`, `hide_typing`, `set_input_enabled`, `set_variant_dark`, `set_variant_light`
- **Variants**: `light`, `dark`

### AvatarLabel
- SVG icon rendering at configurable size

## Service Components

### ChatFormatter
- Builds structured `ChatMessage` objects for welcome, lists, status, install summary, SLM diagnosis

### SessionStatsService
- Aggregates dashboard KPIs from sessions/reports directories

### SlmResponseParser
- Parses SLM output into `ChatSection` list for rich display
