"""Regelwerk und Regelauswertung.

Platzhalter für die Regelausführung. Vorgesehen ist ein leichtgewichtiger
Mechanismus, der einzelne Regeln auf die Daten anwendet und die Ergebnisse
(Regelverstösse samt Begründung) einheitlich zurückgibt.

Designidee für die spätere Umsetzung:

* Jede Regel ist eine klar abgegrenzte, einzeln testbare Einheit.
* Neue Regeln lassen sich hinzufügen, ohne bestehende zu verändern.

Die konkreten Regeln und Datenstrukturen werden bewusst noch nicht festgelegt.
"""

from __future__ import annotations


def evaluate(data: object) -> object:
    """Wendet die Regeln auf die Daten an.

    Args:
        data: Die zu prüfenden Artikel-/Attributdaten.

    Returns:
        Später eine Sammlung nachvollziehbarer Regelverstösse/Vorschläge.

    Raises:
        NotImplementedError: Solange die Regelprüfung noch nicht implementiert
            ist.
    """
    raise NotImplementedError("Regelprüfung ist noch nicht implementiert.")
