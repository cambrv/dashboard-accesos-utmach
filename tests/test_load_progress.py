from load_progress import LoadProgress


class _FakeStatus:
    def __init__(self):
        self.updates = []
        self.messages = []

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def write(self, message):
        self.messages.append(message)


class _FakeBar:
    def __init__(self):
        self.values = []

    def progress(self, value, text=None):
        self.values.append((value, text))


class _Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


class _FakeTimer:
    def __init__(self):
        self.stopped_at = []

    def stop(self, elapsed):
        self.stopped_at.append(elapsed)


def test_progress_never_moves_backwards_and_completes_at_100():
    status = _FakeStatus()
    bar = _FakeBar()
    progress = LoadProgress(status, bar, clock=_Clock())

    progress.start_stage("Lectura", indeterminate=True)
    progress.finish_stage(25, "Lectura completada")
    progress.finish_stage(12, "Hito fuera de orden")
    progress.complete()

    values = [value for value, _ in bar.values]
    assert values == sorted(values)
    assert values[-1] == 100
    assert "indeterminado" in bar.values[0][1]
    assert status.updates[-1]["state"] == "complete"


def test_failure_keeps_last_percentage_and_never_reports_complete():
    status = _FakeStatus()
    bar = _FakeBar()
    progress = LoadProgress(status, bar, clock=_Clock())

    progress.finish_stage(25, "Lectura completada")
    progress.fail("Error de lectura")
    progress.complete()

    assert progress.failed
    assert progress.percent == 25
    assert max(value for value, _ in bar.values) == 25
    assert status.updates[-1]["state"] == "error"


def test_live_timer_stops_on_success_and_failure():
    success_timer = _FakeTimer()
    success = LoadProgress(
        _FakeStatus(), _FakeBar(), clock=_Clock(), live_timer=success_timer
    )
    success.complete()

    failure_timer = _FakeTimer()
    failure = LoadProgress(
        _FakeStatus(), _FakeBar(), clock=_Clock(), live_timer=failure_timer
    )
    failure.fail("Error de lectura")

    assert len(success_timer.stopped_at) == 1
    assert len(failure_timer.stopped_at) == 1
