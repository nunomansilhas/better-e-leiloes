"""
Notification Engine - Processa eventos e dispara notificações baseadas em regras

Optimizations:
- Rules cache with TTL (avoid repeated DB queries)
- Duplicate notification prevention
- Batch processing with asyncio.gather()
- DB-level filtering by rule type
- ending_soon notifications support
"""
import asyncio
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from models import EventData


class NotificationEngine:
    """
    Motor de notificações que avalia eventos contra regras configuradas
    """

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    def __init__(self):
        self._rules_cache: Dict[str, List[dict]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    async def _get_rules_cached(self, rule_type: str, db_manager) -> List[dict]:
        """
        Get rules from cache or DB. Cache invalidates after CACHE_TTL seconds.
        """
        now = datetime.now()
        cache_key = rule_type

        # Check if cache is valid
        if cache_key in self._rules_cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if cache_time and (now - cache_time).total_seconds() < self.CACHE_TTL:
                return self._rules_cache[cache_key]

        # Fetch from DB (filtered by type - more efficient)
        rules = await db_manager.get_notification_rules_by_type(rule_type, active_only=True)

        # Update cache
        self._rules_cache[cache_key] = rules
        self._cache_timestamps[cache_key] = now

        return rules

    def invalidate_cache(self, rule_type: Optional[str] = None):
        """
        Invalidate rules cache. Call when rules are created/updated/deleted.
        """
        if rule_type:
            self._rules_cache.pop(rule_type, None)
            self._cache_timestamps.pop(rule_type, None)
        else:
            self._rules_cache.clear()
            self._cache_timestamps.clear()

    async def process_new_event(self, event: EventData, db_manager) -> List[int]:
        """
        Processa um novo evento e cria notificações se match com regras.
        Retorna lista de IDs de notificações criadas.
        """
        rules = await self._get_rules_cached("new_event", db_manager)
        if not rules:
            return []

        notifications_created = []

        # Process rules in parallel
        async def check_and_create(rule):
            if not self._event_matches_rule(event, rule):
                return None

            # Check for duplicates (prevent same notification within 24h)
            if await db_manager.notification_exists(
                rule["id"], event.reference, "new_event", hours=24
            ):
                return None

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
            print(f"  🔔 Notificação criada: {event.reference} (regra: {rule['name']})")

            return notification_id

        # Run all checks in parallel
        results = await asyncio.gather(*[check_and_create(r) for r in rules], return_exceptions=True)

        for result in results:
            if result is not None and not isinstance(result, Exception):
                notifications_created.append(result)

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
        print(f"  📊 Processing price change: {event.reference} ({old_price} -> {new_price})")
        rules = await self._get_rules_cached("price_change", db_manager)
        print(f"  📊 Found {len(rules)} price_change rules")
        if not rules:
            return []

        notifications_created = []
        variacao = new_price - old_price

        async def check_and_create(rule):
            # Check if variation meets minimum threshold
            variacao_min = rule.get("variacao_min")
            if variacao_min is not None:
                if variacao_min < 0 and variacao > variacao_min:
                    print(f"    ❌ Rule {rule['name']}: variation {variacao} > min {variacao_min}")
                    return None
                elif variacao_min > 0 and variacao < variacao_min:
                    print(f"    ❌ Rule {rule['name']}: variation {variacao} < min {variacao_min}")
                    return None

            if not self._event_matches_rule(event, rule):
                print(f"    ❌ Rule {rule['name']}: event doesn't match filters")
                return None

            # Instant notification - no cooldown for price changes
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
            print(f"  🔔 Notificação preço: {event.reference} ({old_price} -> {new_price})")

            return notification_id

        results = await asyncio.gather(*[check_and_create(r) for r in rules], return_exceptions=True)

        for result in results:
            if result is not None and not isinstance(result, Exception):
                notifications_created.append(result)

        return notifications_created

    async def process_ending_soon(
        self,
        event: EventData,
        minutes_remaining: int,
        db_manager
    ) -> List[int]:
        """
        Processa eventos que estão prestes a terminar.
        Cria notificações para regras 'ending_soon' se os minutos restantes
        são menores ou iguais ao configurado na regra.
        """
        rules = await self._get_rules_cached("ending_soon", db_manager)
        if not rules:
            return []

        notifications_created = []

        async def check_and_create(rule):
            # Check if event is within the notification window
            rule_minutes = rule.get("minutos_restantes", 60)
            if minutes_remaining > rule_minutes:
                return None

            if not self._event_matches_rule(event, rule):
                return None

            # Check for duplicates (prevent same notification within the rule's window)
            # Use the rule's minutes as the dedup window
            dedup_hours = max(1, rule_minutes // 60)
            if await db_manager.notification_exists(
                rule["id"], event.reference, "ending_soon", hours=dedup_hours
            ):
                return None

            notification_id = await db_manager.create_notification({
                "rule_id": rule["id"],
                "notification_type": "ending_soon",
                "event_reference": event.reference,
                "event_titulo": event.titulo,
                "event_tipo": event.tipo,
                "event_subtipo": event.subtipo,
                "event_distrito": event.distrito,
                "preco_atual": event.lance_atual or event.valor_base
            })

            await db_manager.increment_rule_triggers(rule["id"])
            print(f"  ⏰ Notificação ending_soon: {event.reference} ({minutes_remaining}min restantes)")

            return notification_id

        results = await asyncio.gather(*[check_and_create(r) for r in rules], return_exceptions=True)

        for result in results:
            if result is not None and not isinstance(result, Exception):
                notifications_created.append(result)

        return notifications_created

    def _event_matches_rule(self, event: EventData, rule: dict) -> bool:
        """
        Verifica se um evento corresponde aos filtros de uma regra.
        """
        # Check event_reference for event-specific rules
        event_ref = rule.get("event_reference")
        if event_ref:
            # If event-specific rule, check reference AND other filters (AND logic)
            if event.reference != event_ref:
                return False
            # Continue to check other filters (don't early return)

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
            if "equip" in tipo_lower:
                return "equipamentos"
            if "mobil" in tipo_lower:
                return "mobiliario"
            if "maq" in tipo_lower:
                return "maquinas"
            if "direit" in tipo_lower:
                return "direitos"

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

    # Process events in parallel batches of 10
    batch_size = 10
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        results = await asyncio.gather(
            *[engine.process_new_event(event, db_manager) for event in batch],
            return_exceptions=True
        )
        for result in results:
            if isinstance(result, list):
                total_notifications += len(result)

    return total_notifications


async def process_ending_soon_batch(events: List[EventData], db_manager) -> int:
    """
    Processa um batch de eventos a terminar (chamado pelo X-Monitor).
    Retorna número total de notificações criadas.
    """
    engine = get_notification_engine()
    total_notifications = 0
    now = datetime.now()

    for event in events:
        if not event.data_fim:
            continue

        # Calculate minutes remaining
        remaining = event.data_fim - now
        minutes_remaining = int(remaining.total_seconds() / 60)

        if minutes_remaining <= 0:
            continue

        try:
            notifications = await engine.process_ending_soon(event, minutes_remaining, db_manager)
            total_notifications += len(notifications)
        except Exception as e:
            print(f"  ❌ Erro ending_soon {event.reference}: {str(e)[:50]}")

    return total_notifications


async def create_event_ended_notification(event_data: dict, db_manager) -> Optional[int]:
    """
    Cria uma notificação quando um evento termina.
    Inclui dados finais: último lance, data de fim, etc.

    Args:
        event_data: Dict com reference, titulo, tipo, subtipo, distrito, lance_atual, data_fim
        db_manager: Database manager instance

    Returns:
        notification_id if created, None otherwise
    """
    try:
        ref = event_data.get('reference')
        if not ref:
            return None

        # Check if notification already exists for this event ending (prevent duplicates)
        if await db_manager.notification_exists(
            rule_id=None,  # System notification, not rule-based
            event_reference=ref,
            notification_type="event_ended",
            hours=24
        ):
            return None

        # Create notification with final event data
        notification_id = await db_manager.create_notification({
            "rule_id": None,  # System notification
            "notification_type": "event_ended",
            "event_reference": ref,
            "event_titulo": event_data.get('titulo', ''),
            "event_tipo": event_data.get('tipo', ''),
            "event_subtipo": event_data.get('subtipo', ''),
            "event_distrito": event_data.get('distrito', ''),
            "preco_atual": event_data.get('lance_atual') or event_data.get('valor_base', 0),
            "preco_anterior": event_data.get('valor_base', 0),  # Store base value for reference
        })

        print(f"  🏁 Notificação evento terminado: {ref}")
        return notification_id

    except Exception as e:
        print(f"  ❌ Erro criar notificação event_ended {event_data.get('reference', '?')}: {str(e)[:50]}")
        return None


async def cleanup_old_notifications(db_manager, days: int = 30) -> int:
    """
    Remove notificações antigas (chamado periodicamente).
    """
    try:
        deleted = await db_manager.delete_old_notifications(days=days)
        if deleted > 0:
            print(f"🗑️ {deleted} notificações antigas removidas (>{days} dias)")
        return deleted
    except Exception as e:
        print(f"❌ Erro ao limpar notificações: {str(e)}")
        return 0
