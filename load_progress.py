"""Presentación del progreso de carga sin alterar el procesamiento de datos."""

from __future__ import annotations

from time import perf_counter
from typing import Callable
from uuid import uuid4

import streamlit as st


_LIVE_TIMER_HTML = (
    '<div class="load-timer" aria-live="polite">'
    "Tiempo transcurrido: <span>0.0 s</span></div>"
)
_LIVE_TIMER_CSS = """
.load-timer {
    color: var(--st-text-color);
    font-family: Inter, sans-serif;
    font-size: 0.875rem;
    line-height: 1.4;
    opacity: 0.78;
    padding: 0.15rem 0 0.4rem;
}
"""
_LIVE_TIMER_JS = """
export default function(component) {
    const { parentElement } = component;
    const output = parentElement.querySelector(".load-timer span");
    const startedAt = performance.now();

    const update = () => {
        const elapsed = (performance.now() - startedAt) / 1000;
        output.textContent = `${elapsed.toFixed(1)} s`;
    };

    update();
    const intervalId = window.setInterval(update, 100);
    return () => window.clearInterval(intervalId);
}
"""


def _live_timer_component():
    """Registra el componente en el runtime activo antes de montarlo."""
    return st.components.v2.component(
        "load_elapsed_timer",
        html=_LIVE_TIMER_HTML,
        css=_LIVE_TIMER_CSS,
        js=_LIVE_TIMER_JS,
    )


class LiveElapsedTimer:
    """Cronómetro visual que continúa mientras Python ejecuta una llamada bloqueante."""

    def __init__(self, container):
        self._slot = container.empty()
        with self._slot:
            _live_timer_component()(key=f"load-timer-{uuid4().hex}")

    def stop(self, elapsed: float) -> None:
        """Sustituye el contador cliente por el tiempo final medido en Python."""
        self._slot.caption(f"Tiempo transcurrido: {elapsed:.1f} s")


class LoadProgress:
    """Coordina ``st.status`` y ``st.progress`` con hitos monotónicos."""

    def __init__(
        self,
        status,
        progress_bar,
        clock: Callable[[], float] = perf_counter,
        live_timer=None,
    ):
        self._status = status
        self._bar = progress_bar
        self._clock = clock
        self._started_at = clock()
        self._stage_started_at = self._started_at
        self._percent = 0
        self._live_timer = live_timer
        self.failed = False

    @property
    def percent(self) -> int:
        return self._percent

    def start_stage(self, label: str, *, indeterminate: bool = False) -> None:
        """Anuncia una operación sin inventar avance dentro de ella."""
        if self.failed:
            return
        self._stage_started_at = self._clock()
        detail = " Avance interno indeterminado." if indeterminate else ""
        elapsed = self._stage_started_at - self._started_at
        text = f"**{self._percent}%** · {label}.{detail} Tiempo transcurrido: {elapsed:.1f} s"
        self._bar.progress(self._percent, text=text)
        self._status.update(label=label, state="running", expanded=True)

    def finish_stage(self, percent: int, label: str) -> None:
        """Completa un hito verificable y registra sus tiempos."""
        if self.failed:
            return
        if not 0 <= percent <= 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        self._percent = max(self._percent, percent)
        now = self._clock()
        stage_elapsed = now - self._stage_started_at
        total_elapsed = now - self._started_at
        self._bar.progress(
            self._percent,
            text=f"**{self._percent}%** · {label}. Tiempo transcurrido: {total_elapsed:.1f} s",
        )
        self._status.write(
            f":material/check_circle: {label} — {stage_elapsed:.1f} s "
            f"(acumulado: {total_elapsed:.1f} s)"
        )

    def fail(self, label: str) -> None:
        """Marca la etapa como fallida sin avanzar ni mostrar 100 %."""
        if self.failed:
            return
        self.failed = True
        elapsed = self._clock() - self._started_at
        if self._live_timer is not None:
            self._live_timer.stop(elapsed)
        self._bar.progress(
            self._percent,
            text=f"**{self._percent}%** · Carga interrumpida. Tiempo transcurrido: {elapsed:.1f} s",
        )
        self._status.write(f":material/error: {label} — {elapsed:.1f} s acumulados")
        self._status.update(label=label, state="error", expanded=True)

    def complete(self, label: str = "Carga finalizada") -> None:
        """Alcanza 100 % solo cuando todo el flujo incluido terminó."""
        if self.failed:
            return
        self._percent = 100
        elapsed = self._clock() - self._started_at
        if self._live_timer is not None:
            self._live_timer.stop(elapsed)
        self._bar.progress(100, text=f"**100%** · {label}. Tiempo total: {elapsed:.1f} s")
        self._status.write(f":material/task_alt: {label} — {elapsed:.1f} s en total")
        self._status.update(label=f"{label} en {elapsed:.1f} s", state="complete", expanded=False)
