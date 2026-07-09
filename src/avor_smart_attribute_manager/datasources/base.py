"""Basisschnittstelle für externe Datenquellen.

Legt die gemeinsame Schnittstelle fest, die alle konkreten Datenquellen später
erfüllen müssen. Konkrete Implementierungen (z. B. Hersteller-Portale)
existieren im aktuellen Projektstand bewusst noch nicht.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DataSource(ABC):
    """Abstrakte Basisklasse für eine externe Datenquelle.

    Dient als stabiler Vertrag zwischen den Fachmodulen und beliebigen
    konkreten Datenquellen. Methoden-Signaturen werden bewusst minimal
    gehalten und erst bei Bedarf erweitert, um keine verfrühten Annahmen zu
    treffen.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Gibt an, ob die Datenquelle aktuell nutzbar ist.

        Returns:
            ``True``, wenn die Quelle erreichbar/verwendbar ist, sonst
            ``False``.
        """
        raise NotImplementedError
