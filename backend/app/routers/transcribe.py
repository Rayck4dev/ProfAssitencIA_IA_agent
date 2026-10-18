"""Endpoint de voz: áudio gravado no navegador -> texto (Whisper)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.dependencies import get_transcription_service
from app.schemas import TranscriptionOut
from app.services.transcription_service import TranscriptionService

router = APIRouter(prefix="/api/transcribe", tags=["Voz"])

MIN_AUDIO_BYTES = 1000  # abaixo disso é uma gravação vazia


@router.post(
    "",
    response_model=TranscriptionOut,
    summary="Transcreve um áudio para texto",
    responses={
        400: {"description": "Áudio vazio ou muito curto"},
        413: {"description": "Áudio maior que o limite"},
        415: {"description": "Formato de áudio não suportado"},
        429: {"description": "Limite de uso da IA atingido"},
        502: {"description": "O Whisper (Groq) não respondeu"},
    },
)
def transcribe(
    request: Request,
    audio: UploadFile = File(..., description="Áudio (webm, ogg, mp4, mp3, wav, flac)"),
    service: TranscriptionService = Depends(get_transcription_service),
) -> TranscriptionOut:
    limit = request.app.state.settings.max_audio_mb * 1024 * 1024
    data = audio.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="Áudio grande demais.")
    if len(data) < MIN_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Áudio vazio ou muito curto.")
    # AIServiceError (formato, limite, falha do Groq) é tratado em main.py.
    return TranscriptionOut(text=service.transcribe(data, audio.content_type or ""))
