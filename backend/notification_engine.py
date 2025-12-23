"""
Notification Engine - Processa eventos e dispara notificações baseadas em regras
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from models import EventData


class NotificationEngine:
    """
    Motor de notificações que avalia eventos contra regras configuradas
    """

    def __init__(self):
        self._rules_cache = []
        self._cache_timestamp = None

    async def process_new_event(self, event: EventData, db_manager) -> List[int]:
        """
        Processa um novo evento e cria notificações se match com regras.
        Retorna lista de IDs de notificações criadas.
        """
        # Get active rules of type 'new_event'
        rules = await db_manager.get_notification_rules(active_only=True)
        new_event_rules = [r for r in rules if r["rule_type"] == "new_event"]

        notifications_created = []

        for rule in new_event_rules:
            if self._event_matches_rule(event, rule):
                # Create notification
                notification_id = await db_manager.create_notification({
                    "rule_id": rule["id"],
                    "notification_type": "new_event",
                    "event_reference": event.reference,
                    "event_titulo": event.titulo,
                    "event_tipo": event.tipo,
                    "event_subtipo": event.subtipo,
                    "event_distrito": event.distrito,
                    "preco_atual": event.lance_atual or event.valor_base
                })

                # Increment rule trigger count
                await db_manager.increment_rule_triggers(rule["id"])

                notifications_created.append(notification_id)
                print(f"  🔔 Notificação criada: {event.reference} (regra: {rule['name']})")

        return notifications_created

    async def process_price_change(
        self,
        event: EventData,
        old_price: float,
        new_price: float,
        db_manager
    ) -> List[int]:
        """
        Processa uma alteração de preço e cria notificações se match com regras.
        """
        # Get active rules of type 'price_change'
        rules = await db_manager.get_notification_rules(active_only=True)
        price_rules = [r for r in rules if r["rule_type"] == "price_change"]

        notifications_created = []
        variacao = new_price - old_price

        for rule in price_rules:
            # Check if variation meets minimum threshold
            variacao_min = rule.get("variacao_min")
            if variacao_min is not None:
                # If variacao_min is negative, we're looking for drops
                if variacao_min < 0 and variacao > variacao_min:
                    continue
                # If variacao_min is positive, we're looking for increases
                elif variacao_min > 0 and variacao < variacao_min:
                    continue

            # Check other filters
            if self._event_matches_rule(event, rule):
                notification_id = await db_manager.create_notification({
                    "rule_id": rule["id"],
                    "notification_type": "price_change",
                    "event_reference": event.reference,
                    "event_titulo": event.titulo,
                    "event_tipo": event.tipo,
                    "event_subtipo": event.subtipo,
                    "event_distrito": event.distrito,
                    "preco_anterior": old_price,
                    "preco_atual": new_price,
                    "preco_variacao": variacao
                })

                await db_manager.increment_rule_triggers(rule["id"])
                notifications_created.append(notification_id)
                print(f"  🔔 Notificação preço: {event.reference} ({old_price} -> {new_price})")

        return notifications_created

    def _event_matches_rule(self, event: EventData, rule: dict) -> bool:
        """
        Verifica se um evento corresponde aos filtros de uma regra.
        """
        # Check tipos filter
        if rule.get("tipos"):
            event_tipo = self._normalize_tipo(event.tipo_id, event.tipo)
            if event_tipo not in rule["tipos"]:
                return False

        # Check subtipos filter
        if rule.get("subtipos"):
            if not event.subtipo or event.subtipo not in rule["subtipos"]:
                return False

        # Check distritos filter
        if rule.get("distritos"):
            if not event.distrito or event.distrito not in rule["distritos"]:
                return False

        # Check concelhos filter
        if rule.get("concelhos"):
            if not event.concelho or event.concelho not in rule["concelhos"]:
                return False

        # Check price range
        preco = event.lance_atual or event.valor_base or 0

        if rule.get("preco_min") is not None:
            if preco < rule["preco_min"]:
                return False

        if rule.get("preco_max") is not None:
            if preco > rule["preco_max"]:
                return False

        return True

    def _normalize_tipo(self, tipo_id: Optional[int], tipo_str: Optional[str]) -> str:
        """
        Normaliza o tipo de evento para string consistente.
        """
        tipo_map = {
            1: "imoveis",
            2: "veiculos",
            3: "equipamentos",
            4: "mobiliario",
            5: "maquinas",
            6: "direitos"
        }

        if tipo_id and tipo_id in tipo_map:
            return tipo_map[tipo_id]

        # Fallback to tipo string
        if tipo_str:
            tipo_lower = tipo_str.lower()
            if "imov" in tipo_lower or "apart" in tipo_lower or "morad" in tipo_lower:
                return "imoveis"
            if "veic" in tipo_lower or "auto" in tipo_lower:
                return "veiculos"

        return "outros"


# Global singleton
_notification_engine = None


def get_notification_engine() -> NotificationEngine:
    """Get or create global notification engine instance"""
    global _notification_engine
    if _notification_engine is None:
        _notification_engine = NotificationEngine()
    return _notification_engine


async def process_new_events_batch(events: List[EventData], db_manager) -> int:
    """
    Processa um batch de novos eventos (chamado pelo Y-Sync).
    Retorna número total de notificações criadas.
    """
    engine = get_notification_engine()
    total_notifications = 0

    for event in events:
        notifications = await engine.process_new_event(event, db_manager)
        total_notifications += len(notifications)

    return total_notifications
