"""
WebRTC, Camera Preview & Direct Browser Audio Recording Components.
Provides:
1. Live HTML5 Camera Feed Preview with permission indicators and Mute/Unmute toggles
2. Direct In-Browser Microphone Recorder with Live Audio Waveform visualization,
   instant playback, and direct transmission to Streamlit (no manual file download/upload needed).
3. Professional Huru.ai-inspired Live AI Interview Studio (render_interview_stage) with:
   - Guaranteed audible interviewer playback via parent-window sticky user activation
   - High-contrast Active Speaker Highlight vs. Silent Participant state
   - Real-time word-synchronized Live Subtitles showing who is speaking and the exact spoken words.
"""
import streamlit.components.v1 as components

def render_camera_preview(height: int = 240, enable_video: bool = True):
    """Renders a responsive HTML5 video element directly in Streamlit accessing the webcam."""
    html_code = f"""
    <div style="background: #1A202C; border-radius: 12px; border: 1px solid #2D3748; padding: 12px; text-align: center; font-family: sans-serif; color: #E2E8F0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="font-size: 0.85rem; font-weight: 600; color: #63B3ED;">
                Candidate Video & Audio Feed
            </div>
            <div id="status-badge" style="font-size: 0.75rem; background: #2B6CB0; color: white; padding: 2px 8px; border-radius: 4px;">
                Checking Camera...
            </div>
        </div>
        
        <div style="position: relative; width: 100%; max-width: 440px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden;">
            <video id="webcam-video" autoplay playsinline muted style="width: 100%; height: {height}px; object-fit: cover; display: {'block' if enable_video else 'none'};"></video>
            <div id="camera-off-msg" style="display: {'none' if enable_video else 'flex'}; height: {height}px; align-items: center; justify-content: center; color: #A0AEC0; font-size: 0.9rem;">
                Camera Paused (Audio Active)
            </div>
        </div>

        <div style="margin-top: 8px; display: flex; justify-content: center; gap: 8px;">
            <button id="toggle-cam" onclick="toggleCamera()" style="background: #2D3748; color: #E2E8F0; border: 1px solid #4A5568; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">
                Toggle Camera
            </button>
            <button id="toggle-mic" onclick="toggleMic()" style="background: #2D3748; color: #E2E8F0; border: 1px solid #4A5568; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">
                Mute / Unmute
            </button>
        </div>
    </div>

    <script>
        let localStream = null;
        let videoElem = document.getElementById("webcam-video");
        let badge = document.getElementById("status-badge");
        let cameraOffMsg = document.getElementById("camera-off-msg");

        async function initMedia() {{
            try {{
                localStream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: true }});
                videoElem.srcObject = localStream;
                badge.innerText = "Camera Active";
                badge.style.background = "#276749";
            }} catch (err) {{
                badge.innerText = "Audio-Only Mode";
                badge.style.background = "#D69E2E";
                videoElem.style.display = "none";
                cameraOffMsg.style.display = "flex";
                cameraOffMsg.innerText = "Camera unavailable or declined. Operating in Audio mode.";
            }}
        }}

        function toggleCamera() {{
            if (localStream) {{
                let videoTracks = localStream.getVideoTracks();
                if (videoTracks.length > 0) {{
                    videoTracks[0].enabled = !videoTracks[0].enabled;
                    videoElem.style.display = videoTracks[0].enabled ? "block" : "none";
                    cameraOffMsg.style.display = videoTracks[0].enabled ? "none" : "flex";
                }}
            }}
        }}

        function toggleMic() {{
            if (localStream) {{
                let audioTracks = localStream.getAudioTracks();
                if (audioTracks.length > 0) {{
                    audioTracks[0].enabled = !audioTracks[0].enabled;
                    let btn = document.getElementById("toggle-mic");
                    btn.innerText = audioTracks[0].enabled ? "Mute" : "Unmute (Muted)";
                    btn.style.background = audioTracks[0].enabled ? "#2D3748" : "#C53030";
                }}
            }}
        }}

        initMedia();
    </script>
    """
    components.html(html_code, height=height + 100)


def render_audio_recorder(recorder_key: str = "interview_rec"):
    """
    Renders a direct in-browser microphone recorder with:
    - Real-time animated canvas waveform
    - Live seconds timer
    - Instant Record, Stop, and Playback controls
    - Automatic Base64 audio transmission to parent Streamlit state via postMessage
    """
    html_code = f"""
    <div style="background: #171923; border: 1px solid #2B6CB0; border-radius: 12px; padding: 16px; font-family: sans-serif; color: #E2E8F0; max-width: 540px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="font-weight: 600; font-size: 0.95rem; color: #63B3ED; display: flex; align-items: center; gap: 6px;">
                In-Browser Microphone Recorder
            </div>
            <div id="rec-timer" style="font-size: 0.9rem; font-weight: bold; background: #2D3748; padding: 3px 10px; border-radius: 6px; color: #E2E8F0;">
                00:00
            </div>
        </div>

        <!-- Real-time Audio Waveform Canvas -->
        <canvas id="waveform-canvas" width="500" height="60" style="width: 100%; height: 60px; background: #0F172A; border-radius: 6px; margin-bottom: 12px;"></canvas>

        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
            <button id="start-btn" onclick="startRecording()" style="background: #C53030; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                <span>●</span> Start Recording
            </button>
            <button id="stop-btn" onclick="stopRecording()" disabled style="background: #4A5568; color: #A0AEC0; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: not-allowed;">
                ■ Stop & Process
            </button>
            <audio id="playback-audio" controls style="display: none; height: 36px; max-width: 220px;"></audio>
        </div>

        <div id="rec-status-msg" style="margin-top: 8px; font-size: 0.8rem; color: #A0AEC0;">
            Click <b>Start Recording</b> to capture your spoken answer.
        </div>
    </div>

    <script>
        let mediaRecorder = null;
        let audioChunks = [];
        let audioContext = null;
        let analyser = null;
        let dataArray = null;
        let animationId = null;
        let startTime = null;
        let timerInterval = null;

        const startBtn = document.getElementById("start-btn");
        const stopBtn = document.getElementById("stop-btn");
        const timerElem = document.getElementById("rec-timer");
        const statusMsg = document.getElementById("rec-status-msg");
        const playback = document.getElementById("playback-audio");
        const canvas = document.getElementById("waveform-canvas");
        const canvasCtx = canvas.getContext("2d");

        function drawWaveform() {{
            if (!analyser) return;
            animationId = requestAnimationFrame(drawWaveform);
            analyser.getByteTimeDomainData(dataArray);

            canvasCtx.fillStyle = "#0F172A";
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

            canvasCtx.lineWidth = 2;
            canvasCtx.strokeStyle = "#63B3ED";
            canvasCtx.beginPath();

            let sliceWidth = canvas.width * 1.0 / analyser.frequencyBinCount;
            let x = 0;

            for (let i = 0; i < analyser.frequencyBinCount; i++) {{
                let v = dataArray[i] / 128.0;
                let y = v * (canvas.height / 2);

                if (i === 0) {{
                    canvasCtx.moveTo(x, y);
                }} else {{
                    canvasCtx.lineTo(x, y);
                }}
                x += sliceWidth;
            }}

            canvasCtx.lineTo(canvas.width, canvas.height / 2);
            canvasCtx.stroke();
        }}

        async function startRecording() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioContext.createAnalyser();
                analyser.fftSize = 256;
                const source = audioContext.createMediaStreamSource(stream);
                source.connect(analyser);
                dataArray = new Uint8Array(analyser.frequencyBinCount);
                drawWaveform();

                audioChunks = [];
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => {{
                    if (e.data.size > 0) audioChunks.push(e.data);
                }};

                mediaRecorder.onstop = async () => {{
                    const audioBlob = new Blob(audioChunks, {{ type: "audio/wav" }});
                    const audioUrl = URL.createObjectURL(audioBlob);
                    playback.src = audioUrl;
                    playback.style.display = "block";

                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    reader.onloadend = () => {{
                        const base64Audio = reader.result;
                        try {{
                            window.parent.postMessage({{
                                type: "streamlit:setComponentValue",
                                value: base64Audio
                            }}, "*");
                        }} catch (err) {{}}
                    }};

                    statusMsg.innerHTML = "<span style='color:#68D391;'>Audio recorded successfully! Review playback above.</span>";
                }};

                mediaRecorder.start();
                startTime = Date.now();
                timerInterval = setInterval(() => {{
                    const elapsed = Math.floor((Date.now() - startTime) / 1000);
                    const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
                    const secs = String(elapsed % 60).padStart(2, '0');
                    timerElem.innerText = `${{mins}}:${{secs}}`;
                }}, 1000);

                startBtn.disabled = true;
                startBtn.style.background = "#4A5568";
                startBtn.style.cursor = "not-allowed";

                stopBtn.disabled = false;
                stopBtn.style.background = "#3182CE";
                stopBtn.style.cursor = "pointer";
                stopBtn.style.color = "white";

                statusMsg.innerHTML = "<span style='color:#FC8181;'>Recording live... Speak clearly into your microphone.</span>";
            }} catch (err) {{
                statusMsg.innerHTML = "<span style='color:#FEB2B2;'>Microphone permission denied or microphone not found.</span>";
            }}
        }}

        function stopRecording() {{
            if (mediaRecorder && mediaRecorder.state !== "inactive") {{
                mediaRecorder.stop();
                clearInterval(timerInterval);
                if (animationId) cancelAnimationFrame(animationId);

                startBtn.disabled = false;
                startBtn.style.background = "#C53030";
                startBtn.style.cursor = "pointer";

                stopBtn.disabled = true;
                stopBtn.style.background = "#4A5568";
                stopBtn.style.cursor = "not-allowed";
                stopBtn.style.color = "#A0AEC0";
            }}
        }}
    </script>
    """
    components.html(html_code, height=195)


def render_interview_stage(
    interviewer_name: str = "Manideep",
    candidate_name: str = "Candidate",
    active_speaker: str = "interviewer",  # "interviewer" | "candidate" | "waiting" | "none"
    current_question: str = "",
    enable_camera: bool = True,
    status_text: str = "",
    transcription_text: str = "",
    is_loading_room: bool = False,
    loading_seconds_left: int = 0,
    audio_base64: str = "",
    height: int = 380,
    role_title: str = "Software Engineer",
    company_context: str = "Enterprise Assessment",
    question_number: int = 1,
    total_questions: int = 5,
    question_category: str = "Core Competency",
    duration_minutes: int = 30,
):
    """
    Renders a Huru.ai-inspired, studio-grade full-width AI Interview Workspace:
    - Top Header: Role & company/job context, QUESTION 01 / 10 progress, duration & elapsed time,
      connection/audio status pill, and End Call button.
    - Prominent Question Area: Question number badge, supporting competency context, and full question text.
    - Main Interview Area: Two large, balanced participant panels (Interviewer & Candidate) with
      high-craft vector executive portraits (no basic emoji avatars), unmistakable SPEAKING vs. SILENT
      panel highlights, waveform animations, and live speech captions.
    - Unified Live Subtitles Bar: Displays the active speaker's name and the exact words being spoken
      in real time (word-by-word synchronized for Interviewer, live STT for Candidate).
    """
    interviewer_border = "#6366F1" if active_speaker == "interviewer" else "rgba(148, 163, 184, 0.14)"
    interviewer_glow = "0 0 0 3px rgba(99, 102, 241, 0.45), 0 22px 50px -6px rgba(99, 102, 241, 0.65)" if active_speaker == "interviewer" else "0 10px 30px -10px rgba(0,0,0,0.5)"
    candidate_border = "#10B981" if active_speaker == "candidate" else "rgba(148, 163, 184, 0.14)"
    candidate_glow = "0 0 0 3px rgba(16, 185, 129, 0.45), 0 22px 50px -6px rgba(16, 185, 129, 0.65)" if active_speaker == "candidate" else "0 10px 30px -10px rgba(0,0,0,0.5)"

    escaped_interviewer = interviewer_name.replace('"', '&quot;').replace("'", "&#39;")
    escaped_candidate = (candidate_name or "Candidate").replace('"', '&quot;').replace("'", "&#39;")
    escaped_role = (role_title or "Professional Role").replace('"', '&quot;').replace("'", "&#39;")
    escaped_company = (company_context or "Live Evaluation").replace('"', '&quot;').replace("'", "&#39;")
    escaped_category = (question_category or "Competency Assessment").replace('"', '&quot;').replace("'", "&#39;")
    escaped_question = (current_question or "").replace('"', '&quot;').replace("'", "&#39;")
    escaped_transcription = (transcription_text or "").replace('"', '&quot;').replace("'", "&#39;")

    interviewer_badge_text = "🎙️ SPEAKING" if active_speaker == "interviewer" else "🔇 SILENT (LISTENING)"
    candidate_badge_text = "🎙️ SPEAKING" if active_speaker == "candidate" else ("🔇 SILENT (LISTENING)" if active_speaker == "interviewer" else "🎤 YOUR TURN — SPEAK NOW")
    interviewer_badge_bg = "rgba(99, 102, 241, 0.28)" if active_speaker == "interviewer" else "rgba(30, 41, 59, 0.85)"
    interviewer_badge_color = "#C7D2FE" if active_speaker == "interviewer" else "#94A3B8"
    candidate_badge_bg = "rgba(16, 185, 129, 0.28)" if active_speaker == "candidate" else "rgba(30, 41, 59, 0.85)"
    candidate_badge_color = "#A7F3D0" if active_speaker == "candidate" else "#94A3B8"

    q_num_str = f"{max(1, int(question_number)):02d}"
    q_tot_str = f"{max(1, int(total_questions)):02d}"
    q_progress_pct = min(100, max(5, int((max(1, int(question_number)) / max(1, int(total_questions))) * 100)))
    dur_str = f"{max(5, int(duration_minutes)):02d}:00"

    is_female_profile = any(n in interviewer_name.lower() for n in ["hema", "sushma"])
    if is_female_profile:
        interviewer_svg = """
        <svg viewBox="0 0 120 120" width="96" height="96" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="avBg" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#312E81"/>
                    <stop offset="100%" stop-color="#1E1B4B"/>
                </linearGradient>
                <linearGradient id="suitGrad" x1="25" y1="75" x2="95" y2="120" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#4F46E5"/>
                    <stop offset="100%" stop-color="#3730A3"/>
                </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="58" fill="url(#avBg)" stroke="#6366F1" stroke-width="2" stroke-opacity="0.5"/>
            <path d="M32 54C32 34 44 22 60 22C76 22 88 34 88 54C88 68 82 78 76 82H44C38 78 32 68 32 54Z" fill="#1E293B"/>
            <path d="M24 114C27 92 41 82 60 82C79 82 93 92 96 114" fill="url(#suitGrad)"/>
            <path d="M50 82L60 98L70 82" fill="#E0E7FF"/>
            <rect x="53" y="69" width="14" height="16" rx="6" fill="#F1C27D"/>
            <ellipse cx="60" cy="52" rx="19" ry="21" fill="#F6D096"/>
            <path d="M40 48C42 34 52 28 64 30C74 31 80 39 80 49C74 43 66 40 56 41C48 42 43 45 40 48Z" fill="#0F172A"/>
            <circle cx="53" cy="52" r="2.1" fill="#1E293B"/>
            <circle cx="67" cy="52" r="2.1" fill="#1E293B"/>
            <path d="M55 61C58 63.5 62 63.5 65 61" stroke="#B45309" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """
    else:
        interviewer_svg = """
        <svg viewBox="0 0 120 120" width="96" height="96" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="avBgM" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#1E3A8A"/>
                    <stop offset="100%" stop-color="#0F172A"/>
                </linearGradient>
                <linearGradient id="suitGradM" x1="24" y1="78" x2="96" y2="120" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#3B82F6"/>
                    <stop offset="100%" stop-color="#1D4ED8"/>
                </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="58" fill="url(#avBgM)" stroke="#60A5FA" stroke-width="2" stroke-opacity="0.5"/>
            <path d="M22 114C26 91 40 81 60 81C80 81 94 91 98 114" fill="url(#suitGradM)"/>
            <path d="M51 81L60 99L69 81" fill="#F8FAFC"/>
            <path d="M58 86L60 102L62 86L60 83Z" fill="#6366F1"/>
            <rect x="52" y="68" width="16" height="16" rx="6" fill="#E5B887"/>
            <ellipse cx="60" cy="50" rx="20" ry="22" fill="#F1C27D"/>
            <path d="M40 44C40 31 49 24 60 24C71 24 80 31 80 44C76 38 69 35 60 35C51 35 44 38 40 44Z" fill="#0F172A"/>
            <circle cx="52.5" cy="50" r="2.2" fill="#0F172A"/>
            <circle cx="67.5" cy="50" r="2.2" fill="#0F172A"/>
            <path d="M54 60C57.5 62.5 62.5 62.5 66 60" stroke="#92400E" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """

    candidate_svg = """
    <svg viewBox="0 0 120 120" width="96" height="96" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="candBg" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#064E3B"/>
                <stop offset="100%" stop-color="#0F172A"/>
            </linearGradient>
        </defs>
        <circle cx="60" cy="60" r="58" fill="url(#candBg)" stroke="#10B981" stroke-width="2" stroke-opacity="0.45"/>
        <circle cx="60" cy="46" r="18" fill="#34D399" fill-opacity="0.88"/>
        <path d="M27 108C31 87 43 77 60 77C77 77 89 87 93 108" fill="#10B981" fill-opacity="0.78"/>
    </svg>
    """

    direct_audio_mime = "audio/wav" if (audio_base64.startswith("UklGR") or audio_base64.startswith("RIFF")) else "audio/mp3"

    html_code = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #F8FAFC;
            overflow: hidden;
        }}
        @keyframes pulseDot {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.45; transform: scale(0.92); }}
        }}
        @keyframes rippleWave {{
            0% {{ transform: scale(0.92); opacity: 0.85; }}
            70% {{ transform: scale(1.32); opacity: 0; }}
            100% {{ transform: scale(1.32); opacity: 0; }}
        }}
        @keyframes eqBounce {{
            0%, 100% {{ height: 6px; opacity: 0.65; }}
            50% {{ height: 22px; opacity: 1; }}
        }}
        .eq-bar {{
            width: 3.5px;
            background: #818CF8;
            border-radius: 999px;
            display: inline-block;
            height: 6px;
            transition: height 0.15s ease;
        }}
        .eq-active .eq-bar:nth-child(1) {{ animation: eqBounce 0.65s infinite 0.0s; }}
        .eq-active .eq-bar:nth-child(2) {{ animation: eqBounce 0.55s infinite 0.15s; }}
        .eq-active .eq-bar:nth-child(3) {{ animation: eqBounce 0.75s infinite 0.25s; }}
        .eq-active .eq-bar:nth-child(4) {{ animation: eqBounce 0.60s infinite 0.10s; }}
        .eq-active .eq-bar:nth-child(5) {{ animation: eqBounce 0.70s infinite 0.20s; }}
        .eq-active .eq-bar:nth-child(6) {{ animation: eqBounce 0.52s infinite 0.05s; }}
        .ctrl-btn {{
            background: rgba(30, 41, 59, 0.85);
            color: #E2E8F0;
            border: 1px solid rgba(148, 163, 184, 0.2);
            height: 38px;
            padding: 0 14px;
            border-radius: 10px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            transition: all 0.18s ease;
            font-family: inherit;
        }}
        .ctrl-btn:hover {{
            background: rgba(51, 65, 85, 0.95);
            border-color: rgba(148, 163, 184, 0.38);
        }}
        .end-call-btn {{
            background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
            color: #FFFFFF;
            border: 1px solid rgba(248, 113, 113, 0.45);
            height: 38px;
            padding: 0 18px;
            border-radius: 10px;
            font-size: 0.82rem;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 6px 18px -4px rgba(239, 68, 68, 0.55);
            transition: all 0.18s ease;
            font-family: inherit;
        }}
        .end-call-btn:hover {{
            background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%);
            transform: translateY(-1px);
        }}
        .spoken-word-active {{
            color: #FFFFFF;
            background: rgba(99, 102, 241, 0.38);
            border-radius: 4px;
            padding: 0 3px;
            font-weight: 700;
        }}
        .spoken-word-past {{
            color: #E2E8F0;
        }}
        .spoken-word-future {{
            color: #94A3B8;
        }}
    </style>

    <div id="call-room-container" style="background: linear-gradient(180deg, #0B0F17 0%, #0F172A 100%); border-radius: 18px; border: 1px solid rgba(148, 163, 184, 0.14); padding: 16px 20px; color: #F8FAFC; box-shadow: 0 24px 60px -15px rgba(0, 0, 0, 0.75); width: 100%; position: relative; display: flex; flex-direction: column; gap: 12px;">

        <!-- Autoplay Unmute Prompt (Only shown if browser blocks initial audio playback) -->
        <button id="unmute-banner" onclick="forceUnlockAndPlayAudio()" style="display: none; position: absolute; top: 14px; left: 50%; transform: translateX(-50%); z-index: 99; background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); color: #FFFFFF; border: 1px solid #A5B4FC; border-radius: 999px; padding: 8px 20px; font-weight: 700; font-size: 0.84rem; cursor: pointer; box-shadow: 0 12px 28px rgba(79, 70, 229, 0.65); align-items: center; gap: 8px;">
            <span>🔊 Click Here to Hear {escaped_interviewer}'s Audio</span>
        </button>

        <!-- 1. TOP HEADER BAR -->
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(148, 163, 184, 0.12);">
            <!-- Left: Interview Role & Company/Job Context -->
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.95rem; color: #FFFFFF; box-shadow: 0 6px 16px -4px rgba(99, 102, 241, 0.55);">
                    AI
                </div>
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span id="header-role-title" style="font-size: 0.96rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.01em;">{escaped_role}</span>
                        <span style="font-size: 0.72rem; font-weight: 600; color: #818CF8; background: rgba(99, 102, 241, 0.14); border: 1px solid rgba(99, 102, 241, 0.3); padding: 2px 8px; border-radius: 999px;">{escaped_company}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 2px;">
                        Interviewer: <strong style="color: #E2E8F0;">{escaped_interviewer}</strong> &bull; Candidate: <strong style="color: #E2E8F0;">{escaped_candidate}</strong>
                    </div>
                </div>
            </div>

            <!-- Center: Question Progress (QUESTION 01 / 10) + Progress Bar -->
            <div style="display: flex; align-items: center; gap: 14px; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(148, 163, 184, 0.14); padding: 6px 14px; border-radius: 12px;">
                <div>
                    <div id="header-question-counter" style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 700; color: #E2E8F0; letter-spacing: 0.06em;">
                        QUESTION {q_num_str} / {q_tot_str}
                    </div>
                    <div style="width: 120px; height: 4px; background: rgba(51, 65, 85, 0.8); border-radius: 999px; margin-top: 5px; overflow: hidden;">
                        <div id="header-question-bar" style="width: {q_progress_pct}%; height: 100%; background: linear-gradient(90deg, #6366F1, #38BDF8); border-radius: 999px; transition: width 0.35s ease;"></div>
                    </div>
                </div>
                <div style="width: 1px; height: 24px; background: rgba(148, 163, 184, 0.16);"></div>
                <!-- Duration & Elapsed Time -->
                <div style="display: flex; align-items: center; gap: 6px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    <span id="live-call-timer" style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600; color: #F8FAFC;">00:00</span>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B;">/ {dur_str}</span>
                </div>
            </div>

            <!-- Right: Connection & Audio Status + Controls + End Call -->
            <div style="display: flex; align-items: center; gap: 8px;">
                <div id="vad-indicator" style="display: inline-flex; align-items: center; gap: 7px; font-size: 0.76rem; font-weight: 600; padding: 6px 12px; border-radius: 999px; background: rgba(16, 185, 129, 0.12); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.28); transition: all 0.2s ease;">
                    <span id="conn-dot" style="width: 7px; height: 7px; border-radius: 50%; background: #10B981; animation: pulseDot 1.6s infinite;"></span>
                    <span id="conn-status-text">Connected &bull; HD Audio</span>
                </div>

                <button id="stage-mic-btn" class="ctrl-btn" onclick="toggleStageMic()" title="Mute / Unmute Microphone">
                    <span id="mic-btn-label">Mic On</span>
                </button>
                <button id="stage-cam-btn" class="ctrl-btn" onclick="toggleStageCam()" title="Toggle Camera Feed">
                    <span id="cam-btn-label">{'Cam On' if enable_camera else 'Cam Off'}</span>
                </button>
                <button id="end-call-btn" class="end-call-btn" onclick="triggerHangup()" title="End Interview Session">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/><line x1="23" y1="1" x2="1" y2="23"/></svg>
                    <span>End Call</span>
                </button>
            </div>
        </div>

        <!-- Voicebox Profile Error Banner (Hidden unless selected Voicebox profile fails to load) -->
        <div id="voice-error-banner" style="display: none; background: rgba(239, 68, 68, 0.16); border: 1px solid rgba(239, 68, 68, 0.55); border-left: 4px solid #EF4444; border-radius: 10px; padding: 10px 16px; color: #FECACA; font-size: 0.82rem; font-weight: 600;">
            ⚠️ <span id="voice-error-text">Selected Voicebox profile could not be loaded.</span>
        </div>

        <!-- 2. QUESTION AREA (Prominent Current Interview Question Card) -->
        <div style="background: linear-gradient(90deg, rgba(30, 41, 59, 0.78) 0%, rgba(15, 23, 42, 0.88) 100%); border: 1px solid rgba(99, 102, 241, 0.32); border-left: 4px solid #6366F1; border-radius: 14px; padding: 13px 18px; display: flex; flex-direction: column; gap: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span id="question-badge-pill" style="font-family: 'JetBrains Mono', monospace; font-size: 0.71rem; font-weight: 700; color: #A5B4FC; background: rgba(99, 102, 241, 0.18); padding: 2px 9px; border-radius: 6px; letter-spacing: 0.05em;">
                        QUESTION {q_num_str}
                    </span>
                    <span id="stage-question-context" style="font-size: 0.75rem; font-weight: 600; color: #94A3B8;">
                        {escaped_category}
                    </span>
                </div>
                <span id="turn-guidance-label" style="font-size: 0.74rem; color: #94A3B8; font-weight: 500;">
                    {status_text or f'Hands-Free Turn Detection Active'}
                </span>
            </div>
            <div id="stage-current-prompt" style="font-size: 1.06rem; font-weight: 600; color: #F8FAFC; line-height: 1.45; letter-spacing: -0.01em;">
                {escaped_question if escaped_question else f"{escaped_interviewer} is preparing your interview question..."}
            </div>
        </div>

        <!-- 3. MAIN INTERVIEW AREA: Two Large, Balanced Participant Panels -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; min-height: {height}px;">

            <!-- LEFT PANEL: AI INTERVIEWER -->
            <div id="syna-panel" style="background: radial-gradient(circle at 50% 35%, #1E293B 0%, #0F172A 78%); border-radius: 16px; height: {height}px; position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: {interviewer_glow}; border: 3px solid {interviewer_border}; transition: all 0.25s ease; overflow: hidden; padding: 18px;">

                <!-- Top-left Role Tag -->
                <div style="position: absolute; top: 14px; left: 16px; display: flex; align-items: center; gap: 8px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); padding: 5px 11px; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.18);">
                    <span id="syna-status-dot" style="width: 8px; height: 8px; border-radius: 50%; background: #6366F1;"></span>
                    <span style="font-size: 0.78rem; font-weight: 700; color: #F8FAFC;">{escaped_interviewer}</span>
                    <span style="font-size: 0.7rem; color: #94A3B8; font-weight: 500;">AI Interviewer</span>
                </div>

                <!-- Top-right Speaking / Silent Indicator + Equalizer -->
                <div style="position: absolute; top: 14px; right: 16px; display: flex; align-items: center; gap: 8px;">
                    <div id="syna-eq-bars" class="{'eq-active' if active_speaker == 'interviewer' else ''}" style="display: flex; align-items: flex-end; gap: 3px; height: 22px; padding: 0 4px;">
                        <span class="eq-bar"></span>
                        <span class="eq-bar"></span>
                        <span class="eq-bar"></span>
                        <span class="eq-bar"></span>
                        <span class="eq-bar"></span>
                        <span class="eq-bar"></span>
                    </div>
                    <div id="syna-badge" style="background: {interviewer_badge_bg}; color: {interviewer_badge_color}; font-size: 0.73rem; font-weight: 700; padding: 4px 12px; border-radius: 999px; border: 1px solid rgba(99, 102, 241, 0.38); letter-spacing: 0.02em;">
                        {interviewer_badge_text}
                    </div>
                </div>

                <!-- Executive Vector Portrait + Speaking Aura -->
                <div style="position: relative; display: flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                    <div id="syna-ripple" style="position: absolute; width: 138px; height: 138px; border-radius: 50%; border: 2.5px solid #6366F1; opacity: {'0.85' if active_speaker == 'interviewer' else '0'}; animation: {'rippleWave 1.6s infinite' if active_speaker == 'interviewer' else 'none'}; pointer-events: none;"></div>
                    <div id="syna-ripple-2" style="position: absolute; width: 118px; height: 118px; border-radius: 50%; background: radial-gradient(circle, rgba(99,102,241,0.35) 0%, rgba(99,102,241,0) 70%); opacity: {'1' if active_speaker == 'interviewer' else '0.18'}; transition: opacity 0.25s ease; pointer-events: none;"></div>
                    <div style="width: 98px; height: 98px; border-radius: 50%; overflow: hidden; display: flex; align-items: center; justify-content: center; box-shadow: 0 12px 28px rgba(0,0,0,0.45); position: relative; z-index: 2;">
                        {interviewer_svg}
                    </div>
                </div>

                <!-- Interviewer Name & Title -->
                <div style="font-weight: 700; font-size: 1.02rem; color: #F8FAFC; z-index: 2; letter-spacing: -0.01em;">
                    {escaped_interviewer}
                </div>
                <div style="font-size: 0.75rem; color: #94A3B8; z-index: 2; margin-top: 2px;">
                    Lead Hiring Panelist
                </div>

                <!-- Interviewer Live Speech Subtitle Overlay -->
                <div style="position: absolute; bottom: 12px; left: 14px; right: 14px; background: rgba(9, 13, 22, 0.85); backdrop-filter: blur(8px); border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 10px; padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                    <div id="interviewer-live-caption" style="font-size: 0.8rem; color: #E2E8F0; line-height: 1.38; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; flex: 1;">
                        {escaped_question if active_speaker == "interviewer" and escaped_question else f"🔇 Silent — Listening to {escaped_candidate}..."}
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                        <span id="vol-icon" onclick="toggleMuteAudio()" style="cursor: pointer; font-size: 0.78rem; font-weight: 700; color: #A5B4FC;" title="Mute / Unmute Interviewer Audio">🔊 Vol</span>
                        <input id="syna-vol-slider" type="range" min="0" max="100" value="95" oninput="updateAudioVolume(this.value)" style="width: 58px; accent-color: #6366F1; cursor: pointer; height: 4px;" title="Interviewer Volume">
                    </div>
                </div>

                <audio id="syna-direct-audio" preload="auto" style="display:none;">
                    {f'<source src="data:{direct_audio_mime};base64,{audio_base64}" type="{direct_audio_mime}">' if audio_base64 else ''}
                </audio>
            </div>

            <!-- RIGHT PANEL: CANDIDATE -->
            <div id="candidate-panel" style="background: radial-gradient(circle at 50% 35%, #1E293B 0%, #0F172A 78%); border-radius: 16px; height: {height}px; position: relative; overflow: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: {candidate_glow}; border: 3px solid {candidate_border}; transition: all 0.25s ease;">

                <!-- Live Camera Stream -->
                <video id="stage-webcam" autoplay playsinline muted style="width: 100%; height: 100%; object-fit: cover; display: {'block' if enable_camera else 'none'}; transform: scaleX(-1);"></video>

                <!-- Professional Studio Silhouette Fallback when Camera is Off -->
                <div id="stage-cam-fallback" style="display: {'none' if enable_camera else 'flex'}; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%; padding: 18px; text-align: center;">
                    <div style="position: relative; display: flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                        <div id="candidate-ripple" style="position: absolute; width: 138px; height: 138px; border-radius: 50%; border: 2.5px solid #10B981; opacity: {'0.85' if active_speaker == 'candidate' else '0'}; animation: {'rippleWave 1.5s infinite' if active_speaker == 'candidate' else 'none'}; pointer-events: none;"></div>
                        <div style="width: 98px; height: 98px; border-radius: 50%; overflow: hidden; display: flex; align-items: center; justify-content: center; box-shadow: 0 12px 28px rgba(0,0,0,0.45);">
                            {candidate_svg}
                        </div>
                    </div>
                    <div style="font-weight: 700; font-size: 1.02rem; color: #F8FAFC;">{escaped_candidate}</div>
                    <div id="cam-sub-status" style="font-size: 0.75rem; color: #94A3B8; margin-top: 2px;">Studio Audio Feed Active</div>
                </div>

                <!-- Top-left Candidate Tag -->
                <div style="position: absolute; top: 14px; left: 16px; display: flex; align-items: center; gap: 8px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); padding: 5px 11px; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.18);">
                    <span id="cand-status-dot" style="width: 8px; height: 8px; border-radius: 50%; background: #10B981;"></span>
                    <span style="font-size: 0.78rem; font-weight: 700; color: #F8FAFC;">{escaped_candidate}</span>
                    <span style="font-size: 0.7rem; color: #94A3B8; font-weight: 500;">Candidate</span>
                </div>

                <!-- Top-right Candidate Speaking / Silent Status Badge -->
                <div id="candidate-badge" style="position: absolute; top: 14px; right: 16px; background: {candidate_badge_bg}; color: {candidate_badge_color}; font-size: 0.73rem; font-weight: 700; padding: 4px 12px; border-radius: 999px; border: 1px solid rgba(16, 185, 129, 0.38); letter-spacing: 0.02em;">
                    {candidate_badge_text}
                </div>

                <!-- Bottom Live Audio Waveform & Subtitle Overlay inside Candidate Panel -->
                <div style="position: absolute; bottom: 12px; left: 14px; right: 14px; background: rgba(9, 13, 22, 0.85); backdrop-filter: blur(8px); border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 10px; padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
                    <div id="candidate-live-caption" style="font-size: 0.8rem; color: #E2E8F0; line-height: 1.38; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; flex: 1;">
                        {escaped_transcription if escaped_transcription else f"🔇 Silent — Listening to {escaped_interviewer}..."}
                    </div>
                    <div id="cand-vad-level-bar" style="display: flex; align-items: flex-end; gap: 2.5px; height: 18px; flex-shrink: 0;">
                        <span class="cand-wave-bar" style="width:3px; height:4px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:6px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:5px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:8px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:5px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:7px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:4px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                        <span class="cand-wave-bar" style="width:3px; height:6px; background:#10B981; border-radius:99px; transition:height 0.08s ease;"></span>
                    </div>
                </div>
            </div>

        </div>

        <!-- 4. UNIFIED REAL-TIME SUBTITLES BAR (Shows Active Speaker & Exact Words Being Spoken) -->
        <div id="unified-subtitle-bar" style="background: rgba(15, 23, 42, 0.92); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 12px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 14px; transition: all 0.25s ease;">
            <div style="display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1;">
                <span id="live-subtitle-speaker-tag" style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; font-weight: 700; color: #C7D2FE; background: rgba(99, 102, 241, 0.22); border: 1px solid rgba(99, 102, 241, 0.45); padding: 4px 10px; border-radius: 6px; letter-spacing: 0.03em; flex-shrink: 0;">
                    🎙️ {escaped_interviewer} (SPEAKING)
                </span>
                <div id="candidate-transcript-text" style="font-size: 0.92rem; font-weight: 500; color: #F8FAFC; line-height: 1.45; overflow-wrap: anywhere;">
                    {escaped_question if escaped_question else "Connecting live subtitles..."}
                </div>
            </div>
            <div id="turn-state-chip" style="font-size: 0.74rem; font-weight: 600; color: #94A3B8; flex-shrink: 0;">
                {escaped_candidate}: Silent (Listening)
            </div>
        </div>

        <!-- 5. LIVE INTERVIEW ACTIVITY LOG & AUDIO CAPTURE MONITORING PANEL -->
        <div id="live-activity-log-panel" style="background: rgba(9, 13, 24, 0.96); border: 1px solid rgba(99, 102, 241, 0.32); border-radius: 14px; overflow: hidden; box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.65); font-family: 'Inter', sans-serif;">
            <!-- Header & Controls Toolbar -->
            <div style="background: linear-gradient(90deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.95) 100%); border-bottom: 1px solid rgba(148, 163, 184, 0.16); padding: 10px 14px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span style="font-size: 0.78rem; font-weight: 800; color: #F8FAFC; letter-spacing: 0.04em; display: inline-flex; align-items: center; gap: 6px;">
                        📊 LIVE INTERVIEW ACTIVITY LOG
                    </span>
                    <button id="log-pause-btn" onclick="toggleLogPause()" style="background: rgba(16, 185, 129, 0.18); border: 1px solid rgba(16, 185, 129, 0.45); color: #6EE7B7; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; padding: 3px 9px; border-radius: 99px; cursor: pointer;">
                        ● LIVE
                    </button>
                    <span id="log-live-state-pill" style="font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; color: #A5B4FC; background: rgba(99, 102, 241, 0.16); border: 1px solid rgba(99, 102, 241, 0.35); padding: 3px 9px; border-radius: 6px;">
                        STATE: INITIALIZING
                    </span>
                    <span id="log-timing-summary" style="font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; color: #94A3B8; background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(148, 163, 184, 0.15); padding: 3px 8px; border-radius: 6px;">
                        TTS: - | STT: - | Eval: - | Turnaround: -
                    </span>
                </div>

                <!-- Filter & Export Controls -->
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                    <div style="display: inline-flex; background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 7px; padding: 2px;">
                        <button id="flt-ALL" onclick="setLogSpeakerFilter('ALL')" style="background: rgba(99, 102, 241, 0.3); color: #E0E7FF; border: none; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 5px; cursor: pointer;">ALL</button>
                        <button id="flt-SYNA" onclick="setLogSpeakerFilter('SYNA')" style="background: transparent; color: #94A3B8; border: none; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 5px; cursor: pointer;">SYNA</button>
                        <button id="flt-CANDIDATE" onclick="setLogSpeakerFilter('CANDIDATE')" style="background: transparent; color: #94A3B8; border: none; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 5px; cursor: pointer;">CANDIDATE</button>
                        <button id="flt-SYSTEM" onclick="setLogSpeakerFilter('SYSTEM')" style="background: transparent; color: #94A3B8; border: none; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 5px; cursor: pointer;">SYSTEM</button>
                    </div>

                    <label style="display: inline-flex; align-items: center; gap: 4px; font-size: 0.68rem; color: #CBD5E1; cursor: pointer; background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(148, 163, 184, 0.2); padding: 3px 7px; border-radius: 6px;">
                        <input type="checkbox" id="log-errors-only" onchange="renderActivityLogRows()" style="accent-color: #EF4444; margin: 0;" />
                        Errors/Retries
                    </label>

                    <label style="display: inline-flex; align-items: center; gap: 4px; font-size: 0.68rem; color: #CBD5E1; cursor: pointer; background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(148, 163, 184, 0.2); padding: 3px 7px; border-radius: 6px;">
                        <input type="checkbox" id="log-autoscroll" checked style="accent-color: #6366F1; margin: 0;" />
                        Auto-scroll
                    </label>

                    <button id="log-privacy-btn" onclick="toggleLogPrivacy()" title="Toggle transcript visibility in logs" style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(148, 163, 184, 0.22); color: #CBD5E1; font-size: 0.66rem; font-weight: 600; padding: 3px 8px; border-radius: 6px; cursor: pointer;">
                        👁️ Transcripts: ON
                    </button>

                    <button onclick="clearActivityLogs()" style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(148, 163, 184, 0.22); color: #CBD5E1; font-size: 0.66rem; font-weight: 600; padding: 3px 8px; border-radius: 6px; cursor: pointer;">
                        🗑️ Clear
                    </button>

                    <button onclick="exportActivityLogs('txt')" style="background: rgba(99, 102, 241, 0.16); border: 1px solid rgba(99, 102, 241, 0.38); color: #C7D2FE; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; cursor: pointer;">
                        ⬇ TXT
                    </button>

                    <button onclick="exportActivityLogs('json')" style="background: rgba(16, 185, 129, 0.16); border: 1px solid rgba(16, 185, 129, 0.38); color: #A7F3D0; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; cursor: pointer;">
                        ⬇ JSON
                    </button>

                    <button id="log-collapse-btn" onclick="toggleLogCollapse()" style="background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(148, 163, 184, 0.25); color: #E2E8F0; font-size: 0.66rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; cursor: pointer;">
                        ▼ Collapse
                    </button>
                </div>
            </div>

            <!-- Scrollable 7-Column Log Table -->
            <div id="activity-log-scroll-container" style="max-height: 265px; overflow-y: auto; overflow-x: auto; background: rgba(7, 10, 19, 0.96);">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.74rem; text-align: left;">
                    <thead style="position: sticky; top: 0; background: #0F172A; z-index: 5; border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                        <tr style="color: #94A3B8; font-family: 'JetBrains Mono', monospace; font-size: 0.67rem; text-transform: uppercase; letter-spacing: 0.04em;">
                            <th style="padding: 7px 10px; white-space: nowrap; width: 78px;">Timestamp</th>
                            <th style="padding: 7px 8px; white-space: nowrap; width: 64px;">Elapsed</th>
                            <th style="padding: 7px 8px; white-space: nowrap; width: 88px;">Speaker</th>
                            <th style="padding: 7px 10px; white-space: nowrap; width: 170px;">Event</th>
                            <th style="padding: 7px 10px;">Captured Content <span style="font-size: 0.6rem; color: #64748B; font-weight: 400;">(click row for details)</span></th>
                            <th style="padding: 7px 8px; white-space: nowrap; width: 74px; text-align: right;">Duration</th>
                            <th style="padding: 7px 10px; white-space: nowrap; width: 82px; text-align: center;">Status</th>
                        </tr>
                    </thead>
                    <tbody id="activity-log-tbody" style="font-family: 'Inter', sans-serif; color: #E2E8F0;">
                        <tr>
                            <td colspan="7" style="padding: 16px; text-align: center; color: #64748B; font-family: 'JetBrains Mono', monospace; font-size: 0.74rem;">
                                Initializing real-time interview activity stream...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const _PARENT_ORIGIN = (window.parent && window.parent.location && window.parent.location.origin) ? window.parent.location.origin : window.location.origin;
        const _IS_LOCAL_DEV = (_PARENT_ORIGIN.includes("127.0.0.1") || _PARENT_ORIGIN.includes("localhost"));
        const BRIDGE_BASE_URL = _IS_LOCAL_DEV ? "http://127.0.0.1:8765" : (_PARENT_ORIGIN + "/api/bridge");
        const INTERVIEWER_NAME = "{escaped_interviewer}";
        const CANDIDATE_NAME = "{escaped_candidate}";
        const INITIAL_AUDIO_B64 = "{audio_base64}";
        const INITIAL_PROMPT_TEXT = "{escaped_question}";

        let stageStream = null;
        let stageVideo = document.getElementById("stage-webcam");
        let stageFallback = document.getElementById("stage-cam-fallback");
        let camSubStatus = document.getElementById("cam-sub-status");
        let micBtn = document.getElementById("stage-mic-btn");
        let camBtn = document.getElementById("stage-cam-btn");
        let micBtnLabel = document.getElementById("mic-btn-label");
        let camBtnLabel = document.getElementById("cam-btn-label");
        let timerSpan = document.getElementById("live-call-timer");
        let localSynaAudio = document.getElementById("syna-direct-audio");
        let volSlider = document.getElementById("syna-vol-slider");
        let volIcon = document.getElementById("vol-icon");
        let unmuteBanner = document.getElementById("unmute-banner");

        // Use parent document Audio element so Chromium inherits the user activation from clicking "Enter Live Interview Room"
        let synaAudio = localSynaAudio;
        try {{
            if (window.parent && window.parent.document) {{
                let parentAudio = window.parent.document.getElementById("syna-parent-stage-audio");
                if (!parentAudio) {{
                    parentAudio = window.parent.document.createElement("audio");
                    parentAudio.id = "syna-parent-stage-audio";
                    parentAudio.preload = "auto";
                    parentAudio.style.display = "none";
                    window.parent.document.body.appendChild(parentAudio);
                }}
                synaAudio = parentAudio;
            }}
        }} catch (e) {{
            synaAudio = localSynaAudio;
        }}

        let synaPanel = document.getElementById("syna-panel");
        let synaRipple = document.getElementById("syna-ripple");
        let synaRipple2 = document.getElementById("syna-ripple-2");
        let synaEqBars = document.getElementById("syna-eq-bars");
        let synaBadge = document.getElementById("syna-badge");
        let interviewerLiveCaption = document.getElementById("interviewer-live-caption");
        let candidatePanel = document.getElementById("candidate-panel");
        let candidateRipple = document.getElementById("candidate-ripple");
        let candidateBadge = document.getElementById("candidate-badge");
        let vadIndicator = document.getElementById("vad-indicator");
        let connDot = document.getElementById("conn-dot");
        let connStatusText = document.getElementById("conn-status-text");
        let transcriptBox = document.getElementById("candidate-transcript-text");
        let subtitleBar = document.getElementById("unified-subtitle-bar");
        let subtitleSpeakerTag = document.getElementById("live-subtitle-speaker-tag");
        let candidateLiveCaption = document.getElementById("candidate-live-caption");
        let turnStateChip = document.getElementById("turn-state-chip");
        let stagePrompt = document.getElementById("stage-current-prompt");
        let headerQuestionCounter = document.getElementById("header-question-counter");
        let headerQuestionBar = document.getElementById("header-question-bar");
        let questionBadgePill = document.getElementById("question-badge-pill");
        let stageQuestionContext = document.getElementById("stage-question-context");
        let candWaveBars = document.querySelectorAll(".cand-wave-bar");
        let voiceErrorBanner = document.getElementById("voice-error-banner");
        let voiceErrorText = document.getElementById("voice-error-text");

        let vadAudioCtx = null;
        let vadAnalyser = null;
        let vadData = null;
        let vadTimeData = null;
        let vadAnimFrameId = null;
        let mediaRecorder = null;
        let recordedChunks = [];
        let isCandidateSpeaking = false;
        let isSynaSpeaking = false;
        let isMicOn = true;
        let isCameraOn = {'true' if enable_camera else 'false'};
        let isCallEnded = false;
        let speechStartTime = 0;
        let lastVoiceTime = 0;
        let lastTotalSpeechDurationMs = 0;
        let synaSpeechEndedAt = 0;
        let waitingForCandidateSince = 0;
        let isSubmittingAudio = false;
        let lastPlayedAudioHash = "";
        let pendingAudioB64 = "";
        let pendingAudioSubtitle = "";
        let currentInterviewerText = INITIAL_PROMPT_TEXT;
        let currentCallStage = "INITIAL_GREETING";
        let greetingDoneSent = false;
        let lastPromptText = "";
        let speechRec = null;
        let liveInterimTranscript = "";
        let callTimerInterval = null;
        let pollInterval = null;
        let turnMonitorInterval = null;

        let ambientNoiseFloor = 14.0;
        let consecutiveSpeechFrames = 0;
        const SPEECH_DEBOUNCE_FRAMES = 5;     // ~80-90ms continuous harmonic voice energy required
        let SILENCE_DURATION_MS = 20000;      // 20.0s continuous silence grace period after candidate stops speaking (configurable)
        const READINESS_SILENCE_MS = 1800;    // 1.8s silence threshold for short readiness response ("Yes, I'm ready")
        const MAX_READINESS_SPEECH_MS = 4800; // Auto-finalize readiness check after 4.8s even if background TV/fan noise continues
        const THINKING_PAUSE_GRACE_MS = 650;  // Extra grace if candidate pauses mid-clause ("and", "because", etc.)
        const MIN_SPEECH_MS = 950;            // Minimum ~1.0s of voiced speech
        let MAX_INACTIVITY_WAIT_MS = 20000;   // 20s inactivity timeout when candidate has not started speaking
        const ECHO_GUARD_COOLDOWN_MS = 450;   // Post-TTS acoustic echo guard cooldown after interviewer finishes speaking
        let isWaitingForSilenceStateNotified = false;

        if (!window.sessionStorage.getItem("syna_call_start")) {{
            window.sessionStorage.setItem("syna_call_start", Date.now().toString());
        }}
        callTimerInterval = setInterval(() => {{
            if (isCallEnded) return;
            if (timerSpan) {{
                let start = parseInt(window.sessionStorage.getItem("syna_call_start") || Date.now().toString());
                let elapsed = Math.floor((Date.now() - start) / 1000);
                let mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
                let secs = String(elapsed % 60).padStart(2, '0');
                timerSpan.innerText = `${{mins}}:${{secs}}`;
            }}
        }}, 1000);

        function renderSynchronizedInterviewerWords(fullText, progressRatio) {{
            if (!fullText) return "";
            const words = fullText.trim().split(/\\s+/);
            if (words.length === 0) return "";
            const activeIdx = Math.min(words.length - 1, Math.max(0, Math.floor(progressRatio * words.length)));
            return words.map((w, idx) => {{
                if (idx === activeIdx) {{
                    return `<span class="spoken-word-active">${{w}}</span>`;
                }} else if (idx < activeIdx) {{
                    return `<span class="spoken-word-past">${{w}}</span>`;
                }} else {{
                    return `<span class="spoken-word-future">${{w}}</span>`;
                }}
            }}).join(" ");
        }}

        function setVisualSpeakerState(speaker, activeText) {{
            if (isCallEnded) return;
            if (speaker === "interviewer") {{
                // Highlight Interviewer Panel brightly & dim Candidate Panel as Silent
                if (synaPanel) {{
                    synaPanel.style.borderColor = "#6366F1";
                    synaPanel.style.boxShadow = "0 0 0 3px rgba(99, 102, 241, 0.45), 0 22px 50px -6px rgba(99, 102, 241, 0.7)";
                    synaPanel.style.opacity = "1";
                    synaPanel.style.transform = "scale(1.008)";
                }}
                if (synaRipple) {{
                    synaRipple.style.opacity = "0.85";
                    synaRipple.style.animation = "rippleWave 1.6s infinite";
                }}
                if (synaRipple2) synaRipple2.style.opacity = "1";
                if (synaEqBars) synaEqBars.classList.add("eq-active");
                if (synaBadge) {{
                    synaBadge.innerText = "🎙️ SPEAKING";
                    synaBadge.style.background = "rgba(99, 102, 241, 0.32)";
                    synaBadge.style.color = "#E0E7FF";
                    synaBadge.style.borderColor = "#818CF8";
                }}

                // Dim Candidate Panel -> Silent
                if (candidatePanel) {{
                    candidatePanel.style.borderColor = "rgba(148, 163, 184, 0.14)";
                    candidatePanel.style.boxShadow = "0 8px 20px -10px rgba(0,0,0,0.45)";
                    candidatePanel.style.opacity = "0.62";
                    candidatePanel.style.transform = "scale(0.992)";
                }}
                if (candidateRipple) {{
                    candidateRipple.style.opacity = "0";
                    candidateRipple.style.animation = "none";
                }}
                if (candidateBadge) {{
                    candidateBadge.innerText = isMicOn ? "🔇 SILENT (LISTENING)" : "🔇 MIC MUTED";
                    candidateBadge.style.background = "rgba(30, 41, 59, 0.85)";
                    candidateBadge.style.color = isMicOn ? "#94A3B8" : "#FCA5A5";
                    candidateBadge.style.borderColor = isMicOn ? "rgba(148, 163, 184, 0.2)" : "rgba(239, 68, 68, 0.4)";
                }}
                if (candidateLiveCaption) {{
                    candidateLiveCaption.innerText = `🔇 Silent — Listening to ${{INTERVIEWER_NAME}}...`;
                }}

                // Update Unified Subtitles Bar for Interviewer
                let spoken = activeText || currentInterviewerText || "";
                if (interviewerLiveCaption && spoken) {{
                    interviewerLiveCaption.innerText = spoken;
                }}
                if (subtitleBar) {{
                    subtitleBar.style.borderColor = "rgba(99, 102, 241, 0.5)";
                }}
                if (subtitleSpeakerTag) {{
                    subtitleSpeakerTag.innerText = `🎙️ ${{INTERVIEWER_NAME}} (SPEAKING)`;
                    subtitleSpeakerTag.style.color = "#E0E7FF";
                    subtitleSpeakerTag.style.background = "rgba(99, 102, 241, 0.28)";
                    subtitleSpeakerTag.style.borderColor = "#818CF8";
                }}
                if (transcriptBox && spoken) {{
                    transcriptBox.innerText = spoken;
                }}
                if (connStatusText) connStatusText.innerText = `${{INTERVIEWER_NAME}} Speaking`;
                if (turnStateChip) turnStateChip.innerText = `${{CANDIDATE_NAME}}: Silent (Listening)`;

            }} else if (speaker === "candidate") {{
                // Highlight Candidate Panel brightly & dim Interviewer Panel as Silent
                if (synaPanel) {{
                    synaPanel.style.borderColor = "rgba(148, 163, 184, 0.14)";
                    synaPanel.style.boxShadow = "0 8px 20px -10px rgba(0,0,0,0.45)";
                    synaPanel.style.opacity = "0.62";
                    synaPanel.style.transform = "scale(0.992)";
                }}
                if (synaRipple) {{
                    synaRipple.style.opacity = "0";
                    synaRipple.style.animation = "none";
                }}
                if (synaRipple2) synaRipple2.style.opacity = "0.18";
                if (synaEqBars) synaEqBars.classList.remove("eq-active");
                if (synaBadge) {{
                    synaBadge.innerText = "🔇 SILENT (LISTENING)";
                    synaBadge.style.background = "rgba(30, 41, 59, 0.85)";
                    synaBadge.style.color = "#94A3B8";
                    synaBadge.style.borderColor = "rgba(148, 163, 184, 0.2)";
                }}
                if (interviewerLiveCaption) {{
                    interviewerLiveCaption.innerText = `🔇 Silent — Listening to ${{CANDIDATE_NAME}}...`;
                }}

                // Bright Highlight on Candidate Panel
                if (candidatePanel) {{
                    candidatePanel.style.borderColor = "#10B981";
                    candidatePanel.style.boxShadow = "0 0 0 3px rgba(16, 185, 129, 0.45), 0 22px 50px -6px rgba(16, 185, 129, 0.7)";
                    candidatePanel.style.opacity = "1";
                    candidatePanel.style.transform = "scale(1.008)";
                }}
                if (candidateRipple) {{
                    candidateRipple.style.opacity = "0.85";
                    candidateRipple.style.animation = "rippleWave 1.5s infinite";
                }}
                if (candidateBadge) {{
                    candidateBadge.innerText = "🎙️ SPEAKING";
                    candidateBadge.style.background = "rgba(16, 185, 129, 0.32)";
                    candidateBadge.style.color = "#D1FAE5";
                    candidateBadge.style.borderColor = "#34D399";
                }}

                // Update Unified Subtitles Bar for Candidate
                let candWords = activeText || liveInterimTranscript || "Speaking...";
                if (candidateLiveCaption) candidateLiveCaption.innerText = candWords;
                if (subtitleBar) {{
                    subtitleBar.style.borderColor = "rgba(16, 185, 129, 0.55)";
                }}
                if (subtitleSpeakerTag) {{
                    subtitleSpeakerTag.innerText = `🎙️ ${{CANDIDATE_NAME}} (SPEAKING)`;
                    subtitleSpeakerTag.style.color = "#D1FAE5";
                    subtitleSpeakerTag.style.background = "rgba(16, 185, 129, 0.28)";
                    subtitleSpeakerTag.style.borderColor = "#34D399";
                }}
                if (transcriptBox) transcriptBox.innerText = candWords;
                if (connDot) connDot.style.background = "#10B981";
                if (connStatusText) connStatusText.innerText = `${{CANDIDATE_NAME}} Speaking`;
                if (turnStateChip) turnStateChip.innerText = `${{INTERVIEWER_NAME}}: Silent (Listening)`;

            }} else if (speaker === "processing") {{
                if (synaEqBars) synaEqBars.classList.remove("eq-active");
                if (synaPanel) synaPanel.style.opacity = "0.9";
                if (candidatePanel) candidatePanel.style.opacity = "0.9";
                if (candidateRipple) {{
                    candidateRipple.style.opacity = "0";
                    candidateRipple.style.animation = "none";
                }}
                if (candidateBadge) {{
                    candidateBadge.innerText = "✓ ANSWER CAPTURED";
                    candidateBadge.style.background = "rgba(99, 102, 241, 0.22)";
                    candidateBadge.style.color = "#A5B4FC";
                }}
                if (synaBadge) {{
                    synaBadge.innerText = "PREPARING RESPONSE";
                    synaBadge.style.background = "rgba(99, 102, 241, 0.22)";
                    synaBadge.style.color = "#A5B4FC";
                }}
                if (connStatusText) connStatusText.innerText = "Processing Answer...";
                if (turnStateChip) turnStateChip.innerText = `${{INTERVIEWER_NAME}} is responding...`;
            }} else {{
                // Waiting for candidate to speak
                if (synaPanel) {{
                    synaPanel.style.borderColor = "rgba(148, 163, 184, 0.14)";
                    synaPanel.style.boxShadow = "0 10px 30px -10px rgba(0,0,0,0.5)";
                    synaPanel.style.opacity = "0.82";
                    synaPanel.style.transform = "scale(1)";
                }}
                if (synaRipple) {{
                    synaRipple.style.opacity = "0";
                    synaRipple.style.animation = "none";
                }}
                if (synaRipple2) synaRipple2.style.opacity = "0.2";
                if (synaEqBars) synaEqBars.classList.remove("eq-active");
                if (synaBadge) {{
                    synaBadge.innerText = "🔇 SILENT (LISTENING)";
                    synaBadge.style.background = "rgba(30, 41, 59, 0.85)";
                    synaBadge.style.color = "#94A3B8";
                }}
                if (interviewerLiveCaption) {{
                    interviewerLiveCaption.innerText = `🔇 Silent — Waiting for ${{CANDIDATE_NAME}} to speak...`;
                }}
                if (candidatePanel) {{
                    candidatePanel.style.borderColor = isMicOn ? "rgba(16, 185, 129, 0.45)" : "rgba(239, 68, 68, 0.4)";
                    candidatePanel.style.boxShadow = "0 10px 30px -10px rgba(0,0,0,0.5)";
                    candidatePanel.style.opacity = "1";
                    candidatePanel.style.transform = "scale(1)";
                }}
                if (candidateRipple) {{
                    candidateRipple.style.opacity = "0";
                    candidateRipple.style.animation = "none";
                }}
                if (candidateBadge) {{
                    candidateBadge.innerText = isMicOn ? "🎤 YOUR TURN — SPEAK NOW" : "🔇 MIC MUTED";
                    candidateBadge.style.background = isMicOn ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)";
                    candidateBadge.style.color = isMicOn ? "#6EE7B7" : "#FCA5A5";
                }}
                if (subtitleSpeakerTag) {{
                    subtitleSpeakerTag.innerText = isMicOn ? `🎤 ${{CANDIDATE_NAME}} (YOUR TURN)` : `🔇 ${{CANDIDATE_NAME}} (MIC MUTED)`;
                    subtitleSpeakerTag.style.color = isMicOn ? "#6EE7B7" : "#FCA5A5";
                    subtitleSpeakerTag.style.background = isMicOn ? "rgba(16, 185, 129, 0.16)" : "rgba(239, 68, 68, 0.16)";
                    subtitleSpeakerTag.style.borderColor = isMicOn ? "rgba(16, 185, 129, 0.35)" : "rgba(239, 68, 68, 0.35)";
                }}
                if (connDot) connDot.style.background = isMicOn ? "#10B981" : "#EF4444";
                if (connStatusText) connStatusText.innerText = isMicOn ? "Connected • Mic Active" : "Mic Muted";
                if (turnStateChip) turnStateChip.innerText = isMicOn ? `${{INTERVIEWER_NAME}}: Silent • Speak naturally` : "Unmute microphone to respond";
            }}
        }}

        function isWithinEchoCooldown() {{
            return (Date.now() - synaSpeechEndedAt) < ECHO_GUARD_COOLDOWN_MS;
        }}

        function getEffectiveSilenceThresholdMs() {{
            if (
                currentCallStage === "INITIAL_GREETING" ||
                currentCallStage === "INTRODUCTION" ||
                currentCallStage === "INTRODUCTION_PLAYING" ||
                currentCallStage === "WAITING_FOR_READINESS"
            ) {{
                return READINESS_SILENCE_MS;
            }}
            const trimmed = (liveInterimTranscript || "").trim().toLowerCase();
            if (!trimmed) return SILENCE_DURATION_MS;
            const midClauseEndings = [" and", " because", " so", " but", " or", " while", " where", " which", " that", " um", " uh", " like"];
            for (let i = 0; i < midClauseEndings.length; i++) {{
                if (trimmed.endsWith(midClauseEndings[i])) {{
                    return SILENCE_DURATION_MS + THINKING_PAUSE_GRACE_MS;
                }}
            }}
            return SILENCE_DURATION_MS;
        }}

        function registerCandidateVoiceActivity(spokenText) {{
            if (isCallEnded || isSynaSpeaking || isWithinEchoCooldown() || !isMicOn || isSubmittingAudio) return;
            const now = Date.now();
            // Guard against interviewer TTS acoustic echo matching currentInterviewerText
            if (spokenText && currentInterviewerText && spokenText.length > 10 && (now - synaSpeechEndedAt) < 2500) {{
                if (currentInterviewerText.toLowerCase().includes(spokenText.toLowerCase())) {{
                    return;
                }}
            }}
            lastVoiceTime = now;
            waitingForCandidateSince = 0;
            if (isWaitingForSilenceStateNotified) {{
                isWaitingForSilenceStateNotified = false;
                fetch(BRIDGE_BASE_URL + "/speaker_state", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ speaker: "candidate", live_transcript: spokenText || liveInterimTranscript || "" }})
                }}).catch(() => {{}});
            }}
            if (!isCandidateSpeaking) {{
                isCandidateSpeaking = true;
                isWaitingForSilenceStateNotified = false;
                speechStartTime = now;
                recordedChunks = [];
                if (mediaRecorder && mediaRecorder.state === "inactive") {{
                    try {{ mediaRecorder.start(200); }} catch (e) {{}}
                }}
                fetch(BRIDGE_BASE_URL + "/speaker_state", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ speaker: "candidate", live_transcript: spokenText || liveInterimTranscript || "" }})
                }}).catch(() => {{}});
            }}
            setVisualSpeakerState("candidate", spokenText || liveInterimTranscript || "Speaking...");
        }}

        function initLiveSpeechRecognition() {{
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) return;
            try {{
                speechRec = new SpeechRec();
                speechRec.continuous = true;
                speechRec.interimResults = true;
                speechRec.lang = "en-US";
                speechRec.onresult = (event) => {{
                    if (isCallEnded || isSynaSpeaking || isWithinEchoCooldown() || !isMicOn || isSubmittingAudio) return;
                    let interim = "";
                    let finalTxt = "";
                    for (let i = 0; i < event.results.length; ++i) {{
                        if (event.results[i].isFinal) {{
                            finalTxt += event.results[i][0].transcript + " ";
                        }} else {{
                            interim += event.results[i][0].transcript;
                        }}
                    }}
                    let combined = (finalTxt + interim).trim();
                    if (combined) {{
                        if (currentInterviewerText && combined.length > 10 && (Date.now() - synaSpeechEndedAt) < 2500) {{
                            if (currentInterviewerText.toLowerCase().includes(combined.toLowerCase())) {{
                                return;
                            }}
                        }}
                        liveInterimTranscript = combined;
                        registerCandidateVoiceActivity(combined);
                        fetch(BRIDGE_BASE_URL + "/speaker_state", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{ speaker: "candidate", live_transcript: combined }})
                        }}).catch(() => {{}});
                    }}
                }};
                speechRec.onerror = () => {{}};
                speechRec.onend = () => {{
                    if (!isCallEnded && !isSynaSpeaking && isMicOn && !isSubmittingAudio) {{
                        try {{ speechRec.start(); }} catch(e) {{}}
                    }}
                }};
                if (!isSynaSpeaking && isMicOn) {{
                    try {{ speechRec.start(); }} catch (e) {{}}
                }}
            }} catch (e) {{}}
        }}

        async function submitCandidateTurn(blobOrNull, transcriptFallback) {{
            if (isCallEnded || isSubmittingAudio || isSynaSpeaking) return;
            const cleanTranscript = (transcriptFallback || liveInterimTranscript || "").trim();
            const wordList = cleanTranscript.split(/\\s+/).filter(w => /[a-zA-Z]/.test(w));
            const hasValidBlob = blobOrNull && blobOrNull.size >= 1200;

            // Reject noise without speech
            if (!hasValidBlob && wordList.length < 1) {{
                if (!isSynaSpeaking) setVisualSpeakerState("waiting");
                return;
            }}

            isSubmittingAudio = true;
            isCandidateSpeaking = false;
            waitingForCandidateSince = 0;
            if (cleanTranscript) {{
                if (transcriptBox) transcriptBox.innerText = cleanTranscript;
                if (candidateLiveCaption) candidateLiveCaption.innerText = cleanTranscript;
            }}
            setVisualSpeakerState("processing");

            let base64Audio = "";
            if (hasValidBlob) {{
                base64Audio = await new Promise((resolve) => {{
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result || "");
                    reader.onerror = () => resolve("");
                    reader.readAsDataURL(blobOrNull);
                }});
            }}

            try {{
                const resp = await fetch(BRIDGE_BASE_URL + "/submit_audio", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        audio_base64: base64Audio,
                        browser_transcript: cleanTranscript,
                        speech_duration_ms: lastTotalSpeechDurationMs,
                        syna_currently_speaking: isSynaSpeaking
                    }})
                }});
                if (resp.ok) {{
                    const data = await resp.json();
                    if (data.status === "noise_ignored" || data.status === "empty_transcript" || data.status === "echo_ignored") {{
                        // Environmental noise or silence filtered by server -> continue listening
                        liveInterimTranscript = "";
                        waitingForCandidateSince = Date.now();
                        if (!isSynaSpeaking && !isCallEnded) {{
                            setVisualSpeakerState("waiting");
                            if (isMicOn && speechRec) {{
                                try {{ speechRec.start(); }} catch (e) {{}}
                            }}
                        }}
                        return;
                    }}
                    if (data.transcript) {{
                        if (transcriptBox) transcriptBox.innerText = data.transcript;
                        if (candidateLiveCaption) candidateLiveCaption.innerText = data.transcript;
                    }}
                    liveInterimTranscript = "";
                    applyServerState(data, true);
                }} else {{
                    await pollServerState();
                }}
            }} catch (err) {{
                await pollServerState();
            }} finally {{
                isSubmittingAudio = false;
                liveInterimTranscript = "";
                lastTotalSpeechDurationMs = 0;
                if (!isSynaSpeaking && !isCallEnded) {{
                    setVisualSpeakerState("waiting");
                    if (isMicOn && speechRec) {{
                        try {{ speechRec.start(); }} catch (e) {{}}
                    }}
                }}
            }}
        }}

        function finalizeCandidateUtterance() {{
            if (!isCandidateSpeaking || isCallEnded || isSubmittingAudio) return;
            const now = Date.now();
            const totalSpeech = now - speechStartTime;
            const silenceWaitMs = Math.max(0, now - lastVoiceTime);
            lastTotalSpeechDurationMs = totalSpeech;
            const capturedWords = (liveInterimTranscript || "").trim();
            const wordList = capturedWords.split(/\\s+/).filter(w => /[a-zA-Z0-9]/.test(w));
            isCandidateSpeaking = false;

            // Reject noise bursts / clicks that are shorter than MIN_SPEECH_MS with fewer than 1 word
            if (totalSpeech < MIN_SPEECH_MS && wordList.length < 1) {{
                if (mediaRecorder && mediaRecorder.state === "recording") {{
                    try {{
                        mediaRecorder._discardNextStop = true;
                        mediaRecorder.stop();
                    }} catch (e) {{}}
                }}
                recordedChunks = [];
                pcmFloatChunks = [];
                waitingForCandidateSince = Date.now();
                setVisualSpeakerState("waiting");
                return;
            }}

            emitClientEvent(
                "CANDIDATE",
                "Silence Detected",
                `End-of-speech silence threshold reached (${{Math.round(silenceWaitMs)}}ms silence after ${{Math.round(totalSpeech)}}ms speech)`,
                silenceWaitMs,
                "SUCCESS",
                {{ silence_ms: silenceWaitMs, speech_duration_ms: totalSpeech }}
            );

            // Build 16kHz 16-bit mono RIFF/WAV blob from captured PCM frames if available
            const wavBlob = encodePCMToWavBlob(pcmFloatChunks, pcmSampleRate);
            pcmFloatChunks = [];

            if (wavBlob && wavBlob.size >= 1200) {{
                if (mediaRecorder && mediaRecorder.state === "recording") {{
                    try {{
                        mediaRecorder._discardNextStop = true;
                        mediaRecorder.stop();
                    }} catch (e) {{}}
                }}
                recordedChunks = [];
                submitCandidateTurn(wavBlob, capturedWords);
                return;
            }}

            if (mediaRecorder && mediaRecorder.state === "recording") {{
                try {{
                    mediaRecorder.stop();
                    return;
                }} catch (e) {{}}
            }}

            if (wordList.length >= 1 || totalSpeech >= MIN_SPEECH_MS) {{
                submitCandidateTurn(null, capturedWords);
            }} else {{
                waitingForCandidateSince = Date.now();
                setVisualSpeakerState("waiting");
            }}
        }}

        function attachAudioCallbacks(audioElem, textForSubtitles, hashKey) {{
            audioElem.ontimeupdate = () => {{
                if (isCallEnded) return;
                if (audioElem.duration && audioElem.duration > 0 && textForSubtitles) {{
                    let ratio = audioElem.currentTime / audioElem.duration;
                    let syncedHtml = renderSynchronizedInterviewerWords(textForSubtitles, ratio);
                    if (transcriptBox) transcriptBox.innerHTML = syncedHtml;
                    if (interviewerLiveCaption) interviewerLiveCaption.innerHTML = syncedHtml;
                }}
            }};
            audioElem.onended = () => {{
                if (isCallEnded) return;
                isSynaSpeaking = false;
                const playbackDurMs = synaPlaybackStartedAt > 0 ? Math.max(0, Date.now() - synaPlaybackStartedAt) : 0;
                synaPlaybackStartedAt = 0;
                synaSpeechEndedAt = Date.now();
                waitingForCandidateSince = Date.now();
                if (transcriptBox && textForSubtitles) transcriptBox.innerText = textForSubtitles;
                if (interviewerLiveCaption && textForSubtitles) interviewerLiveCaption.innerText = textForSubtitles;

                // When introduction finishes, DO NOT auto-advance! Transition to WAITING_FOR_READINESS
                if (
                    currentCallStage === "INITIAL_GREETING" ||
                    currentCallStage === "INTRODUCTION" ||
                    currentCallStage === "INTRODUCTION_PLAYING"
                ) {{
                    currentCallStage = "WAITING_FOR_READINESS";
                    setVisualSpeakerState("waiting", "Before we begin, are you comfortable and ready to start?");
                    emitClientEvent("SYNA", "Audio Playback Finished", "Introduction playback completed", playbackDurMs, "SUCCESS");
                    fetch(BRIDGE_BASE_URL + "/introduction_finished", {{ method: "POST" }}).catch(() => {{}});
                    liveInterimTranscript = "";
                    recordedChunks = [];
                    pcmFloatChunks = [];
                    setTimeout(() => {{
                        if (!isCallEnded && !isSynaSpeaking && isMicOn && speechRec) {{
                            try {{ speechRec.start(); }} catch (e) {{}}
                        }}
                    }}, ECHO_GUARD_COOLDOWN_MS);
                    return;
                }}

                // Otherwise enter candidate listening mode after brief echo cooldown
                currentCallStage = "LISTENING_TO_CANDIDATE";
                liveInterimTranscript = "";
                recordedChunks = [];
                pcmFloatChunks = [];
                setVisualSpeakerState("waiting");
                setTimeout(() => {{
                    if (!isCallEnded && !isSynaSpeaking && isMicOn && speechRec) {{
                        try {{ speechRec.start(); }} catch (e) {{}}
                    }}
                }}, ECHO_GUARD_COOLDOWN_MS);
                fetch(BRIDGE_BASE_URL + "/speaker_state", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        speaker: "none",
                        call_stage: "LISTENING_TO_CANDIDATE",
                        playback_duration_ms: playbackDurMs
                    }})
                }}).catch(() => {{}});
            }};
        }}

        function forceUnlockAndPlayAudio() {{
            if (isCallEnded) return;
            if (unmuteBanner) unmuteBanner.style.display = "none";
            if (pendingAudioB64) {{
                let b64 = pendingAudioB64;
                let sub = pendingAudioSubtitle || currentInterviewerText;
                pendingAudioB64 = "";
                playBase64Audio(b64, sub, true);
            }} else if (synaAudio && synaAudio.paused && synaAudio.src) {{
                isSynaSpeaking = true;
                setVisualSpeakerState("interviewer", currentInterviewerText);
                synaAudio.play().catch(() => {{}});
            }}
        }}

        // Automatically unlock audio on any click or key press in parent or iframe
        try {{
            window.addEventListener("pointerdown", () => {{ if (pendingAudioB64) forceUnlockAndPlayAudio(); }}, {{ passive: true }});
            if (window.parent && window.parent.document) {{
                window.parent.document.addEventListener("pointerdown", () => {{ if (pendingAudioB64) forceUnlockAndPlayAudio(); }}, {{ passive: true }});
            }}
        }} catch (e) {{}}

        let introAudioHash = "";
        let synaPlaybackStartedAt = 0;
        let pcmFloatChunks = [];
        let pcmSampleRate = 16000;
        let scriptProcessorNode = null;

        // Live Activity Log state & controls
        let cachedActivityLogs = [];
        let isLogPaused = false;
        let isLogCollapsed = false;
        let activeLogSpeakerFilter = "ALL";
        let expandedLogSeqIds = new Set();
        let lastRenderedLogCount = -1;
        let lastRenderedTopSeq = -1;
        let logTranscriptsVisible = true;

        function emitClientEvent(speaker, eventName, content, durationMs = null, status = "SUCCESS", details = {{}}) {{
            fetch(BRIDGE_BASE_URL + "/client_event", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    speaker: speaker,
                    event: eventName,
                    content: content,
                    duration_ms: durationMs,
                    status: status,
                    details: details
                }})
            }}).catch(() => {{}});
        }}

        function escapeHtmlText(str) {{
            if (str === null || str === undefined) return "";
            return String(str)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }}

        function toggleLogPause() {{
            isLogPaused = !isLogPaused;
            const btn = document.getElementById("log-pause-btn");
            if (btn) {{
                if (isLogPaused) {{
                    btn.innerText = "⏸ PAUSED";
                    btn.style.background = "rgba(245, 158, 11, 0.22)";
                    btn.style.borderColor = "rgba(245, 158, 11, 0.5)";
                    btn.style.color = "#FCD34D";
                }} else {{
                    btn.innerText = "● LIVE";
                    btn.style.background = "rgba(16, 185, 129, 0.18)";
                    btn.style.borderColor = "rgba(16, 185, 129, 0.45)";
                    btn.style.color = "#6EE7B7";
                    renderActivityLogRows(true);
                }}
            }}
        }}

        function setLogSpeakerFilter(filterVal) {{
            activeLogSpeakerFilter = filterVal;
            ["ALL", "SYNA", "CANDIDATE", "SYSTEM"].forEach(k => {{
                const b = document.getElementById("flt-" + k);
                if (b) {{
                    if (k === filterVal) {{
                        b.style.background = "rgba(99, 102, 241, 0.35)";
                        b.style.color = "#E0E7FF";
                    }} else {{
                        b.style.background = "transparent";
                        b.style.color = "#94A3B8";
                    }}
                }}
            }});
            renderActivityLogRows(true);
        }}

        function toggleLogCollapse() {{
            isLogCollapsed = !isLogCollapsed;
            const container = document.getElementById("activity-log-scroll-container");
            const btn = document.getElementById("log-collapse-btn");
            if (container) container.style.display = isLogCollapsed ? "none" : "block";
            if (btn) btn.innerText = isLogCollapsed ? "▲ Expand" : "▼ Collapse";
        }}

        async function toggleLogPrivacy() {{
            try {{
                const res = await fetch(BRIDGE_BASE_URL + "/log_control", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ action: "toggle_privacy" }})
                }});
                if (res.ok) {{
                    const st = await res.json();
                    logTranscriptsVisible = !!st.log_transcripts_enabled;
                    const btn = document.getElementById("log-privacy-btn");
                    if (btn) btn.innerText = logTranscriptsVisible ? "👁️ Transcripts: ON" : "🔒 Transcripts: MASKED";
                    if (st.activity_logs) {{
                        cachedActivityLogs = st.activity_logs;
                        renderActivityLogRows(true);
                    }}
                }}
            }} catch (e) {{}}
        }}

        async function clearActivityLogs() {{
            try {{
                const res = await fetch(BRIDGE_BASE_URL + "/log_control", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ action: "clear" }})
                }});
                if (res.ok) {{
                    const st = await res.json();
                    cachedActivityLogs = st.activity_logs || [];
                    expandedLogSeqIds.clear();
                    renderActivityLogRows(true);
                }}
            }} catch (e) {{}}
        }}

        function exportActivityLogs(format) {{
            window.open(BRIDGE_BASE_URL + "/export_logs?format=" + encodeURIComponent(format), "_blank");
        }}

        function toggleLogRowDetail(seqId) {{
            if (expandedLogSeqIds.has(seqId)) {{
                expandedLogSeqIds.delete(seqId);
            }} else {{
                expandedLogSeqIds.add(seqId);
            }}
            renderActivityLogRows(true);
        }}

        function renderActivityLogRows(forceRender = false) {{
            if (isLogPaused && !forceRender) return;
            const tbody = document.getElementById("activity-log-tbody");
            if (!tbody) return;

            const errorsOnlyElem = document.getElementById("log-errors-only");
            const errorsOnly = errorsOnlyElem ? errorsOnlyElem.checked : false;

            const filtered = (cachedActivityLogs || []).filter(item => {{
                if (activeLogSpeakerFilter !== "ALL" && item.speaker !== activeLogSpeakerFilter) return false;
                if (errorsOnly && item.status !== "FAILED" && item.status !== "RETRY") return false;
                return true;
            }});

            const latestSeq = filtered.length > 0 ? filtered[filtered.length - 1].seq_id : 0;
            if (!forceRender && filtered.length === lastRenderedLogCount && latestSeq === lastRenderedTopSeq) {{
                return;
            }}
            lastRenderedLogCount = filtered.length;
            lastRenderedTopSeq = latestSeq;

            if (filtered.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="7" style="padding: 14px; text-align: center; color: #64748B; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;">No matching activity log events.</td></tr>`;
                return;
            }}

            let rowsHtml = "";
            for (let i = 0; i < filtered.length; i++) {{
                const row = filtered[i];
                const seqId = row.seq_id || (i + 1);
                const sp = row.speaker || "SYSTEM";
                const st = row.status || "SUCCESS";

                let spBadgeStyle = "background: rgba(148, 163, 184, 0.16); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3);";
                if (sp === "SYNA") {{
                    spBadgeStyle = "background: rgba(99, 102, 241, 0.22); color: #C7D2FE; border: 1px solid rgba(99, 102, 241, 0.45);";
                }} else if (sp === "CANDIDATE") {{
                    spBadgeStyle = "background: rgba(16, 185, 129, 0.22); color: #A7F3D0; border: 1px solid rgba(16, 185, 129, 0.45);";
                }}

                let stBadgeStyle = "background: rgba(16, 185, 129, 0.18); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.4);";
                if (st === "WAITING") {{
                    stBadgeStyle = "background: rgba(59, 130, 246, 0.18); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.4);";
                }} else if (st === "RETRY") {{
                    stBadgeStyle = "background: rgba(245, 158, 11, 0.2); color: #FCD34D; border: 1px solid rgba(245, 158, 11, 0.45);";
                }} else if (st === "FAILED") {{
                    stBadgeStyle = "background: rgba(239, 68, 68, 0.22); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.45);";
                }}

                const displayContent = (!logTranscriptsVisible && row.is_transcript)
                    ? "[Transcript Masked by Privacy Setting]"
                    : (row.content || "");

                const isExpanded = expandedLogSeqIds.has(seqId);
                const rowBg = (i % 2 === 0) ? "rgba(15, 23, 42, 0.55)" : "rgba(30, 41, 59, 0.32)";

                rowsHtml += `
                    <tr onclick="toggleLogRowDetail(${{seqId}})" style="background: ${{rowBg}}; border-bottom: 1px solid rgba(148, 163, 184, 0.08); cursor: pointer; transition: background 0.15s;">
                        <td style="padding: 6px 10px; font-family: 'JetBrains Mono', monospace; font-size: 0.69rem; color: #94A3B8; white-space: nowrap;">${{escapeHtmlText(row.timestamp || "")}}</td>
                        <td style="padding: 6px 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.69rem; color: #64748B; white-space: nowrap;">${{escapeHtmlText(row.elapsed || "00:00")}}</td>
                        <td style="padding: 6px 8px; white-space: nowrap;">
                            <span style="${{spBadgeStyle}} font-family: 'JetBrains Mono', monospace; font-size: 0.63rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;">${{escapeHtmlText(sp)}}</span>
                        </td>
                        <td style="padding: 6px 10px; font-weight: 600; color: #F1F5F9; white-space: nowrap;">${{escapeHtmlText(row.event || "")}}</td>
                        <td style="padding: 6px 10px; color: #CBD5E1; line-height: 1.35; word-break: break-word;">${{escapeHtmlText(displayContent)}}</td>
                        <td style="padding: 6px 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.69rem; color: #A5B4FC; text-align: right; white-space: nowrap;">${{escapeHtmlText(row.duration || "-")}}</td>
                        <td style="padding: 6px 10px; text-align: center; white-space: nowrap;">
                            <span style="${{stBadgeStyle}} font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;">${{escapeHtmlText(st)}}</span>
                        </td>
                    </tr>
                `;

                if (isExpanded) {{
                    const detJson = escapeHtmlText(JSON.stringify(row.details || {{}}, null, 2));
                    rowsHtml += `
                        <tr style="background: rgba(9, 13, 24, 0.98); border-bottom: 1px solid rgba(99, 102, 241, 0.25);">
                            <td colspan="7" style="padding: 8px 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: #A5B4FC;">
                                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 4px; color: #94A3B8;">
                                    <span><b>Seq:</b> #${{seqId}}</span>
                                    <span><b>Exact Time:</b> ${{escapeHtmlText(row.timestamp_ms || row.timestamp)}}</span>
                                    <span><b>State:</b> ${{escapeHtmlText(row.state || "")}}</span>
                                    <span><b>Question:</b> ${{row.question_number ? ("Q" + row.question_number + " (ID=" + row.question_id + ")") : "N/A"}}</span>
                                    <span><b>Session ID:</b> ${{escapeHtmlText(row.session_id || "")}}</span>
                                </div>
                                <pre style="margin: 0; padding: 6px 8px; background: rgba(15, 23, 42, 0.9); border-radius: 6px; color: #E2E8F0; overflow-x: auto; font-size: 0.66rem;">${{detJson}}</pre>
                            </td>
                        </tr>
                    `;
                }}
            }}

            tbody.innerHTML = rowsHtml;

            const autoScrollElem = document.getElementById("log-autoscroll");
            const scrollContainer = document.getElementById("activity-log-scroll-container");
            if (autoScrollElem && autoScrollElem.checked && scrollContainer && !isLogCollapsed) {{
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }}
        }}

        function encodePCMToWavBlob(float32Chunks, sourceSampleRate) {{
            if (!float32Chunks || float32Chunks.length === 0) return null;
            let totalLen = 0;
            for (let i = 0; i < float32Chunks.length; i++) totalLen += float32Chunks[i].length;
            if (totalLen < 800) return null;

            const merged = new Float32Array(totalLen);
            let offset = 0;
            for (let i = 0; i < float32Chunks.length; i++) {{
                merged.set(float32Chunks[i], offset);
                offset += float32Chunks[i].length;
            }}

            const targetRate = 16000;
            const ratio = sourceSampleRate / targetRate;
            const outLength = Math.max(1, Math.round(totalLen / ratio));
            const pcm16 = new Int16Array(outLength);
            for (let i = 0; i < outLength; i++) {{
                const srcIdx = Math.min(totalLen - 1, Math.floor(i * ratio));
                const s = Math.max(-1, Math.min(1, merged[srcIdx]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }}

            const buffer = new ArrayBuffer(44 + pcm16.length * 2);
            const view = new DataView(buffer);
            const writeStr = (pos, str) => {{
                for (let i = 0; i < str.length; i++) view.setUint8(pos + i, str.charCodeAt(i));
            }};
            writeStr(0, "RIFF");
            view.setUint32(4, 36 + pcm16.length * 2, true);
            writeStr(8, "WAVE");
            writeStr(12, "fmt ");
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, 1, true);
            view.setUint32(24, targetRate, true);
            view.setUint32(28, targetRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            writeStr(36, "data");
            view.setUint32(40, pcm16.length * 2, true);
            for (let i = 0; i < pcm16.length; i++) {{
                view.setInt16(44 + i * 2, pcm16[i], true);
            }}
            return new Blob([buffer], {{ type: "audio/wav" }});
        }}

        function computeAudioHash(b64) {{
            if (!b64 || b64.length <= 100) return "";
            let mid = Math.floor(b64.length / 2);
            return (
                b64.length + "_" +
                b64.substring(120, 184) + "_" +
                b64.substring(mid, mid + 64) + "_" +
                b64.substring(Math.max(0, b64.length - 64))
            );
        }}

        function playBase64Audio(b64, subtitleText, forceReplay = false) {{
            if (isCallEnded || !b64 || b64.length <= 100) return;
            let hash = computeAudioHash(b64);
            if (!forceReplay && hash === lastPlayedAudioHash) return;
            // Never replay the introduction greeting audio once the interview has advanced to questions
            if (
                introAudioHash &&
                hash === introAudioHash &&
                currentCallStage !== "INTRODUCTION" &&
                currentCallStage !== "INTRODUCTION_PLAYING" &&
                currentCallStage !== "INITIAL_GREETING" &&
                currentCallStage !== "WAITING_FOR_READINESS"
            ) {{
                return;
            }}
            if (
                currentCallStage === "INTRODUCTION" ||
                currentCallStage === "INTRODUCTION_PLAYING" ||
                currentCallStage === "INITIAL_GREETING"
            ) {{
                if (!introAudioHash) introAudioHash = hash;
            }}
            lastPlayedAudioHash = hash;

            let spokenText = subtitleText || currentInterviewerText || "";
            currentInterviewerText = spokenText;
            if (stagePrompt && spokenText) {{
                stagePrompt.innerText = spokenText;
            }}

            // Stop candidate speech recognition & recording while interviewer speaks (Step 1)
            isSynaSpeaking = true;
            isCandidateSpeaking = false;
            if (speechRec) {{
                try {{ speechRec.stop(); }} catch (e) {{}}
            }}
            if (mediaRecorder && mediaRecorder.state === "recording") {{
                try {{
                    mediaRecorder._discardNextStop = true;
                    mediaRecorder.stop();
                }} catch (e) {{}}
                recordedChunks = [];
            }}

            let mime = (b64.startsWith("UklGR") || b64.startsWith("RIFF")) ? "audio/wav" : "audio/mp3";
            let dataUri = "data:" + mime + ";base64," + b64;

            if (synaAudio) {{
                try {{ synaAudio.pause(); }} catch (e) {{}}
                synaAudio.src = dataUri;
                synaAudio.volume = volSlider ? (volSlider.value / 100.0) : 0.95;
                setVisualSpeakerState("interviewer", spokenText);
                attachAudioCallbacks(synaAudio, spokenText, hash);

                let playPromise = synaAudio.play();
                if (playPromise !== undefined) {{
                    playPromise.then(() => {{
                        synaPlaybackStartedAt = Date.now();
                        lastPlayedAudioHash = hash;
                        pendingAudioB64 = "";
                        if (unmuteBanner) unmuteBanner.style.display = "none";
                        emitClientEvent("SYNA", "Audio Playback Started", spokenText ? spokenText.substring(0, 120) : "Interviewer audio playing", null, "WAITING");
                    }}).catch(() => {{
                        if (localSynaAudio && synaAudio !== localSynaAudio) {{
                            localSynaAudio.src = dataUri;
                            localSynaAudio.volume = volSlider ? (volSlider.value / 100.0) : 0.95;
                            attachAudioCallbacks(localSynaAudio, spokenText, hash);
                            localSynaAudio.play().then(() => {{
                                synaAudio = localSynaAudio;
                                synaPlaybackStartedAt = Date.now();
                                lastPlayedAudioHash = hash;
                                pendingAudioB64 = "";
                                if (unmuteBanner) unmuteBanner.style.display = "none";
                                emitClientEvent("SYNA", "Audio Playback Started", spokenText ? spokenText.substring(0, 120) : "Interviewer audio playing", null, "WAITING");
                            }}).catch(() => {{
                                pendingAudioB64 = b64;
                                pendingAudioSubtitle = spokenText;
                                if (unmuteBanner) unmuteBanner.style.display = "inline-flex";
                            }});
                        }} else {{
                            pendingAudioB64 = b64;
                            pendingAudioSubtitle = spokenText;
                            if (unmuteBanner) unmuteBanner.style.display = "inline-flex";
                        }}
                    }});
                }}
            }}
        }}

        function applyServerState(state, forcePlayNewTurn = false) {{
            if (isCallEnded || !state) return;

            if (state.silence_threshold_ms && state.silence_threshold_ms >= 1500 && state.silence_threshold_ms <= 60000) {{
                SILENCE_DURATION_MS = state.silence_threshold_ms;
            }}
            if (state.max_inactivity_timeout_ms && state.max_inactivity_timeout_ms >= 5000) {{
                MAX_INACTIVITY_WAIT_MS = state.max_inactivity_timeout_ms;
            }}

            if (voiceErrorBanner && voiceErrorText) {{
                if (state.voice_error) {{
                    voiceErrorText.innerText = state.voice_error;
                    voiceErrorBanner.style.display = "block";
                }} else {{
                    voiceErrorBanner.style.display = "none";
                }}
            }}

            if (state.call_stage) {{
                currentCallStage = state.call_stage;
            }}

            // Update Live Activity Log state pill, timing summary, and log rows
            const statePill = document.getElementById("log-live-state-pill");
            if (statePill && (state.flow_state || state.canonical_state || state.call_stage)) {{
                statePill.innerText = `STATE: ${{state.flow_state || state.canonical_state || state.call_stage}}`;
            }}
            if (state.timing_metrics) {{
                const tm = state.timing_metrics;
                const timingSummary = document.getElementById("log-timing-summary");
                if (timingSummary) {{
                    const fmtMs = (v) => (v !== undefined && v !== null) ? (v >= 1000 ? (v / 1000).toFixed(2) + "s" : Math.round(v) + "ms") : "-";
                    timingSummary.innerText = `TTS: ${{fmtMs(tm.last_tts_generation_ms)}} | STT: ${{fmtMs(tm.last_stt_processing_ms)}} | Eval: ${{fmtMs(tm.last_evaluation_ms)}} | Turnaround: ${{fmtMs(tm.last_turnaround_ms)}}`;
                }}
            }}
            if (typeof state.log_transcripts_enabled === "boolean") {{
                logTranscriptsVisible = state.log_transcripts_enabled;
                const pBtn = document.getElementById("log-privacy-btn");
                if (pBtn) pBtn.innerText = logTranscriptsVisible ? "👁️ Transcripts: ON" : "🔒 Transcripts: MASKED";
            }}
            if (Array.isArray(state.activity_logs)) {{
                cachedActivityLogs = state.activity_logs;
                renderActivityLogRows(false);
            }}

            if (state.question_number && state.total_questions) {{
                let qNum = String(Math.max(1, state.question_number)).padStart(2, '0');
                let qTot = String(Math.max(1, state.total_questions)).padStart(2, '0');
                if (headerQuestionCounter) {{
                    headerQuestionCounter.innerText = `QUESTION ${{qNum}} / ${{qTot}}`;
                }}
                if (questionBadgePill) {{
                    questionBadgePill.innerText = `QUESTION ${{qNum}}`;
                }}
                if (headerQuestionBar) {{
                    let pct = Math.min(100, Math.max(5, Math.round((state.question_number / state.total_questions) * 100)));
                    headerQuestionBar.style.width = pct + "%";
                }}
            }}

            if (state.current_category && stageQuestionContext) {{
                stageQuestionContext.innerText = state.current_category;
            }}

            if (state.subtitles && stagePrompt && state.subtitles !== lastPromptText) {{
                lastPromptText = state.subtitles;
                currentInterviewerText = state.subtitles;
                stagePrompt.innerText = state.subtitles;
                if (isSynaSpeaking || state.active_speaker === "syna" || forcePlayNewTurn) {{
                    setVisualSpeakerState("interviewer", state.subtitles);
                }}
            }}

            if (state.live_transcript && isCandidateSpeaking) {{
                setVisualSpeakerState("candidate", state.live_transcript);
            }}

            if (state.current_audio_b64 && state.current_audio_b64.length > 100) {{
                playBase64Audio(state.current_audio_b64, state.subtitles, forcePlayNewTurn);
            }} else if (state.audio_generating) {{
                isSynaSpeaking = true;
                setVisualSpeakerState("interviewer", state.subtitles || currentInterviewerText);
            }}

            if (state.finished || state.exit_requested) {{
                if (state.closing_audio_b64 && state.closing_audio_b64.length > 100) {{
                    playBase64Audio(state.closing_audio_b64, state.subtitles);
                    setTimeout(() => {{ triggerHangup(); }}, 5500);
                }} else {{
                    setTimeout(() => {{ triggerHangup(); }}, 1200);
                }}
            }}
        }}

        async function pollServerState() {{
            if (isCallEnded || isSubmittingAudio) return;
            try {{
                const res = await fetch(BRIDGE_BASE_URL + "/state");
                if (!res.ok) return;
                const state = await res.json();
                applyServerState(state, false);
            }} catch (err) {{}}
        }}

        function startContinuousVAD(stream) {{
            try {{
                vadAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
                pcmSampleRate = vadAudioCtx.sampleRate || 16000;
                const source = vadAudioCtx.createMediaStreamSource(stream);

                // Band-pass filter chain: strip AC hum/rumble (<90Hz) and high-frequency hiss/clicks (>3800Hz)
                const highPassFilter = vadAudioCtx.createBiquadFilter();
                highPassFilter.type = "highpass";
                highPassFilter.frequency.value = 90.0;
                highPassFilter.Q.value = 0.707;

                const lowPassFilter = vadAudioCtx.createBiquadFilter();
                lowPassFilter.type = "lowpass";
                lowPassFilter.frequency.value = 3800.0;
                lowPassFilter.Q.value = 0.707;

                vadAnalyser = vadAudioCtx.createAnalyser();
                vadAnalyser.fftSize = 512;
                vadAnalyser.smoothingTimeConstant = 0.35;

                source.connect(highPassFilter);
                highPassFilter.connect(lowPassFilter);
                lowPassFilter.connect(vadAnalyser);

                // Capture clean mono PCM samples while candidate is speaking so we always produce a standard 16kHz RIFF/WAV blob
                try {{
                    scriptProcessorNode = vadAudioCtx.createScriptProcessor(4096, 1, 1);
                    lowPassFilter.connect(scriptProcessorNode);
                    scriptProcessorNode.connect(vadAudioCtx.destination);
                    scriptProcessorNode.onaudioprocess = (audioProcessingEvent) => {{
                        if (isCandidateSpeaking && !isSynaSpeaking && isMicOn && !isSubmittingAudio) {{
                            const inputData = audioProcessingEvent.inputBuffer.getChannelData(0);
                            pcmFloatChunks.push(new Float32Array(inputData));
                        }}
                    }};
                }} catch (e) {{}}

                vadData = new Uint8Array(vadAnalyser.frequencyBinCount);
                vadTimeData = new Uint8Array(vadAnalyser.fftSize);

                // Route filtered speech audio into MediaRecorder when supported
                let recorderStream = null;
                try {{
                    const filteredDest = vadAudioCtx.createMediaStreamDestination();
                    lowPassFilter.connect(filteredDest);
                    recorderStream = filteredDest.stream;
                }} catch (e) {{
                    recorderStream = new MediaStream(stream.getAudioTracks());
                }}

                mediaRecorder = new MediaRecorder(recorderStream);
                mediaRecorder.ondataavailable = (e) => {{
                    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
                }};
                mediaRecorder.onstop = async () => {{
                    if (mediaRecorder._discardNextStop) {{
                        mediaRecorder._discardNextStop = false;
                        recordedChunks = [];
                        return;
                    }}
                    if (isCallEnded || isSubmittingAudio) return;
                    const blob = recordedChunks.length > 0 ? new Blob(recordedChunks, {{ type: "audio/webm" }}) : null;
                    recordedChunks = [];
                    await submitCandidateTurn(blob, liveInterimTranscript);
                }};

                function checkVoiceActivity() {{
                    if (isCallEnded) return;
                    vadAnimFrameId = requestAnimationFrame(checkVoiceActivity);
                    if (!vadAnalyser) return;

                    vadAnalyser.getByteFrequencyData(vadData);
                    vadAnalyser.getByteTimeDomainData(vadTimeData);

                    // 1. Speech band energy: bins 3 to 35 (~250Hz - ~3400Hz, human voice formants)
                    let speechSum = 0;
                    let speechCount = 0;
                    let speechPeakBin = 0;
                    let maxBin = Math.min(36, vadData.length);
                    for (let i = 3; i < maxBin; i++) {{
                        speechSum += vadData[i];
                        if (vadData[i] > speechPeakBin) speechPeakBin = vadData[i];
                        speechCount++;
                    }}
                    let currentSpeechEnergy = speechCount > 0 ? (speechSum / speechCount) : 0;

                    // 2. High-frequency non-vocal noise band: bins 45 to 90 (~4200Hz - ~8500Hz)
                    let highNoiseSum = 0;
                    let highNoiseCount = 0;
                    for (let i = 45; i < Math.min(90, vadData.length); i++) {{
                        highNoiseSum += vadData[i];
                        highNoiseCount++;
                    }}
                    let highNoiseEnergy = highNoiseCount > 0 ? (highNoiseSum / highNoiseCount) : 0;

                    // 3. Time-domain RMS & Zero-Crossing Rate (ZCR) for voice harmonicity check
                    let sumSq = 0;
                    let zc = 0;
                    for (let i = 0; i < vadTimeData.length; i++) {{
                        let sample = (vadTimeData[i] - 128) / 128.0;
                        sumSq += sample * sample;
                        if (i > 0) {{
                            let prev = (vadTimeData[i - 1] - 128) / 128.0;
                            if ((prev >= 0 && sample < 0) || (prev < 0 && sample >= 0)) zc++;
                        }}
                    }}
                    let rms = Math.sqrt(sumSq / vadTimeData.length);
                    let zcr = zc / vadTimeData.length;

                    if (candWaveBars && candWaveBars.length > 0) {{
                        for (let i = 0; i < candWaveBars.length; i++) {{
                            let binVal = vadData[(i * 4) + 3] || 0;
                            let barH = (isSynaSpeaking || !isMicOn) ? 4 : Math.max(4, Math.min(18, Math.round((binVal / 255) * 20)));
                            candWaveBars[i].style.height = barH + "px";
                            candWaveBars[i].style.opacity = isCandidateSpeaking ? "1" : "0.4";
                        }}
                    }}

                    if (isSynaSpeaking || isWithinEchoCooldown() || !isMicOn || isSubmittingAudio) return;

                    // Continuously update ambient noise floor when not speaking
                    if (!isCandidateSpeaking) {{
                        ambientNoiseFloor = (ambientNoiseFloor * 0.96) + (currentSpeechEnergy * 0.04);
                    }}

                    const dynamicThreshold = Math.max(24.0, ambientNoiseFloor + 13.0);
                    // Human speech has clear harmonic formants (speechPeakBin > currentSpeechEnergy * 1.35)
                    // and speech band dominates high-frequency hiss, with moderate ZCR (< 0.38)
                    const isVocalSpectrum = (
                        currentSpeechEnergy > dynamicThreshold &&
                        speechPeakBin > (ambientNoiseFloor + 22.0) &&
                        currentSpeechEnergy > (highNoiseEnergy * 1.25) &&
                        rms > 0.015 &&
                        zcr < 0.38
                    );

                    if (isVocalSpectrum) {{
                        consecutiveSpeechFrames++;
                        if (consecutiveSpeechFrames >= SPEECH_DEBOUNCE_FRAMES) {{
                            registerCandidateVoiceActivity(liveInterimTranscript);
                        }}
                    }} else {{
                        consecutiveSpeechFrames = 0;
                        if (isCandidateSpeaking) {{
                            let silenceElapsed = Date.now() - lastVoiceTime;
                            let targetSilenceMs = getEffectiveSilenceThresholdMs();
                            if (silenceElapsed >= 1200 && !isWaitingForSilenceStateNotified && currentCallStage !== "WAITING_FOR_READINESS") {{
                                isWaitingForSilenceStateNotified = true;
                                fetch(BRIDGE_BASE_URL + "/speaker_state", {{
                                    method: "POST",
                                    headers: {{ "Content-Type": "application/json" }},
                                    body: JSON.stringify({{ speaker: "waiting_for_silence", live_transcript: liveInterimTranscript || "" }})
                                }}).catch(() => {{}});
                            }}
                            if (silenceElapsed >= 1200 && candidateBadge && currentCallStage !== "WAITING_FOR_READINESS") {{
                                let remSec = Math.max(0, Math.ceil((targetSilenceMs - silenceElapsed) / 1000));
                                candidateBadge.innerText = `⏳ LISTENING (SILENCE GRACE: ${{remSec}}s)`;
                            }}
                            if (silenceElapsed >= targetSilenceMs) {{
                                finalizeCandidateUtterance();
                            }}
                        }}
                    }}
                }}

                checkVoiceActivity();
            }} catch (e) {{}}
        }}

        // Backup turn-completion & 20-second inactivity monitor (runs every 180ms)
        turnMonitorInterval = setInterval(() => {{
            if (isCallEnded || isSynaSpeaking || isWithinEchoCooldown() || !isMicOn || isSubmittingAudio) return;
            const now = Date.now();
            const isReadinessStage = (
                currentCallStage === "INITIAL_GREETING" ||
                currentCallStage === "INTRODUCTION" ||
                currentCallStage === "INTRODUCTION_PLAYING" ||
                currentCallStage === "WAITING_FOR_READINESS"
            );
            // If in readiness stage and candidate has spoken for >= 1.2s with an affirmative word OR total recording exceeds 4.8s (e.g. background room noise), finalize immediately!
            if (isCandidateSpeaking && isReadinessStage) {{
                const lowerInterim = (liveInterimTranscript || "").toLowerCase();
                const hasReadyWord = /\\b(yes|yeah|yep|ready|start|begin|sure|ok|okay|proceed|go|comfortable|set)\\b/.test(lowerInterim);
                if ((hasReadyWord && (now - speechStartTime) >= 1200) || (now - speechStartTime) >= MAX_READINESS_SPEECH_MS) {{
                    finalizeCandidateUtterance();
                    return;
                }}
            }}
            if (isCandidateSpeaking && (now - lastVoiceTime) >= getEffectiveSilenceThresholdMs()) {{
                finalizeCandidateUtterance();
                return;
            }}
            // Configurable 20-second inactivity timeout when candidate has not started speaking
            if (!isCandidateSpeaking && waitingForCandidateSince > 0 && (now - waitingForCandidateSince) >= MAX_INACTIVITY_WAIT_MS) {{
                waitingForCandidateSince = now;
                fetch(BRIDGE_BASE_URL + "/inactivity_timeout", {{ method: "POST" }})
                    .then(r => r.ok ? r.json() : null)
                    .then(data => {{ if (data) applyServerState(data, true); }})
                    .catch(() => {{}});
            }}
        }}, 180);

        async function initStageMedia() {{
            // 1. Immediately start playing interviewer welcome audio BEFORE awaiting camera/mic permissions
            if (INITIAL_AUDIO_B64 && INITIAL_AUDIO_B64.length > 100) {{
                playBase64Audio(INITIAL_AUDIO_B64, INITIAL_PROMPT_TEXT);
            }} else {{
                setVisualSpeakerState("interviewer", INITIAL_PROMPT_TEXT);
            }}
            pollServerState();

            // 2. Start polling server state every 850ms
            pollInterval = setInterval(pollServerState, 850);

            // 3. Initialize camera and microphone VAD with browser echoCancellation, noiseSuppression, and autoGainControl
            const audioConstraints = {{
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                channelCount: 1,
                sampleRate: 16000
            }};
            try {{
                stageStream = await navigator.mediaDevices.getUserMedia({{
                    video: isCameraOn,
                    audio: audioConstraints
                }});
                if (isCameraOn && stageVideo) {{
                    stageVideo.srcObject = stageStream;
                    stageVideo.style.display = "block";
                    stageVideo.play().catch(() => {{}});
                    if (stageFallback) stageFallback.style.display = "none";
                }}
                startContinuousVAD(stageStream);
                initLiveSpeechRecognition();
            }} catch (err) {{
                try {{
                    stageStream = await navigator.mediaDevices.getUserMedia({{
                        audio: audioConstraints
                    }});
                    isCameraOn = false;
                    if (stageVideo) stageVideo.style.display = "none";
                    if (stageFallback) stageFallback.style.display = "flex";
                    if (camBtnLabel) camBtnLabel.innerText = "Cam Off";
                    if (camSubStatus) camSubStatus.innerText = "Audio-Only Studio Mode";
                    startContinuousVAD(stageStream);
                    initLiveSpeechRecognition();
                }} catch (audioErr) {{
                    if (camSubStatus) camSubStatus.innerText = "Please allow microphone access in your browser";
                }}
            }}
        }}

        function toggleStageMic() {{
            if (isCallEnded) return;
            isMicOn = !isMicOn;

            if (stageStream) {{
                const audioTracks = stageStream.getAudioTracks();
                for (let i = 0; i < audioTracks.length; i++) {{
                    audioTracks[i].enabled = isMicOn;
                }}
            }}

            if (!isMicOn) {{
                // Turn Microphone OFF
                if (speechRec) {{
                    try {{ speechRec.stop(); }} catch (e) {{}}
                }}
                if (mediaRecorder && mediaRecorder.state === "recording") {{
                    try {{
                        mediaRecorder._discardNextStop = true;
                        mediaRecorder.stop();
                    }} catch (e) {{}}
                }}
                recordedChunks = [];
                isCandidateSpeaking = false;
                if (micBtnLabel) micBtnLabel.innerText = "Mic Off";
                if (micBtn) {{
                    micBtn.style.borderColor = "#EF4444";
                    micBtn.style.background = "rgba(239, 68, 68, 0.18)";
                    micBtn.style.color = "#FCA5A5";
                }}
                if (!isSynaSpeaking) setVisualSpeakerState("waiting");
            }} else {{
                // Turn Microphone ON
                if (vadAudioCtx && vadAudioCtx.state === "suspended") {{
                    vadAudioCtx.resume().catch(() => {{}});
                }}
                if (speechRec && !isSynaSpeaking) {{
                    try {{ speechRec.start(); }} catch (e) {{}}
                }}
                if (micBtnLabel) micBtnLabel.innerText = "Mic On";
                if (micBtn) {{
                    micBtn.style.borderColor = "rgba(148, 163, 184, 0.2)";
                    micBtn.style.background = "rgba(30, 41, 59, 0.85)";
                    micBtn.style.color = "#E2E8F0";
                }}
                if (!isSynaSpeaking) setVisualSpeakerState("waiting");
            }}
        }}

        async function toggleStageCam() {{
            if (isCallEnded) return;
            isCameraOn = !isCameraOn;

            if (!isCameraOn) {{
                // Turn Camera OFF
                if (stageStream) {{
                    const videoTracks = stageStream.getVideoTracks();
                    for (let i = 0; i < videoTracks.length; i++) {{
                        videoTracks[i].enabled = false;
                    }}
                }}
                if (stageVideo) stageVideo.style.display = "none";
                if (stageFallback) stageFallback.style.display = "flex";
                if (camBtnLabel) camBtnLabel.innerText = "Cam Off";
                if (camBtn) {{
                    camBtn.style.borderColor = "#EF4444";
                    camBtn.style.background = "rgba(239, 68, 68, 0.18)";
                    camBtn.style.color = "#FCA5A5";
                }}
            }} else {{
                // Turn Camera ON
                let hasLiveVideoTrack = false;
                if (stageStream) {{
                    const videoTracks = stageStream.getVideoTracks();
                    for (let i = 0; i < videoTracks.length; i++) {{
                        if (videoTracks[i].readyState === "live") {{
                            videoTracks[i].enabled = true;
                            hasLiveVideoTrack = true;
                        }}
                    }}
                }}
                if (!hasLiveVideoTrack) {{
                    try {{
                        const camStream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                        const newVideoTracks = camStream.getVideoTracks();
                        if (newVideoTracks.length > 0) {{
                            if (stageStream) {{
                                stageStream.addTrack(newVideoTracks[0]);
                            }} else {{
                                stageStream = camStream;
                            }}
                            if (stageVideo) stageVideo.srcObject = stageStream;
                            hasLiveVideoTrack = true;
                        }}
                    }} catch (e) {{
                        isCameraOn = false;
                        if (camBtnLabel) camBtnLabel.innerText = "Cam Off";
                        return;
                    }}
                }}
                if (stageVideo) {{
                    stageVideo.style.display = "block";
                    stageVideo.play().catch(() => {{}});
                }}
                if (stageFallback) stageFallback.style.display = "none";
                if (camBtnLabel) camBtnLabel.innerText = "Cam On";
                if (camBtn) {{
                    camBtn.style.borderColor = "rgba(148, 163, 184, 0.2)";
                    camBtn.style.background = "rgba(30, 41, 59, 0.85)";
                    camBtn.style.color = "#E2E8F0";
                }}
            }}
        }}

        function updateAudioVolume(val) {{
            if (synaAudio) synaAudio.volume = val / 100.0;
            if (localSynaAudio) localSynaAudio.volume = val / 100.0;
            if (volIcon) volIcon.innerText = (val == 0) ? "🔇 Muted" : "🔊 Vol";
        }}

        function toggleMuteAudio() {{
            if (volSlider) {{
                if (volSlider.value > 0) {{
                    volSlider.dataset.prev = volSlider.value;
                    volSlider.value = 0;
                }} else {{
                    volSlider.value = volSlider.dataset.prev || 95;
                }}
                updateAudioVolume(volSlider.value);
            }}
        }}

        function clickStreamlitEndCallButton() {{
            try {{
                if (!window.parent || !window.parent.document) return false;
                const buttons = window.parent.document.querySelectorAll("button");
                for (let b of buttons) {{
                    const label = (b.textContent || b.innerText || "").trim();
                    if (label.includes("End Call") || label.includes("Finish Interview")) {{
                        b.click();
                        return true;
                    }}
                }}
            }} catch (e) {{}}
            return false;
        }}

        async function triggerHangup() {{
            if (isCallEnded) {{
                clickStreamlitEndCallButton();
                return;
            }}
            isCallEnded = true;
            isSynaSpeaking = false;
            isCandidateSpeaking = false;
            isSubmittingAudio = false;

            // 1. Stop interview timer & polling loops
            if (callTimerInterval) {{ clearInterval(callTimerInterval); callTimerInterval = null; }}
            if (pollInterval) {{ clearInterval(pollInterval); pollInterval = null; }}
            if (turnMonitorInterval) {{ clearInterval(turnMonitorInterval); turnMonitorInterval = null; }}
            if (vadAnimFrameId) {{ cancelAnimationFrame(vadAnimFrameId); vadAnimFrameId = null; }}
            window.sessionStorage.removeItem("syna_call_start");

            // 2. Stop speech recognition & audio recording
            if (speechRec) {{
                try {{
                    speechRec.onend = null;
                    speechRec.onresult = null;
                    speechRec.abort();
                }} catch (e) {{}}
                speechRec = null;
            }}
            if (mediaRecorder) {{
                try {{
                    mediaRecorder._discardNextStop = true;
                    mediaRecorder.onstop = null;
                    if (mediaRecorder.state !== "inactive") mediaRecorder.stop();
                }} catch (e) {{}}
                mediaRecorder = null;
            }}
            recordedChunks = [];

            // 3. Stop Web Audio VAD context
            if (vadAudioCtx) {{
                try {{ vadAudioCtx.close(); }} catch (e) {{}}
                vadAudioCtx = null;
                vadAnalyser = null;
            }}

            // 4. Stop microphone & camera tracks immediately
            if (stageStream) {{
                try {{
                    stageStream.getTracks().forEach((t) => {{
                        try {{ t.stop(); }} catch (e) {{}}
                    }});
                }} catch (e) {{}}
                stageStream = null;
            }}
            if (stageVideo) {{
                try {{ stageVideo.srcObject = null; stageVideo.style.display = "none"; }} catch (e) {{}}
            }}
            if (stageFallback) stageFallback.style.display = "flex";

            // 5. Stop interviewer audio playback
            if (synaAudio) {{
                try {{
                    synaAudio.onended = null;
                    synaAudio.ontimeupdate = null;
                    synaAudio.pause();
                    synaAudio.src = "";
                }} catch (e) {{}}
            }}
            if (localSynaAudio) {{
                try {{
                    localSynaAudio.onended = null;
                    localSynaAudio.ontimeupdate = null;
                    localSynaAudio.pause();
                    localSynaAudio.src = "";
                }} catch (e) {{}}
            }}

            // 6. Update UI to ENDED state immediately
            const endBtn = document.getElementById("end-call-btn");
            if (endBtn) endBtn.innerHTML = "<span>Ending Session...</span>";
            if (connStatusText) connStatusText.innerText = "Interview Ended";
            if (connDot) connDot.style.background = "#EF4444";

            // 7. Notify backend bridge server to mark session FINISHED and cancel pending tasks
            try {{
                await fetch(BRIDGE_BASE_URL + "/end_call", {{ method: "POST" }});
            }} catch (e) {{}}

            // 8. Trigger Streamlit transition to Stage 3 Completion Report (with retry safeguard)
            clickStreamlitEndCallButton();
            setTimeout(() => {{ clickStreamlitEndCallButton(); }}, 250);
            setTimeout(() => {{ clickStreamlitEndCallButton(); }}, 700);
        }}

        initStageMedia();
    </script>
    """
    components.html(html_code, height=height + 560)
