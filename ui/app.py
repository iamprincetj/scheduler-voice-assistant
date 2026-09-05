import sys
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import gradio as gr

from src.stt_engine import WhisperSTT
from src.nlu_extractor import IntentExtractor
from src.calendar_backend import LocalJSONCalendar
from src.pipeline import SchedulerPipeline

from src.notifier import ConsoleNotifier, GoogleCalendarNotifier
from src.reminder_service import ReminderService


# Load the pipeline ONCE at startup - not per request - since loading
# the whisper model is the expensive part

pipeline = SchedulerPipeline(
    stt=WhisperSTT(model_size="base"),
    extractor=IntentExtractor(),
    calendar=LocalJSONCalendar()
)

reminder_service = ReminderService(
    calendar=pipeline.calendar,
    notifier=GoogleCalendarNotifier(),
    lookahead_minutes=15,
)

def start_schedule():
    scheduler = BackgroundScheduler()
    scheduler.add_job(reminder_service.check_and_notify, "interval", minutes=1)
    scheduler.start()
    print("Scheduler started successfully")

start_schedule()

def load_events_table():
    events = json.loads(pipeline.calendar.storage_path.read_text())

    return [
        [
            e.get("person"), e.get("when"),e.get("raw_transcript"), e.get("reminded"),e.get("booked_at")
        ] for e in reversed(events)
    ]


def handle_booking(audio_path):
    if audio_path is None:
        return "⚠️ Please record or upload audio first.", "", "", load_events_table()

    result = pipeline.run(audio_path=audio_path)
    intent = result['intent']
    confirmation = result['confirmation']
    summary = f"**Person:** {intent.person or 'Not detected'}  \n**When:** {intent.parsed_datetime or 'Not detected'}"

    if intent.ambiguous:
        summary += f"  \n⚠️ **Ambiguous phrasing detected.** Candidates: {intent.all_date_candidates}"

    confirmation_text = f"✅ Booked: {confirmation}"

    return result["transcript"], summary, confirmation_text, load_events_table()



with gr.Blocks(title="AI Scheduler Assistant") as demo:
    gr.Markdown("# 🗓️ AI Scheduler Assistant by Prince TJ")
    gr.Markdown(
        "Speak or upload a scheduling request (e.g. *'Schedule a meeting with Sarah tomorrow at 3pm'*) "
        "and the assistant will transcribe it, extract the details, and book the event."
    )

    audio_input = gr.Audio(
        sources=["microphone", "upload"], type="filepath", label="Your scheduling request"
    )
    book_btn = gr.Button("📅 Book It", variant="primary")

    with gr.Row():
        transcript_output = gr.Textbox(label="Transcript", interactive=False)
        summary_output = gr.Markdown(label="Extracted Details")

    confirmation_output = gr.Markdown()

    gr.Markdown("### 📋 Booked Events")
    events_table = gr.Dataframe(
        headers=["Person", "When", "Transcript", "Reminded","Booked At"],
        value=load_events_table(),
        interactive=False,
    )

    book_btn.click(
        fn=handle_booking,
        inputs=[audio_input],
        outputs=[transcript_output, summary_output, confirmation_output, events_table],
    )

if __name__ == "__main__":
    demo.launch()
