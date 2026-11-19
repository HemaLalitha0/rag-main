import sqlite3

conn = sqlite3.connect(r'C:\Users\lenovo\AppData\Roaming\sh.voicebox.app\voicebox.db')
c = conn.cursor()
c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
for name, sql in c.fetchall():
    print(f"=== Table: {name} ===")
    print(sql)

c.execute("SELECT id, name, default_engine, preset_engine, preset_voice_id, voice_type FROM profiles")
print("\n=== Current Profiles in DB ===")
for r in c.fetchall():
    print(r)
