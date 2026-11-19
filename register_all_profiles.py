import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\lenovo\AppData\Roaming\sh.voicebox.app\voicebox.db')
c = conn.cursor()

now = datetime.now().isoformat()

# Profiles configuration:
# Preserve exact existing cloned voice profiles (voice_type='cloned', default_engine='chatterbox')
# NEVER overwrite with generic Kokoro presets.
profiles_to_register = [
    {
        "id": "m7112026-b84e-4e89-a29d-manideepvoice01",
        "name": "Manideep",
        "desc": "Calm, authoritative, professional Indian tech news presenter.",
        "voice_type": "cloned",
        "preset_engine": None,
        "preset_voice_id": None,
        "default_engine": "chatterbox"
    },
    {
        "id": "c7112026-b84e-4e89-a29d-chiragvoice01",
        "name": "Chirag",
        "desc": "Soft, gentle, calm conversational voice.",
        "voice_type": "cloned",
        "preset_engine": None,
        "preset_voice_id": None,
        "default_engine": "chatterbox"
    },
    {
        "id": "h7112026-b84e-4e89-a29d-hemavoice01",
        "name": "Hema",
        "desc": "Soft, gentle, expressive female voice.",
        "voice_type": "cloned",
        "preset_engine": None,
        "preset_voice_id": None,
        "default_engine": "chatterbox"
    },
    {
        "id": "s8dz6e36-b84e-4e89-a29d-sushmavoice01",
        "name": "Sushma",
        "desc": "Polished, warm, studio-grade female voice.",
        "voice_type": "cloned",
        "preset_engine": None,
        "preset_voice_id": None,
        "default_engine": "chatterbox"
    }
]

for p in profiles_to_register:
    c.execute("""
        INSERT INTO profiles (id, name, description, language, voice_type, preset_engine, preset_voice_id, default_engine, created_at, updated_at)
        VALUES (?, ?, ?, 'en', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            voice_type = excluded.voice_type,
            preset_engine = excluded.preset_engine,
            preset_voice_id = excluded.preset_voice_id,
            default_engine = excluded.default_engine,
            updated_at = excluded.updated_at
        ON CONFLICT(name) DO UPDATE SET
            id = excluded.id,
            description = excluded.description,
            voice_type = excluded.voice_type,
            preset_engine = excluded.preset_engine,
            preset_voice_id = excluded.preset_voice_id,
            default_engine = excluded.default_engine,
            updated_at = excluded.updated_at
    """, (p["id"], p["name"], p["desc"], p["voice_type"], p["preset_engine"], p["preset_voice_id"], p["default_engine"], now, now))

conn.commit()

c.execute("SELECT id, name, default_engine, preset_engine, preset_voice_id, voice_type FROM profiles")
print("Registered profiles in database:")
for r in c.fetchall():
    print(r)
conn.close()
