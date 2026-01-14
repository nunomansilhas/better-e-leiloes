# -*- coding: utf-8 -*-
"""
Vehicle Data Pipeline
Processes vehicle auction events to enrich with market data and comparisons.

Features:
- Looks up vehicle info from InfoMatricula API (by matricula)
- Checks insurance status
- Fetches market prices for comparison
- Calculates potential savings
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_

from database import get_db, EventDB, EventVehicleDataDB
from services.vehicle_lookup import (
    lookup_plate_infomatricula_api,
    check_insurance_api,
    get_market_prices,
    decode_portuguese_plate,
)
from logger import log_info, log_error, log_warning


class VehiclePipelineManager:
    """
    Manager for vehicle data enrichment pipeline.
    Processes vehicle events to add market comparison data.
    """

    def __init__(self):
        self.is_running = False
        self._stop_requested = False
        self.current_reference: Optional[str] = None
        self.current_event_titulo: Optional[str] = None
        self.total_processed = 0
        self.total_failed = 0

    async def start(self):
        """Start the vehicle data pipeline"""
        if self.is_running:
            log_warning("Vehicle pipeline already running")
            return

        self.is_running = True
        self._stop_requested = False
        log_info("🚗 Vehicle data pipeline started")

        try:
            while not self._stop_requested:
                # Get next vehicle event to process
                event = await self._get_next_event()

                if not event:
                    log_info("Vehicle pipeline: No more events to process")
                    break

                self.current_reference = event['reference']
                self.current_event_titulo = event.get('titulo', '')

                try:
                    await self._process_event(event)
                    self.total_processed += 1
                except Exception as e:
                    log_error(f"Vehicle pipeline error for {event['reference']}: {e}")
                    await self._mark_failed(event['reference'], str(e))
                    self.total_failed += 1

                # Small delay between events
                await asyncio.sleep(1)

        finally:
            self.is_running = False
            self.current_reference = None
            self.current_event_titulo = None
            log_info(f"🚗 Vehicle pipeline stopped. Processed: {self.total_processed}, Failed: {self.total_failed}")

    async def stop(self):
        """Stop the pipeline gracefully"""
        self._stop_requested = True
        log_info("Vehicle pipeline stop requested")

    async def _get_next_event(self) -> Optional[Dict[str, Any]]:
        """
        Get next vehicle event to process.
        Priority:
        1. Events with matricula that haven't been processed
        2. Events ending soonest first
        """
        async with get_db() as db:
            # Get events that:
            # - Are vehicles (tipo_id=2)
            # - Have a matricula
            # - Are not terminated/cancelled
            # - Haven't been processed yet (not in event_vehicle_data or status=pending)
            subquery = select(EventVehicleDataDB.reference).where(
                EventVehicleDataDB.status.in_(['completed', 'processing'])
            )

            query = (
                select(EventDB)
                .where(
                    and_(
                        EventDB.tipo_id == 2,  # Veículos
                        EventDB.matricula.isnot(None),
                        EventDB.matricula != '',
                        EventDB.terminado == False,
                        EventDB.cancelado == False,
                        EventDB.reference.notin_(subquery)
                    )
                )
                .order_by(EventDB.data_fim.asc())
                .limit(1)
            )

            result = await db.session.execute(query)
            event = result.scalar_one_or_none()

            if event:
                return {
                    'reference': event.reference,
                    'titulo': event.titulo,
                    'matricula': event.matricula,
                    'valor_base': float(event.valor_base) if event.valor_base else None,
                    'lance_atual': float(event.lance_atual) if event.lance_atual else None,
                    'descricao': event.descricao,
                }

            return None

    async def _process_event(self, event: Dict[str, Any]):
        """Process a single vehicle event"""
        reference = event['reference']
        matricula = event['matricula']

        log_info(f"🚗 Processing vehicle: {reference} - {matricula}")

        async with get_db() as db:
            # Create or get existing record
            existing = await db.session.execute(
                select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
            )
            vehicle_data = existing.scalar_one_or_none()

            if not vehicle_data:
                vehicle_data = EventVehicleDataDB(
                    reference=reference,
                    matricula=matricula,
                    event_titulo=event.get('titulo'),
                    event_valor_base=event.get('valor_base'),
                    event_lance_atual=event.get('lance_atual'),
                    status='processing'
                )
                db.session.add(vehicle_data)
            else:
                vehicle_data.status = 'processing'

            await db.session.commit()

        # 1. Lookup vehicle info from InfoMatricula API
        vehicle_info = await lookup_plate_infomatricula_api(matricula)

        if 'error' not in vehicle_info:
            async with get_db() as db:
                result = await db.session.execute(
                    select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                )
                vehicle_data = result.scalar_one()

                vehicle_data.marca = vehicle_info.get('marca')
                vehicle_data.modelo = vehicle_info.get('modelo')
                vehicle_data.versao = vehicle_info.get('versao')
                vehicle_data.ano = vehicle_info.get('ano')
                vehicle_data.combustivel = vehicle_info.get('combustivel')
                vehicle_data.potencia_cv = vehicle_info.get('potencia_cv')
                vehicle_data.potencia_kw = vehicle_info.get('potencia_kw')
                vehicle_data.cor = vehicle_info.get('cor')
                vehicle_data.categoria = vehicle_info.get('categoria')
                vehicle_data.vin = vehicle_info.get('vin')
                vehicle_data.tipo_proprietario = vehicle_info.get('tipo_proprietario')
                vehicle_data.origem = vehicle_info.get('origem')

                await db.session.commit()

            log_info(f"  ✅ Vehicle info: {vehicle_info.get('marca')} {vehicle_info.get('modelo')} ({vehicle_info.get('ano')})")

        # 2. Check insurance status
        insurance_info = await check_insurance_api(matricula)

        if 'error' not in insurance_info:
            async with get_db() as db:
                result = await db.session.execute(
                    select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                )
                vehicle_data = result.scalar_one()

                vehicle_data.tem_seguro = insurance_info.get('tem_seguro')
                vehicle_data.seguradora = insurance_info.get('seguradora')
                vehicle_data.seguro_apolice = insurance_info.get('apolice')
                vehicle_data.seguro_data_fim = insurance_info.get('data_fim')

                await db.session.commit()

            log_info(f"  🛡️ Insurance: {'Valid' if insurance_info.get('tem_seguro') else 'No'}")

        # 3. Get market prices (if we have vehicle info)
        if 'error' not in vehicle_info and vehicle_info.get('marca'):
            # Extract km from description if available
            km = self._extract_km_from_description(event.get('descricao', ''))

            market_data = await get_market_prices(
                marca=vehicle_info.get('marca'),
                modelo=vehicle_info.get('modelo'),
                ano=vehicle_info.get('ano'),
                combustivel=vehicle_info.get('combustivel'),
                km=km,
                debug=False
            )

            if market_data:
                async with get_db() as db:
                    result = await db.session.execute(
                        select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                    )
                    vehicle_data = result.scalar_one()

                    vehicle_data.market_num_resultados = market_data.num_resultados
                    vehicle_data.market_preco_min = market_data.preco_min
                    vehicle_data.market_preco_max = market_data.preco_max
                    vehicle_data.market_preco_medio = market_data.preco_medio
                    vehicle_data.market_preco_mediana = market_data.preco_mediana
                    vehicle_data.market_fonte = market_data.fonte
                    vehicle_data.market_listings = json.dumps(market_data.listings[:10])  # Store top 10

                    # Calculate savings
                    valor_leilao = event.get('valor_base') or event.get('lance_atual') or 0
                    if valor_leilao > 0 and market_data.preco_medio > 0:
                        vehicle_data.poupanca_estimada = market_data.preco_medio - valor_leilao
                        vehicle_data.desconto_percentagem = ((market_data.preco_medio - valor_leilao) / market_data.preco_medio) * 100

                    await db.session.commit()

                log_info(f"  💰 Market: {market_data.num_resultados} listings, avg €{market_data.preco_medio:,.0f}")

        # Mark as completed
        async with get_db() as db:
            result = await db.session.execute(
                select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
            )
            vehicle_data = result.scalar_one()

            vehicle_data.status = 'completed'
            vehicle_data.processed_at = datetime.utcnow()

            await db.session.commit()

        log_info(f"  ✅ Completed: {reference}")

    async def _mark_failed(self, reference: str, error: str):
        """Mark event as failed"""
        async with get_db() as db:
            result = await db.session.execute(
                select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
            )
            vehicle_data = result.scalar_one_or_none()

            if vehicle_data:
                vehicle_data.status = 'failed'
                vehicle_data.error_message = error[:500]
                vehicle_data.updated_at = datetime.utcnow()
            else:
                vehicle_data = EventVehicleDataDB(
                    reference=reference,
                    status='failed',
                    error_message=error[:500]
                )
                db.session.add(vehicle_data)

            await db.session.commit()

    def _extract_km_from_description(self, descricao: str) -> Optional[int]:
        """Try to extract kilometers from event description"""
        import re

        if not descricao:
            return None

        # Common patterns: "123.456 km", "123456km", "123 456 Km"
        patterns = [
            r'(\d{1,3}[.\s]?\d{3})\s*km',  # 123.456 km or 123456 km
            r'quilometr[ao]gem[:\s]+(\d{1,3}[.\s]?\d{3})',  # quilometragem: 123456
            r'(\d{1,3}[.\s]?\d{3})\s*quilómetros',  # 123456 quilómetros
        ]

        for pattern in patterns:
            match = re.search(pattern, descricao.lower())
            if match:
                km_str = match.group(1).replace('.', '').replace(' ', '')
                try:
                    return int(km_str)
                except:
                    pass

        return None

    async def process_single(self, reference: str) -> Dict[str, Any]:
        """Process a single event by reference (for manual/API trigger)"""
        async with get_db() as db:
            result = await db.session.execute(
                select(EventDB).where(EventDB.reference == reference)
            )
            event = result.scalar_one_or_none()

            if not event:
                return {'error': f'Event {reference} not found'}

            if not event.matricula:
                return {'error': f'Event {reference} has no matricula'}

            event_dict = {
                'reference': event.reference,
                'titulo': event.titulo,
                'matricula': event.matricula,
                'valor_base': float(event.valor_base) if event.valor_base else None,
                'lance_atual': float(event.lance_atual) if event.lance_atual else None,
                'descricao': event.descricao,
            }

        try:
            await self._process_event(event_dict)
            return {'status': 'completed', 'reference': reference}
        except Exception as e:
            return {'error': str(e)}


# Singleton instance
_vehicle_pipeline_manager: Optional[VehiclePipelineManager] = None


def get_vehicle_pipeline_manager() -> VehiclePipelineManager:
    """Get the singleton vehicle pipeline manager"""
    global _vehicle_pipeline_manager
    if _vehicle_pipeline_manager is None:
        _vehicle_pipeline_manager = VehiclePipelineManager()
    return _vehicle_pipeline_manager
