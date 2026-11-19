import sqlite3

db_path = r"C:\Users\lenovo\AppData\Roaming\sh.voicebox.app\voicebox.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Keep Chirag as primary voice profile, remove old unused profiles
keep_ids = ('c7112026-b84e-4e89-a29d-chiragvoice01', '54d39b7c-6a34-413f-b8b4-c23b654c444c')
c.execute("DELETE FROM profiles WHERE id NOT IN (?, ?)", keep_ids)
conn.commit()

c.execute("SELECT id, name, default_engine, preset_engine, preset_voice_id, voice_type FROM profiles")
for row in c.fetchall():
    print("Remaining profile:", row)
conn.close()
