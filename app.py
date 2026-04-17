import streamlit as st
import requests
import boto3
import tempfile
import base64
import os
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# ── CONFIG ─────────────────────────────────────────────
API_BASE = "http://translation-api-alb-1449114033.us-east-1.elb.amazonaws.com"
TRANSLATE_API = f"{API_BASE}/translate"
VOICE_API = f"{API_BASE}/voice-translate"
TRANSCRIBE_API = f"{API_BASE}/transcribe"
TTS_API = f"{API_BASE}/tts"


AWS_REGION = "us-east-1"
OUTPUT_BUCKET = "linguaflow-responses-bucket"

s3 = boto3.client(
    "s3",
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
    region_name=st.secrets["AWS_REGION"]
)

# ── PAGE CONFIG ────────────────────────────────────────
st.set_page_config(page_title="LinguaFlow", layout="wide")

# ── CUSTOM UI STYLE ────────────────────────────────────
st.markdown("""
<style>
.main { background-color: #0e1117; }
h1, h2, h3 { color: #ffffff; }

.title-box {
    background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    color: white;
    margin-bottom: 20px;
}

.result {
    background: #1c1f2b;
    padding: 15px;
    border-radius: 10px;
    margin-top: 10px;
    color: #ffffff;
    border-left: 4px solid #4b6cb7;
}

div.stButton > button {
    background-color: #4b6cb7;
    color: white;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    border: none;
    font-weight: 600;
}

div.stButton > button:hover {
    background-color: #5f7ddb;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION ────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ── LANGUAGES ──────────────────────────────────────────
LANGUAGES = {
    "English": "en", "French": "fr", "Spanish": "es",
    "German": "de", "Italian": "it", "Hebrew": "he", "Chinese": "zh",
    "Japanese": "ja", "Korean": "ko", "Russian": "ru",
    "Portuguese": "pt", "Arabic": "ar", "Hindi": "hi"
}

# ── HEADER ─────────────────────────────────────────────
st.markdown("""
<div class="title-box">
    <h1>🌍 LinguaFlow</h1>
    <p>Translate Text • Voice • Batch Processing</p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    src_name = st.selectbox("Source Language", list(LANGUAGES.keys()))
    tgt_name = st.selectbox("Target Language", list(LANGUAGES.keys()), index=1)

    src_code = LANGUAGES[src_name]
    tgt_code = LANGUAGES[tgt_name]

# ── TABS ───────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📝 Text", "🎤 Voice", "📜 History"])

# ======================================================
# 🟢 TEXT TAB (TEXT + BATCH FIXED)
# ======================================================
with tab1:
    st.subheader("Text & Batch Translation")

    # ── MODE SWITCH ───────────────────────────────────
    mode = st.radio("Choose Mode", ["Text Translation", "Batch Translation"])

    # ── SESSION STATE ────────────────────────────────
    if "translated_text" not in st.session_state:
        st.session_state.translated_text = ""

    if "tts_audio" not in st.session_state:
        st.session_state.tts_audio = None

    if "last_lang_pair" not in st.session_state:
        st.session_state.last_lang_pair = None

    # ── CURRENT LANGUAGE PAIR ────────────────────────
    current_pair = f"{src_code}-{tgt_code}"

    # Reset translation if language changes
    if st.session_state.last_lang_pair != current_pair:
        st.session_state.translated_text = ""
        st.session_state.tts_audio = None
        st.session_state.last_lang_pair = current_pair

    # ==================================================
    # 📝 TEXT TRANSLATION MODE
    # ==================================================
    if mode == "Text Translation":

        text = st.text_area("Enter text", key="input_text")

        if st.button("Translate Text"):

            if not text.strip():
                st.warning("Please enter text")
                st.stop()

            res = requests.post(TRANSLATE_API, json={
                "text": text,
                "source_lang": src_code,
                "target_lang": tgt_code
            })

            data = res.json()

            if "error" in data:
                st.error(data["error"])
            else:
                st.session_state.translated_text = data["translated"]
                st.session_state.tts_audio = None

                st.session_state.history.insert(0, {
                    "type": "text",
                    "original": text,
                    "translated": data["translated"],
                    "time": datetime.now().strftime("%H:%M:%S")
                })

        # ── DISPLAY RESULT ─────────────────────────────
        if st.session_state.translated_text:
            st.markdown("### ✅ Translation")
            st.markdown(
                f"<div class='result'>{st.session_state.translated_text}</div>",
                unsafe_allow_html=True
            )

            # ── READ ALOUD ─────────────────────────────
            if st.button("🔊 Read Aloud"):

                tts = requests.post(
                    TTS_API,
                    json={"text": st.session_state.translated_text}
                ).json()

                st.session_state.tts_audio = s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": OUTPUT_BUCKET,
                        "Key": tts["audio_s3_key"]
                    },
                    ExpiresIn=3600
                )

            # ── AUDIO PLAYER ───────────────────────────
            if st.session_state.tts_audio:
                st.audio(st.session_state.tts_audio)


    # ==================================================
    # 📦 BATCH TRANSLATION MODE
    # ==================================================
    elif mode == "Batch Translation":

        st.markdown("### 📦 Batch Translation (TXT / CSV)")

        uploaded_file = st.file_uploader(
            "Upload file",
            type=["txt", "csv"]
        )

        if uploaded_file:

            st.info("File ready for processing")

            if st.button("Process Batch"):

                file_bytes = uploaded_file.read()
                encoded = base64.b64encode(file_bytes).decode()

                res = requests.post(f"{API_BASE}/batch", json={
                    "filename": uploaded_file.name,
                    "file_content_base64": encoded,
                    "source_lang": src_code,
                    "target_lang": tgt_code
                })

                try:
                    data = res.json()
                except:
                    st.error("Invalid API response")
                    st.text(res.text)
                    st.stop()

                if "error" in data:
                    st.error(data["error"])
                else:
                    st.success("Batch completed successfully!")

                    # ── GENERATE DOWNLOAD LINK ─────────────────────
                    download_url = s3.generate_presigned_url(
                        "get_object",
                        Params={
                            "Bucket": OUTPUT_BUCKET,
                            "Key": data["s3_output_key"]
                        },
                        ExpiresIn=3600
                    )

                    st.success("✅ Batch completed successfully!")

                    # ── DOWNLOAD BUTTON ────────────────────────────
                    st.markdown("### 📥 Download Translated File")

                    st.link_button("⬇️ Download File", download_url)

                    # Optional info
                    st.caption(f"Rows translated: {data['rows_translated']}")
                    st.session_state.history.insert(0, {
                        "type": "batch",
                        "original": uploaded_file.name,
                        "translated": f"{data['rows_translated']} rows translated",
                        "time": datetime.now().strftime("%H:%M:%S")
                    })
# ======================================================
# 🎤 VOICE TAB
# ======================================================
with tab2:
    st.subheader("Voice Translation")

    mode = st.radio("Mode", ["Upload", "Live"])

    def process_audio(file_path, filename):

        with st.spinner("Processing audio..."):
            # ── TRANSCRIBE
            with open(file_path, "rb") as f:
                res = requests.post(
                    TRANSCRIBE_API,
                    files={"file": (filename, f, "audio/wav")}
                )

            if res.status_code != 200:
                st.error("Transcription failed")
                st.text(res.text)
                return

            transcribe_res = res.json()
            transcript = transcribe_res.get("text", "")

            st.markdown("### 📝 Transcript")
            st.markdown(f"<div class='result'>{transcript}</div>", unsafe_allow_html=True)

            # ── VOICE TRANSLATE
            with open(file_path, "rb") as f:
                res = requests.post(
                    VOICE_API,
                    files={"file": (filename, f, "audio/wav")},
                    data={"target_lang": tgt_code}
                )

            if res.status_code != 200:
                st.error("Voice translation failed")
                st.text(res.text)
                return

            voice_res = res.json()

            # ✅ DETECTED LANGUAGE
            detected = voice_res.get("detected_language", "unknown")
            st.markdown(f"### 🌐 Detected Language: {detected}")

            translated = voice_res.get("translated_text", "")

            st.markdown("### 🌍 Translation")
            st.markdown(f"<div class='result'>{translated}</div>", unsafe_allow_html=True)

            # ── AUDIO
            try:
                audio_url = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": OUTPUT_BUCKET, "Key": voice_res["audio_s3_key"]},
                    ExpiresIn=3600
                )
                st.audio(audio_url)
            except:
                audio_url = None

            st.session_state.history.insert(0, {
                "type": "voice",
                "original": transcript,
                "translated": translated,
                "audio": audio_url,
                "time": datetime.now().strftime("%H:%M:%S")
            })

    if mode == "Upload":
        audio_file = st.file_uploader("Upload audio", type=["wav"])

        if audio_file and st.button("Process Audio"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_file.read())
                temp_path = tmp.name

            process_audio(temp_path, audio_file.name)
            os.remove(temp_path)

    else:
        audio = mic_recorder()

        if audio and st.button("Process Recording"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio["bytes"])
                temp_path = tmp.name

            process_audio(temp_path, "live.wav")
            os.remove(temp_path)

# ======================================================
# 📜 HISTORY TAB
# ======================================================
with tab3:
    st.subheader("Translation History")

    if not st.session_state.history:
        st.info("No history yet")

    for item in st.session_state.history:
        st.markdown(f"🕒 {item['time']}")
        st.markdown(f"<div class='result'>Original: {item['original']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='result'>Translated: {item['translated']}</div>", unsafe_allow_html=True)

        if item.get("audio"):
            st.audio(item["audio"])

        st.markdown("---")