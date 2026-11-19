@echo off
echo ========================================================
echo Starting Authentic Voicebox Server (Port 17493)...
echo ========================================================
start "" "C:\Users\lenovo\Downloads\Voicebox_Extracted\PFiles\Voicebox\voicebox-server.exe" --host 127.0.0.1 --port 17493 --data-dir "%APPDATA%\sh.voicebox.app"
echo Voicebox server started in the background on http://127.0.0.1:17493.
