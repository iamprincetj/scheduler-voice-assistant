# SCHEDULER VOICE ASSISTANT

A voice assistant for scheduling your daily life and work.

# PIPELINE

```
audio file → [STT Layer] → text → [NLU Layer] → structured intent → [Action Layer] → booked event
```

- STT Layer — only knows "audio in, text out." Built behind an abstract STTEngine interface. This is the layer where you'll swap in Sahara for the real hackathon, and where your benchmark step will plug in multiple models interchangeably.
- NLU Layer — only knows "text in, structured intent out" (who, what, when). Rule-based for now; swappable for an LLM later without touching anything else.
- Action Layer — only knows "structured intent in, booked event out." Built behind an abstract CalendarBackend interface — today it's a local JSON file, later it's a real Google Calendar API call, and the rest of your code won't need to change at all.
