from typing import TYPE_CHECKING

from kpi.base.protocol import ObserverProtocol
from kpi.op.observer import LocalObserver, NoOpObserver, SentryObserver

if TYPE_CHECKING:
    _noop_observer: ObserverProtocol = NoOpObserver()

    _local_observer: ObserverProtocol = LocalObserver()

    _sentry_observer: ObserverProtocol = SentryObserver()
