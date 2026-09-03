from src.stt_engine import WhisperSTT
from src.nlu_extractor import IntentExtractor
from src.calendar_backend import LocalJSONCalendar
from src.pipeline import SchedulerPipeline


def main():
    pipeline = SchedulerPipeline(
        stt=WhisperSTT(model_size="base"),
        extractor=IntentExtractor(),
        calendar=LocalJSONCalendar(),
    )

    result = pipeline.run("test1.wav")


    print("Transcript:", result["transcript"])
    print("Person:", result["intent"].person)
    print("When:", result["intent"].parsed_datetime)
    if result['intent'].ambiguous:
        print("⚠️  Ambiguous date/time detected. Candidates found:", result["intent"].all_date_candidates)
    print("Booked event:", result["confirmation"])


if __name__ == "__main__":
    main()