from .stt_engine import STTEngine
from .nlu_extractor import IntentExtractor
from .calendar_backend import CalendarBackend


class SchedulerPipeline:
    """"
    Wires STT -> NLU -> Action together. Doesn't know or care which concrete implementation of each layer it's using.    
    """

    def __init__(self, stt: STTEngine, extractor: IntentExtractor, calendar: CalendarBackend):
        self.stt = stt
        self.extractor = extractor
        self.calendar = calendar

        


    def run(self, audio_path: str) -> dict:
        transcript = self.stt.transcribe(audio_path)
        intent = self.extractor.extract(transcript)
        confirmation = self.calendar.book_event(intent)

        return {
            "transcript": transcript,
            "intent": intent,
            "confirmation": confirmation
        }