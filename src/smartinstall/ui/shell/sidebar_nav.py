"""Collapsible enterprise left navigation with CCTech branding."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.theme.cctech_theme import CCTechPalette
from smartinstall.ui.widgets.avatar_label import icon_pixmap

_EXPANDED_W = 260
_COLLAPSED_W = 72
_ANIM_MS = 200


class SidebarNav(QFrame):
    """Branded collapsible sidebar with sectioned navigation."""

    page_selected = Signal(int)
    collapsed_changed = Signal(bool)

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._collapsed = False
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: list[QPushButton] = []
        self._labels_to_hide: list[QWidget] = []
        self._width_anim: QPropertyAnimation | None = None
        self.setObjectName("sidebarNav")
        self._set_width(_EXPANDED_W)
        self._build_ui()

    def _set_width(self, width: int) -> None:
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

    def _build_ui(self) -> None:
        p = self._palette
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        brand = QWidget()
        brand.setObjectName("sidebarBrand")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(16, 18, 16, 14)
        brand_layout.setSpacing(0)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)
        self._logo = QLabel()
        self._logo.setPixmap(load_brand_logo_pixmap(40))
        self._logo.setFixedSize(40, 40)
        self._logo.setStyleSheet("background: transparent;")
        logo_row.addWidget(self._logo, alignment=Qt.AlignmentFlag.AlignVCenter)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(2)
        self._company_lbl = QLabel("CCTech")
        self._company_lbl.setObjectName("sidebarCompany")
        self._product_lbl = QLabel("Smart Installer AI")
        self._product_lbl.setObjectName("sidebarProduct")
        brand_text.addWidget(self._company_lbl)
        brand_text.addWidget(self._product_lbl)
        self._labels_to_hide.extend([self._company_lbl, self._product_lbl])
        logo_row.addLayout(brand_text, stretch=1)
        brand_layout.addLayout(logo_row)
        root.addWidget(brand)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {p.sidebar_border};")
        root.addWidget(div)

        body = QWidget()
        body.setObjectName("sidebarBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 14, 10, 12)
        body_layout.setSpacing(4)

        self._section_nav = self._section_label("NAVIGATE")
        body_layout.addWidget(self._section_nav)
        self._labels_to_hide.append(self._section_nav)

        nav_labels = (
            "Dashboard",
            "Monitoring",
            "Troubleshooting",
            "Install Center",
            "Full Chat",
        )
        icons = ("system.svg", "system.svg", "assistant.svg", "system.svg", "chatbot.svg")
        for idx, (label, icon_name) in enumerate(zip(nav_labels, icons, strict=True)):
            btn = self._nav_button(label, icon_name, idx)
            self._nav_buttons.append(btn)
            body_layout.addWidget(btn)

        body_layout.addStretch(1)

        self._collapse_btn = QToolButton()
        self._collapse_btn.setObjectName("sidebarCollapse")
        self._collapse_btn.setToolTip("Collapse sidebar")
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.clicked.connect(self.toggle_collapsed)
        self._update_collapse_button_ui()
        body_layout.addWidget(self._collapse_btn)

        root.addWidget(body, stretch=1)
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        p = self._palette
        self.setStyleSheet(
            f"""
            QFrame#sidebarNav {{
                background: {p.sidebar_bg};
                border-right: 1px solid {p.sidebar_border};
            }}
            QWidget#sidebarBrand, QWidget#sidebarBody {{
                background: transparent;
            }}
            QLabel#sidebarCompany {{
                color: {p.blue_500};
                font-size: 9.5pt;
                font-weight: 600;
                background: transparent;
            }}
            QLabel#sidebarProduct {{
                color: {p.text_inverse};
                font-size: 11pt;
                font-weight: 600;
                background: transparent;
            }}
            QLabel#sidebarSection {{
                color: {p.text_muted_inverse};
                font-size: 7.5pt;
                font-weight: 600;
                letter-spacing: 1.5px;
                padding: 4px 4px 2px 4px;
                background: transparent;
            }}
            QPushButton#sidebarNav {{
                background: transparent;
                color: {p.sidebar_text};
                border: none;
                border-radius: 8px;
                padding: 11px 12px;
                text-align: left;
                font-size: 9.5pt;
                font-weight: 500;
            }}
            QPushButton#sidebarNav:hover {{
                background: {p.sidebar_surface};
                color: {p.text_inverse};
            }}
            QPushButton#sidebarNav:checked {{
                background: {p.sidebar_surface};
                color: {p.sidebar_text_active};
                font-weight: 600;
                border-left: 3px solid {p.blue_600};
            }}
            QToolButton#sidebarCollapse {{
                background: {p.sidebar_surface};
                color: {p.text_inverse};
                border: 1px solid {p.sidebar_border};
                border-radius: 8px;
                padding: 10px;
                font-size: 9pt;
                font-weight: 500;
            }}
            QToolButton#sidebarCollapse:hover {{
                background: {p.navy_800};
                border-color: {p.blue_500};
            }}
            """
        )

    def toggle_collapsed(self) -> None:
        target = _COLLAPSED_W if not self._collapsed else _EXPANDED_W
        self._animate_width(target)

    def _animate_width(self, target: int) -> None:
        if self._width_anim is not None and self._width_anim.state() == QPropertyAnimation.State.Running:
            self._width_anim.stop()

        self._width_anim = QPropertyAnimation(self, b"minimumWidth", self)
        self._width_anim.setDuration(_ANIM_MS)
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(target)
        self._width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _sync_width(value: object) -> None:
            w = int(value)
            self._set_width(w)

        self._width_anim.valueChanged.connect(_sync_width)
        self._width_anim.finished.connect(lambda: self._on_width_done(target))
        self._width_anim.start()

    def _on_width_done(self, target: int) -> None:
        self._collapsed = target <= _COLLAPSED_W
        self._set_width(target)
        for widget in self._labels_to_hide:
            widget.setVisible(not self._collapsed)
        nav_labels = (
            "Dashboard",
            "Monitoring",
            "Troubleshooting",
            "Install Center",
            "Full Chat",
        )
        if self._collapsed:
            for btn in self._nav_buttons:
                btn.setText("")
        else:
            for btn, label in zip(self._nav_buttons, nav_labels, strict=True):
                btn.setText(f"  {label}")
        self._update_collapse_button_ui()
        self.collapsed_changed.emit(self._collapsed)

    def _update_collapse_button_ui(self) -> None:
        if self._collapsed:
            self._collapse_btn.setText("☰")
            self._collapse_btn.setToolTip("Expand sidebar")
        else:
            self._collapse_btn.setText("  ◀  Collapse")
            self._collapse_btn.setToolTip("Collapse sidebar")

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sidebarSection")
        lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return lbl

    def _nav_button(self, text: str, icon_name: str, page_index: int) -> QPushButton:
        btn = QPushButton(f"  {text}")
        btn.setObjectName("sidebarNav")
        btn.setIcon(QIcon(icon_pixmap(icon_name, 18)))
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nav_group.addButton(btn, page_index)
        btn.clicked.connect(lambda checked=False, i=page_index: self.page_selected.emit(i))
        return btn

    def set_active_page(self, index: int) -> None:
        btn = self._nav_group.button(index)
        if btn is not None:
            btn.setChecked(True)
