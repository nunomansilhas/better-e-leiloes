import sqlite3

conn = sqlite3.connect('eleiloes.db')
c = conn.cursor()

# Total de eventos
c.execute('SELECT COUNT(*) FROM events')
total = c.fetchone()[0]
print(f'📊 Total de eventos: {total}')

# Eventos com GPS
c.execute('SELECT COUNT(*) FROM events WHERE latitude IS NOT NULL')
com_gps = c.fetchone()[0]
print(f'📍 Eventos com GPS: {com_gps}')

# Verificar se NP1133692025 existe
c.execute("SELECT reference, latitude, longitude FROM events WHERE reference = 'NP1133692025'")
evento = c.fetchone()
if evento:
    print(f'\n✅ NP1133692025 EXISTE')
    print(f'   GPS: {evento[1]}, {evento[2]}' if evento[1] else '   GPS: NÃO TEM')
else:
    print('\n❌ NP1133692025 NÃO EXISTE na base de dados')

# Listar primeiros 5 eventos
print('\n📋 Primeiros 5 eventos:')
c.execute('SELECT reference, latitude, longitude FROM events LIMIT 5')
for r in c.fetchall():
    gps_status = f'GPS: {r[1]:.6f}, {r[2]:.6f}' if r[1] else 'SEM GPS'
    print(f'   {r[0]}: {gps_status}')

conn.close()
