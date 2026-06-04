"""Enterprise home dashboard — professional CCTech landing experience."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
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
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        container.setObjectName("dashContainer")
        container.setStyleSheet(f"QWidget#dashContainer {{ background: {palette.canvas}; }}")
        self.setWidget(container)
        self._root = QVBoxLayout(container)
        self._root.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        self._root.setSpacing(PAGE_SPACING)

        self._stats_host = QWidget()
        self._stats_grid = QGridLayout(self._stats_host)
        self._stats_grid.setSpacing(GRID_GAP)
        self._stats_grid.setContentsMargins(0, 0, 0, 0)
        for col in range(4):
            self._stats_grid.setColumnStretch(col, 1)
        self._sessions_host = QVBoxLayout()
        self._sessions_host.setSpacing(CARD_INNER_SPACING - 4)
        self._active_host = QVBoxLayout()
        self._active_host.setSpacing(CARD_INNER_SPACING - 4)
        self._system_status_label = QLabel()
        self._monitoring_status_label = QLabel()
        self._ai_recommendations_host = QVBoxLayout()
        self._ai_recommendations_host.setSpacing(CARD_INNER_SPACING - 4)
        self._build_static()

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
        hero.setMinimumHeight(210)
        hero.setStyleSheet(hero_panel_stylesheet(p))
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(28)

        text = QVBoxLayout()
        text.setSpacing(14)

        badge = QLabel("CCTech · Enterprise AI Platform")
        badge.setObjectName("heroBadge")
        badge.setMaximumWidth(300)

        headline = QLabel("Smart Installer AI")
        headline.setObjectName("heroTitle")

        sub = QLabel(
            "Autonomous Windows installation monitoring, real-time evidence "
            "collection, and local AI-powered troubleshooting — built for enterprise IT."
        )
        sub.setObjectName("heroSubtitle")
        sub.setWordWrap(True)
        sub.setMaximumWidth(580)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        monitor_btn = hero_primary_button("View live monitoring", p, parent=hero)
        monitor_btn.clicked.connect(self.monitoring_requested.emit)
        center_btn = hero_outline_button("Installation Center", p, parent=hero)
        center_btn.clicked.connect(self.installation_center_requested.emit)
        actions.addWidget(monitor_btn)
        actions.addWidget(center_btn)
        actions.addStretch(1)

        text.addWidget(badge)
        text.addWidget(headline)
        text.addWidget(sub)
        text.addSpacing(4)
        text.addLayout(actions)
        layout.addLayout(text, stretch=2)

        logo = QLabel()
        logo.setObjectName("heroLogo")
        logo.setPixmap(load_brand_logo_pixmap(72))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(80, 80)
        logo.setScaledContents(False)
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignVCenter)
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
        for i, (icon, title, desc) in enumerate(items):
            grid.addWidget(
                FeatureCard(icon=icon, title=title, description=desc, palette=p),
                i // 2,
                i % 2,
            )
        layout.addLayout(grid)
        return card

    def _build_three_column(self) -> QWidget:
        p = self._palette
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GRID_GAP)

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

        layout.addWidget(active_card, stretch=1)
        layout.addWidget(sessions_card, stretch=1)
        layout.addWidget(status_card, stretch=1)
        layout.addWidget(ai_card, stretch=1)
        return row

    def _build_benefits(self) -> QFrame:
        p = self._palette
        card, layout = section_card(p)
        heading = QLabel("Why Smart Installer AI?")
        heading.setStyleSheet(heading_stylesheet(p))
        layout.addWidget(heading)
        grid = QGridLayout()
        grid.setSpacing(GRID_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
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
        for i, (icon, title, desc) in enumerate(benefits):
            grid.addWidget(self._benefit_cell(icon, title, desc), i // 2, i % 2)
        layout.addLayout(grid)
        return card

    def _benefit_cell(self, icon: str, title: str, desc: str) -> QFrame:
        p = self._palette
        cell = QFrame()
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

    def refresh(self, stats: DashboardStats) -> None:
        p = self._palette

        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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
        for idx, card in enumerate(cards):
            self._stats_grid.addWidget(card, 0, idx)

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
                issues_lbl = QLabel(f"{session.error_count} issue(s)")
                issues_lbl.setStyleSheet(muted_stylesheet(p) + " border: none;")

                left = QVBoxLayout()
                left.setSpacing(2)
                left.addWidget(name_lbl)
                left.addWidget(issues_lbl)

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
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
