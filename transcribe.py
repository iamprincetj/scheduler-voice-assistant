import whisper

model = whisper.load_model("base")
result = model.transcribe("test1.wav")
print("Transcribe:", result["text"])