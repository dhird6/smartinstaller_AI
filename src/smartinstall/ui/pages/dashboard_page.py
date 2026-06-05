"""Enterprise home dashboard — professional CCTech landing experience."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.layout.responsive import (
    configure_page_container,
    configure_page_scroll,
    grid_columns_for_mode,
    layout_mode_for_width,
)

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.components.feature_card import FeatureCard
from smartinstall.ui.components.stat_card import StatCard
from smartinstall.ui.components.ui_card import (
    CARD_INNER_SPACING,
    GRID_GAP,
    PAGE_MARGIN,
    PAGE_SPACING,
    apply_card_style,
    section_card,
)
from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.services.session_stats_service import DashboardStats
from smartinstall.ui.theme.cctech_theme import (
    CCTechPalette,
    body_stylesheet,
    heading_stylesheet,
    hero_panel_stylesheet,
    muted_stylesheet,
)


class DashboardPage(QScrollArea):
    """Information-rich enterprise landing page."""

    monitoring_requested = Signal()
    installation_center_requested = Signal()
    prompt_requested = Signal(str)

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        configure_page_scroll(self)
        self._layout_mode = "compact"
        container = QWidget()
        container.setObjectName("dashContainer")
        container.setStyleSheet(f"QWidget#dashContainer {{ background: {palette.canvas}; }}")
        configure_page_container(container)
        self.setWidget(container)
        self._root = QVBoxLayout(container)
        self._root.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN - 8, PAGE_MARGIN, PAGE_MARGIN)
        self._root.setSpacing(PAGE_SPACING - 4)

        self._stats_host = QWidget()
        self._stats_host.setMinimumWidth(0)
        self._stats_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._stats_grid = QGridLayout(self._stats_host)
        self._stats_grid.setSpacing(GRID_GAP)
        self._stats_grid.setContentsMargins(0, 0, 0, 0)
        for col in range(4):
            self._stats_grid.setColumnStretch(col, 1)
        self._stat_cards: list[StatCard] = []
        self._sessions_host = QVBoxLayout()
        self._sessions_host.setSpacing(CARD_INNER_SPACING - 4)
        self._active_host = QVBoxLayout()
        self._active_host.setSpacing(CARD_INNER_SPACING - 4)
        self._system_status_label = QLabel()
        self._monitoring_status_label = QLabel()
        self._ai_recommendations_host = QVBoxLayout()
        self._ai_recommendations_host.setSpacing(CARD_INNER_SPACING - 4)
        self._last_stats_fingerprint = ""
        self._build_static()

    def invalidate_cache(self) -> None:
        """Force the next refresh to rebuild dashboard widgets."""
        self._last_stats_fingerprint = ""
        self.reflow_for_width(900)

    def _build_static(self) -> None:
        self._root.addWidget(self._build_hero())
        self._root.addWidget(self._stats_host)
        self._root.addWidget(self._build_capabilities())
        self._root.addWidget(self._build_three_column())
        self._root.addWidget(self._build_benefits())
        self._root.addStretch(1)

    def _build_hero(self) -> QFrame:
        p = self._palette
        hero = QFrame()
        hero.setObjectName("dashHero")
        hero.setMinimumHeight(160)
        hero.setMinimumWidth(0)
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        hero.setStyleSheet(hero_panel_stylesheet(p))
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        logo = QLabel()
        logo.setObjectName("heroLogo")
        logo_pixmap = load_brand_logo_pixmap(52)
        logo.setPixmap(logo_pixmap)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(56, 56)
        logo.setScaledContents(not logo_pixmap.isNull())
        header_row.addWidget(logo, alignment=Qt.AlignmentFlag.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        badge = QLabel("CCTech · Enterprise AI Platform")
        badge.setObjectName("heroBadge")
        badge.setWordWrap(True)

        headline = QLabel("Smart Installer AI")
        headline.setObjectName("heroTitle")
        headline.setWordWrap(True)

        title_col.addWidget(badge)
        title_col.addWidget(headline)
        header_row.addLayout(title_col, stretch=1)
        layout.addLayout(header_row)

        sub = QLabel(
            "Autonomous Windows installation monitoring, real-time evidence "
            "collection, and local AI-powered troubleshooting — built for enterprise IT."
        )
        sub.setObjectName("heroSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        self._hero_actions_host = QWidget()
        self._hero_actions_host.setMinimumWidth(0)
        self._hero_actions_layout = QVBoxLayout(self._hero_actions_host)
        self._hero_actions_layout.setContentsMargins(0, 0, 0, 0)
        self._hero_actions_layout.setSpacing(8)

        monitor_btn = hero_primary_button("View live monitoring", p, parent=hero)
        monitor_btn.clicked.connect(self.monitoring_requested.emit)
        center_btn = hero_outline_button("Installation Center", p, parent=hero)
        center_btn.clicked.connect(self.installation_center_requested.emit)
        for btn in (monitor_btn, center_btn):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hero_monitor_btn = monitor_btn
        self._hero_center_btn = center_btn
        self._hero_actions_layout.addWidget(monitor_btn)
        self._hero_actions_layout.addWidget(center_btn)
        layout.addWidget(self._hero_actions_host)
        return hero

    def _build_capabilities(self) -> QFrame:
        p = self._palette
        card, layout = section_card(p)
        heading = QLabel("Key capabilities")
        heading.setStyleSheet(heading_stylesheet(p))
        layout.addWidget(heading)
        grid = QGridLayout()
        grid.setSpacing(GRID_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        self._capabilities_grid = grid
        self._feature_cards: list[FeatureCard] = []
        items = [
            ("⚡", "Installation automation",
             "One-click monitored installs with full evidence capture."),
            ("📊", "Live monitoring",
             "Real-time timeline, process tracking and log stream."),
            ("🤖", "AI troubleshooting",
             "Local SLM + RAG for automated root-cause and fix workflows."),
            ("🔒", "Enterprise privacy",
             "Fully on-premises — no cloud dependency for AI diagnosis."),
        ]
        cap_cols = grid_columns_for_mode(self._layout_mode, wide=2, compact=2)
        for i, (icon, title, desc) in enumerate(items):
            feature = FeatureCard(icon=icon, title=title, description=desc, palette=p)
            self._feature_cards.append(feature)
            grid.addWidget(feature, i // cap_cols, i % cap_cols)
        layout.addLayout(grid)
        return card

    def _build_three_column(self) -> QWidget:
        p = self._palette
        row = QWidget()
        row.setMinimumWidth(0)
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.setStyleSheet("background: transparent;")
        self._info_grid = QGridLayout(row)
        self._info_grid.setContentsMargins(0, 0, 0, 0)
        self._info_grid.setSpacing(GRID_GAP)

        active_card, active_layout = section_card(p)
        active_heading = QLabel("Active installations")
        active_heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        active_layout.addWidget(active_heading)
        active_layout.addLayout(self._active_host)

        sessions_card, sessions_layout = section_card(p)
        sessions_heading = QLabel("Recent installations")
        sessions_heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        sessions_layout.addWidget(sessions_heading)
        sessions_layout.addLayout(self._sessions_host)

        status_card, status_layout = section_card(p)
        status_heading = QLabel("System status")
        status_heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        status_layout.addWidget(status_heading)
        self._system_status_label.setWordWrap(True)
        self._system_status_label.setStyleSheet(body_stylesheet(p))
        status_layout.addWidget(self._system_status_label)
        self._monitoring_status_label.setWordWrap(True)
        self._monitoring_status_label.setStyleSheet(body_stylesheet(p))
        status_layout.addWidget(self._monitoring_status_label)

        ai_card, ai_layout = section_card(p)
        ai_heading = QLabel("AI highlights")
        ai_heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        ai_layout.addWidget(ai_heading)
        ai_layout.addLayout(self._ai_recommendations_host)
        ai_layout.addStretch(1)

        self._info_cards = (active_card, sessions_card, status_card, ai_card)
        for card in self._info_cards:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._place_info_cards(mode=self._layout_mode)
        return row

    def _place_info_cards(self, *, mode: str) -> None:
        for card in self._info_cards:
            self._info_grid.removeWidget(card)
        cards = self._info_cards
        cols = grid_columns_for_mode(mode, wide=4, compact=2)
        for idx, card in enumerate(cards):
            self._info_grid.addWidget(card, idx // cols, idx % cols)
        for col in range(cols):
            self._info_grid.setColumnStretch(col, 1)

    def reflow_for_width(self, width: int) -> None:
        mode = layout_mode_for_width(width)
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        self._place_info_cards(mode=mode)
        self._reflow_stats(mode=mode)
        self._reflow_feature_grid(mode=mode)
        self._reflow_benefits_grid(mode=mode)
        self._reflow_hero_actions(mode=mode)

    def _reflow_stats(self, *, mode: str) -> None:
        if not self._stat_cards:
            return
        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            if item.widget():
                self._stats_grid.removeWidget(item.widget())
        cols = grid_columns_for_mode(mode, wide=4, compact=2)
        for idx, card in enumerate(self._stat_cards):
            self._stats_grid.addWidget(card, idx // cols, idx % cols)

    def _reflow_feature_grid(self, *, mode: str) -> None:
        if not hasattr(self, "_capabilities_grid"):
            return
        while self._capabilities_grid.count():
            item = self._capabilities_grid.takeAt(0)
            if item.widget():
                self._capabilities_grid.removeWidget(item.widget())
        cols = grid_columns_for_mode(mode, wide=2, compact=2)
        for idx, card in enumerate(self._feature_cards):
            self._capabilities_grid.addWidget(card, idx // cols, idx % cols)

    def _reflow_benefits_grid(self, *, mode: str) -> None:
        if not hasattr(self, "_benefits_grid"):
            return
        while self._benefits_grid.count():
            item = self._benefits_grid.takeAt(0)
            if item.widget():
                self._benefits_grid.removeWidget(item.widget())
        cols = grid_columns_for_mode(mode, wide=2, compact=2)
        for idx, cell in enumerate(self._benefit_cells):
            self._benefits_grid.addWidget(cell, idx // cols, idx % cols)

    def _reflow_hero_actions(self, *, mode: str) -> None:
        if not hasattr(self, "_hero_actions_layout"):
            return
        while self._hero_actions_layout.count():
            item = self._hero_actions_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        buttons = (self._hero_monitor_btn, self._hero_center_btn)
        if mode == "wide":
            row_host = QWidget()
            row_host.setMinimumWidth(0)
            row = QHBoxLayout(row_host)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            for btn in buttons:
                btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                row.addWidget(btn)
            row.addStretch(1)
            self._hero_actions_layout.addWidget(row_host)
        else:
            for btn in buttons:
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self._hero_actions_layout.addWidget(btn)

    def _build_benefits(self) -> QFrame:
        p = self._palette
        card, layout = section_card(p)
        heading = QLabel("Why Smart Installer AI?")
        heading.setStyleSheet(heading_stylesheet(p))
        layout.addWidget(heading)
        grid = QGridLayout()
        grid.setSpacing(GRID_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        self._benefits_grid = grid
        self._benefit_cells: list[QFrame] = []
        benefits = (
            ("⚡", "Reduced MTTR",
             "Faster failure diagnosis with AI-guided remediation steps."),
            ("📋", "Audit-ready reports",
             "Unified JSON evidence packages for compliance and review."),
            ("🔄", "Consistent deployments",
             "Repeatable, monitored install workflows across all environments."),
            ("🏆", "Enterprise-grade UX",
             "Professional CCTech-branded experience built for IT teams."),
        )
        ben_cols = grid_columns_for_mode(self._layout_mode, wide=2, compact=2)
        for i, (icon, title, desc) in enumerate(benefits):
            cell = self._benefit_cell(icon, title, desc)
            self._benefit_cells.append(cell)
            grid.addWidget(cell, i // ben_cols, i % ben_cols)
        layout.addLayout(grid)
        return card

    def _benefit_cell(self, icon: str, title: str, desc: str) -> QFrame:
        p = self._palette
        cell = QFrame()
        cell.setMinimumWidth(0)
        cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        apply_card_style(cell, p, object_name="benefitCell")
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(8)
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18pt; background: transparent;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=10))
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(body_stylesheet(p))
        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        return cell

    @staticmethod
    def _stats_fingerprint(stats: DashboardStats) -> str:
        active = ",".join(
            f"{item.installer_name}:{item.stage}:{item.mode}"
            for item in stats.active_installations
        )
        recent = ",".join(
            f"{item.session_id}:{item.outcome}:{item.error_count}"
            for item in stats.recent_sessions
        )
        recommendations = "|".join(stats.ai_recommendations)
        return (
            f"{stats.active_count}|{stats.failed}|{stats.successful}|{stats.total_sessions}|"
            f"{stats.partial}|{int(stats.background_service_running)}|"
            f"{int(stats.automatic_monitoring_enabled)}|{int(stats.ai_troubleshooting_enabled)}|"
            f"{active}|{recent}|{recommendations}"
        )

    def refresh(self, stats: DashboardStats) -> None:
        fingerprint = self._stats_fingerprint(stats)
        if fingerprint == self._last_stats_fingerprint:
            return
        self._last_stats_fingerprint = fingerprint
        p = self._palette

        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._stat_cards.clear()

        rate = round(100 * stats.successful / stats.total_sessions) if stats.total_sessions else 0
        cards = [
            StatCard(
                title="Active now",
                value=str(stats.active_count),
                subtitle="Automatic + manual monitoring",
                palette=p,
            ),
            StatCard(
                title="Failed",
                value=str(stats.failed),
                subtitle="Needs troubleshooting",
                palette=p,
            ),
            StatCard(
                title="Success rate",
                value=f"{rate}%",
                subtitle=f"{stats.successful} successful of {stats.total_sessions}",
                palette=p,
            ),
            StatCard(
                title="AI troubleshooting",
                value="ON" if stats.ai_troubleshooting_enabled else "OFF",
                subtitle="Local Ollama + Chroma RAG",
                palette=p,
            ),
        ]
        self._stat_cards = cards
        cols = grid_columns_for_mode(self._layout_mode, wide=4, compact=2)
        for idx, card in enumerate(cards):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._stats_grid.addWidget(card, idx // cols, idx % cols)

        self._clear_layout(self._active_host)
        if not stats.active_installations:
            empty_active = QLabel("No active installations — background monitoring is standing by.")
            empty_active.setWordWrap(True)
            empty_active.setStyleSheet(muted_stylesheet(p))
            self._active_host.addWidget(empty_active)
        else:
            for active in stats.active_installations:
                row = QFrame()
                apply_card_style(row, p, object_name="activeRow")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(12, 10, 12, 10)
                name_lbl = QLabel(f"<b>{active.installer_name}</b>")
                name_lbl.setStyleSheet(
                    f"color: {p.text_primary}; font-size: 9.5pt; border: none;"
                )
                stage_lbl = QLabel(active.stage)
                stage_lbl.setStyleSheet(muted_stylesheet(p) + " border: none;")
                left = QVBoxLayout()
                left.addWidget(name_lbl)
                left.addWidget(stage_lbl)
                pill = QLabel(active.mode.upper())
                pill.setStyleSheet(
                    f"color: {p.blue_600}; background: {p.info_bg}; border: 1px solid {p.border};"
                    f" border-radius: 10px; padding: 2px 10px; font-size: 8pt; font-weight: 700;"
                )
                rl.addLayout(left, stretch=1)
                rl.addWidget(pill, alignment=Qt.AlignmentFlag.AlignVCenter)
                self._active_host.addWidget(row)

        self._clear_layout(self._sessions_host)
        if not stats.recent_sessions:
            empty = QLabel("No recent activity — launch an installation to get started.")
            empty.setWordWrap(True)
            empty.setStyleSheet(muted_stylesheet(p))
            self._sessions_host.addWidget(empty)
        else:
            for session in stats.recent_sessions:
                outcome_lower = (session.outcome or "").lower()
                if "success" in outcome_lower or "complet" in outcome_lower:
                    accent = p.success
                    pill_bg = p.success_bg
                    pill_border = p.success_border
                elif "fail" in outcome_lower or "error" in outcome_lower:
                    accent = p.error
                    pill_bg = p.error_bg
                    pill_border = p.error_border
                else:
                    accent = p.warning
                    pill_bg = p.warning_bg
                    pill_border = p.warning_border

                row = QFrame()
                apply_card_style(row, p, object_name="sessionRow")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(12, 10, 12, 10)
                rl.setSpacing(12)

                name_lbl = QLabel(f"<b>{session.installer_name}</b>")
                name_lbl.setStyleSheet(
                    f"color: {p.text_primary}; font-size: 9.5pt; border: none;"
                )
                meta_lbl = QLabel(
                    f"{session.error_count} issue(s)"
                    + (f"  ·  {self._format_timestamp(session.timestamp)}" if session.timestamp else "")
                )
                meta_lbl.setStyleSheet(muted_stylesheet(p) + " border: none;")

                left = QVBoxLayout()
                left.setSpacing(2)
                left.addWidget(name_lbl)
                left.addWidget(meta_lbl)

                pill = QLabel(session.outcome or "Unknown")
                pill.setStyleSheet(
                    f"color: {accent}; background: {pill_bg}; border: 1px solid {pill_border};"
                    f" border-radius: 10px; padding: 2px 10px;"
                    f" font-size: 8pt; font-weight: 700;"
                )
                rl.addLayout(left, stretch=1)
                rl.addWidget(pill, alignment=Qt.AlignmentFlag.AlignVCenter)
                self._sessions_host.addWidget(row)

        self._system_status_label.setText(
            f"<b style='color:{p.text_primary}'>Platform</b>"
            f"&nbsp;&nbsp;Smart Installer AI — Next Gen Monitoring<br/><br/>"
            f"<b style='color:{p.text_primary}'>Total sessions</b>"
            f"&nbsp;&nbsp;{stats.total_sessions}<br/>"
            f"<b style='color:{p.text_primary}'>Partial</b>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{stats.partial}"
        )
        monitor_line = (
            "Background service: RUNNING"
            if stats.background_service_running
            else "Background service: STOPPED"
        )
        auto_line = (
            "Automatic monitoring: ENABLED"
            if stats.automatic_monitoring_enabled
            else "Automatic monitoring: DISABLED"
        )
        heartbeat = ""
        if stats.last_heartbeat:
            heartbeat = f"<br/><b style='color:{p.text_primary}'>Last heartbeat</b>&nbsp;&nbsp;{stats.last_heartbeat}"
        self._monitoring_status_label.setText(
            f"<b style='color:{p.text_primary}'>Monitoring</b><br/>"
            f"{monitor_line}<br/>{auto_line}{heartbeat}"
        )

        self._clear_layout(self._ai_recommendations_host)
        recommendations = stats.ai_recommendations or [
            "Launch installers from Explorer for automatic monitoring, or use Installation Center.",
        ]
        for body_text in recommendations:
            lbl = QLabel(f"•  {body_text}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(body_stylesheet(p))
            self._ai_recommendations_host.addWidget(lbl)

    @staticmethod
    def _format_timestamp(timestamp: str) -> str:
        if not timestamp:
            return ""
        cleaned = timestamp.replace("T", " ").replace("Z", " UTC")
        if len(cleaned) >= 16:
            return cleaned[:16]
        return cleaned

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
