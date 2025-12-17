"""
Test MySQL connection with different passwords
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

passwords_to_try = [
    ("Empty password", ""),
    ("Password: root", "root"),
    ("Password: password", "password"),
    ("Password: admin", "admin"),
    ("Password: mysql", "mysql"),
]

async def test_connection(password_name, password):
    if password:
        url = f"mysql+aiomysql://root:{password}@localhost:3306/eleiloes"
    else:
        url = f"mysql+aiomysql://root@localhost:3306/eleiloes"

    try:
        engine = create_async_engine(url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute("SELECT VERSION()")
            version = result.scalar()
            print(f"✅ {password_name} - SUCCESS!")
            print(f"   MySQL version: {version}")
            print(f"   Use this in .env:")
            if password:
                print(f"   DATABASE_URL=mysql+aiomysql://root:{password}@localhost:3306/eleiloes")
            else:
                print(f"   DATABASE_URL=mysql+aiomysql://root:@localhost:3306/eleiloes")
            print()
            return True
    except Exception as e:
        print(f"❌ {password_name} - Failed: {str(e)[:80]}")
        return False

async def main():
    print("🔍 Testing MySQL connection with different passwords...\n")

    success = False
    for password_name, password in passwords_to_try:
        if await test_connection(password_name, password):
            success = True
            break

    if not success:
        print("\n⚠️  None of the common passwords worked!")
        print("\nTry these solutions:")
        print("1. Reset MySQL root password")
        print("2. Check your MySQL installation documentation")
        print("3. If using phpMyAdmin, check the phpMyAdmin config for password")
        print("4. Try: mysql -u root -p (and enter your password manually)")

asyncio.run(main())
