import os
import tempfile
import subprocess

import importlib.metadata

from typing import BinaryIO, Union
from os import path

import ffmpeg
from fastapi import FastAPI, File, UploadFile, Query, applications, APIRouter
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
# from whisper import tokenizer

# ASR_ENGINE = os.getenv("ASR_ENGINE", "openai_whisper")
# if ASR_ENGINE == "faster_whisper":
#     from .faster_whisper.core import transcribe, language_detection
# else:
#     from .openai_whisper.core import transcribe, language_detection

ASR_ENGINE = "MMS"

SAMPLE_RATE = 16000
LANGUAGE_CODES = ["eng"] # sorted(list(tokenizer.LANGUAGES.keys()))

BASE_URL = os.getenv("BASE_URL", "")

projectMetadata = importlib.metadata.metadata('whisper-asr-webservice')
app = FastAPI(
    title=projectMetadata['Name'].title().replace('-', ' '),
    description=projectMetadata['Summary'],
    version=projectMetadata['Version'],
    contact={
        "url": projectMetadata['Home-page']
    },
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    license_info={
        "name": "MIT License",
        "url": projectMetadata['License']
    },
    docs_url=f"{BASE_URL}/docs",
    openapi_url=f"{BASE_URL}/openapi.json"
)

router = APIRouter(prefix=BASE_URL)


assets_path = os.getcwd() + "/swagger-ui-assets"
if path.exists(assets_path + "/swagger-ui.css") and path.exists(assets_path + "/swagger-ui-bundle.js"):
    app.mount(f"{BASE_URL}/assets",
              StaticFiles(directory=assets_path), name="static")

    def swagger_monkey_patch(*args, **kwargs):
        kwargs["openapi_url"] = f"{BASE_URL}/openapi.json"
        return get_swagger_ui_html(
            *args,
            **kwargs,
            swagger_favicon_url="",
            swagger_css_url=f"{BASE_URL}/assets/swagger-ui.css",
            swagger_js_url=f"{BASE_URL}/assets/swagger-ui-bundle.js",
        )
    applications.get_swagger_ui_html = swagger_monkey_patch


@router.get("/", response_class=RedirectResponse, include_in_schema=False)
async def index():
    return f"{BASE_URL}/docs"


@router.post("/asr", tags=["Endpoints"])
def asr(
    language: Union[str, None] = Query(default="eng", enum=LANGUAGE_CODES),

    audio_file: UploadFile = File(...),
    encode: bool = Query(
        default=True, description="Encode audio first through ffmpeg"),
    output: Union[str, None] = Query(
        default="txt", enum=["txt", "vtt", "srt", "tsv", "json"]),
):
    
    temp_audio_path = load_audio(audio_file.file, encode)

    try:
        result = transcribe(temp_audio_path, language, output)
    finally:
        os.remove(temp_audio_path)

    return StreamingResponse(
        result,  # iter([result]) ?
        media_type="text/plain",
        headers={
            'Asr-Engine': ASR_ENGINE,
            'Content-Disposition': f'attachment; filename="{audio_file.filename}.{output}"'
        })


# @router.post("/detect-language", tags=["Endpoints"])
# def detect_language(
#     audio_file: UploadFile = File(...),
#     encode: bool = Query(
#         default=True, description="Encode audio first through ffmpeg")
# ):
#     detected_lang_code = language_detection(
#         load_audio(audio_file.file, encode))
#     return {"detected_language": tokenizer.LANGUAGES[detected_lang_code], "language_code": detected_lang_code}


app.include_router(router)


def transcribe(audio_file_path: str, language: str, output_format: str):
    """
    Transcribe audio using MMS ASR.
    Parameters:
        audio_file_path (str): Path to the audio file.
        task (str): The task, either 'transcribe' or 'translate'.
        language (str): The language code for transcription.
        initial_prompt (str): An optional initial transcription prompt.
        word_timestamps (bool): Include word-level timestamps if supported.
        output_format (str): Desired output format.
    Returns:
        str: Transcribed text or formatted output.
    """
    try:
        command = [
            'python', 'examples/mms/asr/infer/mms_infer.py',
            '--model', '/content/fairseq/models_new/mms1b_all.pt',
            '--lang', language,
            '--audio', audio_file_path
        ]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"MMS inference failed: {result.stderr}")

        transcription = result.stdout.strip()
        if output_format == "json":
            return {"transcription": transcription}
        elif output_format in ["txt", "vtt", "srt", "tsv"]:
            return transcription
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    except Exception as e:
        raise RuntimeError(f"Transcription error: {str(e)}")


def load_audio(file: BinaryIO, encode=True, sr: int = SAMPLE_RATE):
    """
    Open an audio file object and read as mono waveform, resampling as necessary.
    Modified from https://github.com/openai/whisper/blob/main/whisper/audio.py to accept a file object
    Parameters
    ----------
    file: BinaryIO
        The audio file like object
    encode: Boolean
        If true, encode audio stream to WAV before sending to whisper
    sr: int
        The sample rate to resample the audio if necessary
    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """

    temp_audio_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    
    if encode:
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input("pipe:", threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
                .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=file.read())
            )
        except ffmpeg.Error as e:
            raise RuntimeError(
                f"Failed to load audio: {e.stderr.decode()}") from e
    else:
        with open(temp_audio_path, "wb") as f:
            f.write(file.read())

    return temp_audio_path # np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
