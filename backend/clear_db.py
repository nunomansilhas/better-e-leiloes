import sqlite3
import os

# Path para base de dados
db_path = 'eleiloes.db'

print("🗑️  Limpando base de dados...")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Conta eventos antes
    c.execute('SELECT COUNT(*) FROM events')
    before = c.fetchone()[0]
    
    # Limpa tabela
    c.execute('DELETE FROM events')
    conn.commit()
    
    # Conta depois
    c.execute('SELECT COUNT(*) FROM events')
    after = c.fetchone()[0]
    
    conn.close()
    
    print(f"✅ Base de dados limpa!")
    print(f"   Eventos removidos: {before}")
    print(f"   Eventos restantes: {after}")
else:
    print(f"❌ Base de dados não encontrada: {db_path}")
