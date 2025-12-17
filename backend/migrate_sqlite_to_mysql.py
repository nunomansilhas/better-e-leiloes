"""
Migration script: SQLite → MySQL
Copies all events from SQLite database to MySQL database
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from database import EventDB, Base, DatabaseManager
from datetime import datetime

# Source: SQLite
SQLITE_URL = "sqlite+aiosqlite:///./eleiloes.db"

# Target: MySQL (from .env)
MYSQL_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:password@localhost:3306/eleiloes")

print("=" * 60)
print("🔄 SQLite → MySQL Migration")
print("=" * 60)
print(f"\n📂 Source (SQLite): {SQLITE_URL}")
print(f"📂 Target (MySQL):  {MYSQL_URL}")
print()

async def migrate():
    # Create engines
    sqlite_engine = create_async_engine(SQLITE_URL, echo=False)
    mysql_engine = create_async_engine(MYSQL_URL, echo=False)

    # Create session makers
    SQLiteSession = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)
    MySQLSession = async_sessionmaker(mysql_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # Step 1: Create tables in MySQL if they don't exist
        print("📋 Step 1: Creating MySQL tables...")
        async with mysql_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("   ✅ MySQL tables created/verified\n")

        # Step 2: Count events in SQLite
        print("📊 Step 2: Counting events in SQLite...")
        async with SQLiteSession() as session:
            result = await session.execute(select(EventDB))
            sqlite_events = result.scalars().all()
            total_events = len(sqlite_events)

        print(f"   Found {total_events} events in SQLite\n")

        if total_events == 0:
            print("⚠️  No events to migrate!")
            return

        # Step 3: Check if MySQL already has events
        print("📊 Step 3: Checking MySQL...")
        async with MySQLSession() as session:
            result = await session.execute(select(EventDB))
            mysql_events = result.scalars().all()
            existing_events = len(mysql_events)

        print(f"   MySQL currently has {existing_events} events\n")

        if existing_events > 0:
            response = input("⚠️  MySQL already has events. Overwrite? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ Migration cancelled")
                return

            print("\n🗑️  Clearing MySQL events table...")
            async with MySQLSession() as session:
                await session.execute("DELETE FROM events")
                await session.commit()
            print("   ✅ MySQL table cleared\n")

        # Step 4: Migrate events
        print(f"🚀 Step 4: Migrating {total_events} events to MySQL...")
        print("   This may take a few minutes...\n")

        migrated_count = 0
        error_count = 0

        async with MySQLSession() as mysql_session:
            for i, event in enumerate(sqlite_events, 1):
                try:
                    # Create new event object (detached from SQLite session)
                    new_event = EventDB(
                        reference=event.reference,
                        tipo_evento=event.tipo_evento,
                        valor_base=event.valor_base,
                        valor_abertura=event.valor_abertura,
                        valor_minimo=event.valor_minimo,
                        lance_atual=event.lance_atual,
                        latitude=event.latitude,
                        longitude=event.longitude,
                        tipo=event.tipo,
                        subtipo=event.subtipo,
                        tipologia=event.tipologia,
                        area_privativa=event.area_privativa,
                        area_dependente=event.area_dependente,
                        area_total=event.area_total,
                        distrito=event.distrito,
                        concelho=event.concelho,
                        freguesia=event.freguesia,
                        matricula=event.matricula,
                        data_inicio=event.data_inicio,
                        data_fim=event.data_fim,
                        imagens=event.imagens,
                        descricao=event.descricao,
                        observacoes=event.observacoes,
                        onuselimitacoes=event.onuselimitacoes,
                        descricao_predial=event.descricao_predial,
                        cerimonia_encerramento=event.cerimonia_encerramento,
                        agente_execucao=event.agente_execucao,
                        dados_processo=event.dados_processo,
                        scraped_at=event.scraped_at,
                        updated_at=event.updated_at
                    )

                    mysql_session.add(new_event)
                    migrated_count += 1

                    # Commit in batches of 100
                    if i % 100 == 0:
                        await mysql_session.commit()
                        print(f"   ✓ Migrated {i}/{total_events} events ({int(i/total_events*100)}%)")

                except Exception as e:
                    error_count += 1
                    print(f"   ⚠️  Error migrating {event.reference}: {e}")

            # Commit remaining
            await mysql_session.commit()

        # Step 5: Verify migration
        print(f"\n📊 Step 5: Verifying migration...")
        async with MySQLSession() as session:
            result = await session.execute(select(EventDB))
            final_count = len(result.scalars().all())

        print(f"   MySQL now has {final_count} events\n")

        # Summary
        print("=" * 60)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 60)
        print(f"Total events in SQLite: {total_events}")
        print(f"Successfully migrated:  {migrated_count}")
        print(f"Errors:                 {error_count}")
        print(f"Final count in MySQL:   {final_count}")
        print()

        if final_count == total_events:
            print("🎉 All events migrated successfully!")
        else:
            print(f"⚠️  Warning: Expected {total_events}, got {final_count}")

        print("\n💡 Next steps:")
        print("   1. Check phpMyAdmin to verify data")
        print("   2. Run: python test_db.py")
        print("   3. Start the server: python -m uvicorn main:app --reload")
        print()

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await sqlite_engine.dispose()
        await mysql_engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
