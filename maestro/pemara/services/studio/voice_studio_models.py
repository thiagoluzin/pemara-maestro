"""Public, bounded inputs for the local narration and voice-cloning studio."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

IDENTIFIER = r'^[a-f0-9]{32}$'


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


class VoiceCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    transcript: str = Field(min_length=1, max_length=5000)
    description: str = Field(default='', max_length=500)
    authorized: StrictBool

    @model_validator(mode='after')
    def authorization(self):
        if not self.authorized:
            raise ValueError('Confirme a autorização para usar esta voz.')
        return self


class NarrationCreate(StrictModel):
    requestId: str = Field(pattern=IDENTIFIER)
    title: str = Field(default='Nova narração', min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=20000)
    voiceId: str | None = Field(default=None, pattern=IDENTIFIER)
    seed: int = Field(default=123, ge=0, le=2147483647, strict=True)
    temperature: float = Field(default=.8, ge=.1, le=1.5, strict=True)
    topP: float = Field(default=.9, ge=.1, le=1, strict=True)
    topK: int = Field(default=30, ge=1, le=100, strict=True)
    maxFrames: int = Field(default=6144, ge=128, le=65536, strict=True)
    mode: Literal['single', 'chunked'] = 'single'
    chunkLength: int = Field(default=800, ge=32, le=2000, strict=True)

    @model_validator(mode='after')
    def frame_limit(self):
        if self.mode == 'single' and self.maxFrames > 8192:
            raise ValueError('A passagem única admite até 8192 quadros de áudio.')
        return self


class ReviewCreate(StrictModel):
    decision: Literal['pending', 'approved', 'rejected']
    note: str = Field(default='', max_length=2000)
