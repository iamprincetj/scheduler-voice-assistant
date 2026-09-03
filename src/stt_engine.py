from abc import ABC, abstractmethod
import whisper

class STTEngine(ABC):
    """
    Base interface all speech-to-text engines must implement
    """

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError




class WhisperSTT(STTEngine):
    """Speech-to-text using Openai's open-source Whisper model"""
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = whisper.load_model(model_size)


    def transcribe(self, audio_path: str) -> str:
        result = self._model.transcribe(audio_path)
        return result['text'].strip()

    
