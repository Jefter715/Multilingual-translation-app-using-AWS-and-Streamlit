from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import boto3
import pandas as pd
import uuid
import io
import time
import requests
import base64

# ── Config ─────────────────────────────────────────────
AWS_REGION = "us-east-1"
INPUT_BUCKET = "linguaflow-input-bucket"
OUTPUT_BUCKET = "linguaflow-responses-bucket"

translate_client = boto3.client("translate", region_name=AWS_REGION)
s3_client = boto3.client("s3", region_name=AWS_REGION)
transcribe_client = boto3.client("transcribe", region_name=AWS_REGION)
polly_client = boto3.client("polly", region_name=AWS_REGION)

app = FastAPI(title="LinguaFlow API", version="1.0")


# ── Models ─────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str


class BatchTranslateRequest(BaseModel):
    filename: str
    file_content_base64: str
    source_lang: str
    target_lang: str


class TTSRequest(BaseModel):
    text: str


# ── Health Check ───────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "healthy"}


# ── TRANSLATE ──────────────────────────────────────────
@app.post("/translate")
async def translate_text(request: TranslateRequest):
    try:
        translated_text = translate_client.translate_text(
            Text=request.text,
            SourceLanguageCode=request.source_lang,
            TargetLanguageCode=request.target_lang
        )["TranslatedText"]

        # 🔊 TEXT TO SPEECH
        audio = polly_client.synthesize_speech(
            Text=translated_text,
            OutputFormat="mp3",
            VoiceId="Joanna"
        )["AudioStream"].read()

        audio_key = f"audio/{uuid.uuid4()}.mp3"

        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=audio_key,
            Body=audio,
            ContentType="audio/mpeg"
        )

        return {
            "original": request.text,
            "translated": translated_text,
            "audio_s3_key": audio_key
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ── TRANSCRIBE ONLY ────────────────────────────────────
@app.post("/transcribe")
async def transcribe_only(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()

        key = f"transcribe/{uuid.uuid4()}.wav"
        s3_client.put_object(Bucket=INPUT_BUCKET, Key=key, Body=file_bytes)

        file_uri = f"s3://{INPUT_BUCKET}/{key}"
        job_name = f"job-{uuid.uuid4()}"

        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": file_uri},
            MediaFormat="wav",
            IdentifyLanguage=True
        )

        # polling
        while True:
            result = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )

            status = result["TranscriptionJob"]["TranscriptionJobStatus"]

            if status in ["COMPLETED", "FAILED"]:
                break

            time.sleep(3)

        if status == "FAILED":
            raise HTTPException(status_code=500, detail="Transcription failed")

        transcript_url = result["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        transcript_json = requests.get(transcript_url).json()

        text = transcript_json["results"]["transcripts"][0]["transcript"]

        return {"text": text}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── TEXT TO SPEECH (POLLY) ─────────────────────────────
@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        response = polly_client.synthesize_speech(
            Text=request.text,
            OutputFormat="mp3",
            VoiceId="Joanna"
        )

        audio = response["AudioStream"].read()

        key = f"tts/{uuid.uuid4()}.mp3"

        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=key,
            Body=audio,
            ContentType="audio/mpeg"
        )

        return {"audio_s3_key": key}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── FULL VOICE PIPELINE ────────────────────────────────
@app.post("/voice-translate")
async def voice_translate(file: UploadFile = File(...), target_lang: str = Form(...)):
    try:
        file_bytes = await file.read()

        key = f"audio/{uuid.uuid4()}_{file.filename}"
        s3_client.put_object(Bucket=INPUT_BUCKET, Key=key, Body=file_bytes)

        file_uri = f"s3://{INPUT_BUCKET}/{key}"
        job_name = f"job-{uuid.uuid4()}"

        # ── START TRANSCRIPTION ─────────────────────────
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": file_uri},
            MediaFormat=file.filename.split(".")[-1].lower(),
            IdentifyLanguage=True
        )

        timeout = 0

        while True:
            result = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )

            status = result["TranscriptionJob"]["TranscriptionJobStatus"]

            if status in ["COMPLETED", "FAILED"]:
                break

            time.sleep(5)
            timeout += 5

            if timeout > 300:
                raise Exception("Transcription timeout - job took too long")

        if status == "FAILED":
            raise Exception("Transcription failed")

        # ── LANGUAGE FIX ───────────────────────────────
        detected_lang = result["TranscriptionJob"].get("LanguageCode", "en")
        detected_lang = detected_lang.split("-")[0]

        # ── GET TRANSCRIPT ─────────────────────────────
        transcript_url = result["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        transcript_json = requests.get(transcript_url).json()

        transcript_text = transcript_json["results"]["transcripts"][0]["transcript"]

        # ── TRANSLATE ───────────────────────────────────
        translated_text = translate_client.translate_text(
            Text=transcript_text,
            SourceLanguageCode=detected_lang,
            TargetLanguageCode=target_lang
        )["TranslatedText"]

        # ── POLLY TTS ───────────────────────────────────
        audio = polly_client.synthesize_speech(
            Text=translated_text,
            OutputFormat="mp3",
            VoiceId="Joanna"
        )["AudioStream"].read()

        audio_key = f"audio/{uuid.uuid4()}.mp3"

        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=audio_key,
            Body=audio,
            ContentType="audio/mpeg"
        )

        return {
            "transcribed_text": transcript_text,
            "translated_text": translated_text,
            "detected_language": detected_lang,
            "audio_s3_key": audio_key
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ── BATCH ──────────────────────────────────────────────
@app.post("/batch")
async def batch_translate(request: BatchTranslateRequest):
    try:
        file_bytes = base64.b64decode(request.file_content_base64)
        file_buffer = io.BytesIO(file_bytes)

        input_key = f"input/{uuid.uuid4()}_{request.filename}"
        s3_client.put_object(Bucket=INPUT_BUCKET, Key=input_key, Body=file_bytes)

        translated_rows = []

        if request.filename.lower().endswith(".csv"):
            df = pd.read_csv(file_buffer)

            if "text" not in df.columns:
                raise HTTPException(status_code=400, detail="CSV must have 'text' column")

            for _, row in df.iterrows():
                translated = translate_client.translate_text(
                    Text=str(row["text"]),
                    SourceLanguageCode=request.source_lang,
                    TargetLanguageCode=request.target_lang
                )["TranslatedText"]

                translated_rows.append(translated)

            df["translated"] = translated_rows
            output_buffer = io.StringIO()
            df.to_csv(output_buffer, index=False)
            output_bytes = output_buffer.getvalue().encode("utf-8")

        else:
            lines = file_bytes.decode("utf-8").splitlines()

            for line in lines:
                translated = translate_client.translate_text(
                    Text=line,
                    SourceLanguageCode=request.source_lang,
                    TargetLanguageCode=request.target_lang
                )["TranslatedText"]

                translated_rows.append(translated)

            output_bytes = "\n".join(translated_rows).encode("utf-8")

        output_key = f"output/{uuid.uuid4()}_{request.filename}"
        s3_client.put_object(Bucket=OUTPUT_BUCKET, Key=output_key, Body=output_bytes)

        return {
            "s3_input_key": input_key,
            "s3_output_key": output_key,
            "rows_translated": len(translated_rows)
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── HISTORY ─────────────────────────────────────────────
@app.get("/history")
async def list_history(bucket: str = OUTPUT_BUCKET, prefix: str = "output/"):
    try:
        resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        files = [obj["Key"] for obj in resp.get("Contents", [])]
        return {"files": files}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)