"""
Comprehensive MySQL connection diagnostics
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

print("=" * 70)
print("🔍 MySQL Connection Diagnostics")
print("=" * 70)

# Step 1: Check .env file
print("\n📁 Step 1: Checking .env file...")
env_path = Path(".env")
if env_path.exists():
    print(f"   ✅ .env file found at: {env_path.absolute()}")

    # Read .env file
    with open(env_path, 'r') as f:
        env_content = f.read()

    # Check if DATABASE_URL is set
    if "DATABASE_URL" in env_content:
        print("   ✅ DATABASE_URL found in .env")

        # Show DATABASE_URL (masked password)
        for line in env_content.split('\n'):
            if line.startswith('DATABASE_URL'):
                # Mask password for display
                url = line.split('=', 1)[1]
                if '@' in url:
                    before_at = url.split('@')[0]
                    after_at = '@' + url.split('@')[1]
                    if ':' in before_at:
                        user = before_at.split(':')[0].split('//')[-1]
                        masked = f"{user}:***{after_at}"
                        print(f"   📝 DATABASE_URL={masked}")
                    else:
                        print(f"   📝 {line}")
                else:
                    print(f"   📝 {line}")
    else:
        print("   ⚠️  DATABASE_URL not found in .env")
        print("   Add this line to .env:")
        print("   DATABASE_URL=mysql+aiomysql://mansilh1_nuno:wcDR%25QY0BGYt@localhost:3306/eleiloes")
else:
    print("   ❌ .env file NOT found!")
    print(f"   Expected location: {env_path.absolute()}")
    print("\n   Create .env file with:")
    print("   DATABASE_URL=mysql+aiomysql://mansilh1_nuno:wcDR%25QY0BGYt@localhost:3306/eleiloes")

# Step 2: Load environment variables
print("\n🔧 Step 2: Loading environment variables...")
from dotenv import load_dotenv
load_dotenv()

database_url = os.getenv("DATABASE_URL")
if database_url:
    print(f"   ✅ DATABASE_URL loaded from environment")
    # Mask password
    if '@' in database_url:
        before_at = database_url.split('@')[0]
        after_at = '@' + database_url.split('@')[1]
        if ':' in before_at:
            user = before_at.split(':')[0].split('//')[-1]
            masked = f"{user}:***{after_at}"
            print(f"   📝 {masked}")
    else:
        print(f"   📝 {database_url}")
else:
    print("   ❌ DATABASE_URL not loaded from environment!")
    print("   Using default SQLite")

# Step 3: Test different password encodings
print("\n🧪 Step 3: Testing password encodings...")

username = "mansilh1_nuno"
password_raw = "wcDR%QY0BGYt"
password_encoded = quote_plus(password_raw)  # URL encode
host = "localhost"
port = 3306
database = "eleiloes"

print(f"   Raw password:     {password_raw}")
print(f"   Encoded password: {password_encoded}")

# Test URLs to try
test_urls = [
    (f"mysql+aiomysql://{username}:{password_raw}@{host}:{port}/{database}", "Raw password"),
    (f"mysql+aiomysql://{username}:{password_encoded}@{host}:{port}/{database}", "URL-encoded password"),
]

print("\n🚀 Step 4: Testing connections...")

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection(url, description):
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT VERSION()"))
            version = result.scalar()
            print(f"\n   ✅ SUCCESS: {description}")
            print(f"   MySQL Version: {version}")

            # Test if eleiloes database exists
            result = await conn.execute(text("SHOW DATABASES LIKE 'eleiloes'"))
            db_exists = result.fetchone()
            if db_exists:
                print(f"   ✅ Database 'eleiloes' exists")
            else:
                print(f"   ⚠️  Database 'eleiloes' NOT found!")
                print(f"   You need to create it using mysql_schema.sql")

            print(f"\n   🎯 USE THIS IN .env:")
            print(f"   DATABASE_URL={url}")

            await engine.dispose()
            return True

    except Exception as e:
        print(f"\n   ❌ FAILED: {description}")
        print(f"   Error: {str(e)[:150]}")
        return False

async def main():
    success = False
    for url, description in test_urls:
        if await test_connection(url, description):
            success = True
            break

    if not success:
        print("\n" + "=" * 70)
        print("❌ All connection attempts failed!")
        print("=" * 70)
        print("\n💡 Troubleshooting tips:")
        print("1. Check if MySQL is running")
        print("2. Verify username and password in phpMyAdmin")
        print("3. Try connecting via phpMyAdmin to confirm credentials")
        print("4. Check if user has access to 'eleiloes' database")
        print("5. Database might be on a different host (not localhost)")
        print("\n🔍 Run this in phpMyAdmin to check users:")
        print("   SELECT User, Host FROM mysql.user;")

asyncio.run(main())
