"""Lightweight UI animations for page transitions and install feedback."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QParallelAnimationGroup, QSequentialAnimationGroup
from PySide6.QtWidgets import QWidget


def fade_in(widget: QWidget, *, duration_ms: int = 280) -> QPropertyAnimation:
    """Fade widget opacity from 0 to 1."""
    effect = widget.graphicsEffect()
    if effect is None:
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration_ms)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    return animation


def slide_fade_in(widget: QWidget, *, duration_ms: int = 320) -> QParallelAnimationGroup:
    """Combined fade + slight vertical slide for page enter."""
    group = QParallelAnimationGroup(widget)
    opacity = fade_in(widget, duration_ms=duration_ms)
    geometry = widget.geometry()
    slide = QPropertyAnimation(widget, b"geometry", widget)
    slide.setDuration(duration_ms)
    slide.setStartValue(geometry.adjusted(0, 12, 0, 12))
    slide.setEndValue(geometry)
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(opacity)
    group.addAnimation(slide)
    return group


def shake_widget(widget: QWidget, *, duration_ms: int = 480) -> QSequentialAnimationGroup:
    """Horizontal shake for error / failure feedback."""
    group = QSequentialAnimationGroup(widget)
    base = widget.pos()
    offsets = (-10, 10, -8, 8, -4, 4, 0)
    step_ms = max(40, duration_ms // len(offsets))
    for dx in offsets:
        anim = QPropertyAnimation(widget, b"pos", widget)
        anim.setDuration(step_ms)
        anim.setStartValue(base)
        anim.setEndValue(QPoint(base.x() + dx, base.y()))
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        group.addAnimation(anim)
    return group


def pulse_opacity(widget: QWidget, *, duration_ms: int = 900) -> QSequentialAnimationGroup:
    """Soft pulse on widget opacity (busy indicators)."""
    from PySide6.QtWidgets import QGraphicsOpacityEffect

    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    group = QSequentialAnimationGroup(widget)
    for start, end in ((1.0, 0.55), (0.55, 1.0)):
        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration_ms // 2)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(anim)
    group.setLoopCount(-1)
    return group
