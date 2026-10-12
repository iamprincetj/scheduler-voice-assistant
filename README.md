# Scheduler Voice Assistant

**Turn a thought into a plan, before it slips away.**

A voice-powered scheduling assistant that turns natural speech into structured calendar events through a modular, extensible pipeline.

> _"Schedule a project review with Alex tomorrow at 2 PM."_
> Audio → Text → Structured Intent → Calendar Event

Repository: <https://github.com/iamprincetj/scheduler-voice-assistant>

---

## Table of Contents

- [Overview](#overview)
- [Pipeline](#pipeline)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Google Calendar API Setup](#google-calendar-api-setup)
- [Run the Application](#run-the-application)
- [Platform Notes](#platform-notes)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Scheduling should be as simple as saying what you need to do.

The project separates speech recognition, natural-language understanding, and calendar operations into independent layers. Each layer sits behind an abstract interface, so you can swap speech-to-text engines, intent parsers, and calendar backends without rewriting the rest of the application.

## Pipeline

```
                        Audio File
                            ⬇️
                        [STT Layer]
                            ⬇️
                          Text
                            ⬇️
                        [NLU Layer]
                            ⬇️
                    Structured Intent
                            ⬇️
                       [Action Layer]
                            ⬇️
                        Booked Event
```

| Layer      | Responsibility                                   | Interface         | Current implementation                                                                                                                                |
| ---------- | ------------------------------------------------ | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **STT**    | Audio in, text out                               | `STTEngine`       | Whisper (local). Designed so other engines (e.g. Sahara for the hackathon) can be swapped in, and multiple models can be benchmarked interchangeably. |
| **NLU**    | Text in, structured intent out (who, what, when) | Intent parser     | Rule-based. Swappable for an LLM later without touching other layers.                                                                                 |
| **Action** | Structured intent in, booked event out           | `CalendarBackend` | Local JSON file for development. Google Calendar API is the intended real backend.                                                                    |

> **Implementation note:** Which calendar backend is active depends on the current source code. Configuring Google API credentials alone does **not** automatically replace the local JSON backend. See [Google Calendar API Setup](#google-calendar-api-setup).

## Features

- Voice-driven scheduling workflow
- Local speech recognition with OpenAI Whisper
- Modular, swappable STT interface
- Structured intent extraction (title, participants, date, time)
- Abstract calendar backend (local JSON today, Google Calendar next)
- Layers are independent: change one without touching the others

## Prerequisites

| Requirement    | Purpose                                     |
| -------------- | ------------------------------------------- |
| Git            | Clone the repository                        |
| Python 3       | Run the application                         |
| pip            | Install Python packages                     |
| FFmpeg         | Decode and process audio formats            |
| Whisper        | Local speech recognition                    |
| Google account | Only needed for Google Calendar integration |

> Python version compatibility depends on the project's dependencies and on Whisper (which relies on PyTorch). Check the repository's dependency files and the [Whisper repository](https://github.com/openai/whisper) before choosing a version.

**Recommended environment:** Ubuntu under Windows Subsystem for Linux (WSL), or native Linux.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/iamprincetj/scheduler-voice-assistant.git
cd scheduler-voice-assistant
```

Run all following commands from the repository root.

### 2. Create a Python virtual environment

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Your prompt should now show `(.venv)`. To leave the environment later, run `deactivate`.

### 3. Install system dependencies (FFmpeg)

**Ubuntu / Debian / WSL**

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv python3-pip
ffmpeg -version
```

**macOS (Homebrew)**

```bash
brew install ffmpeg
ffmpeg -version
```

**Windows (Chocolatey)**

```powershell
choco install ffmpeg
ffmpeg -version
```

Or follow the [FFmpeg download guide](https://ffmpeg.org/download.html) and make sure `ffmpeg` is on your `PATH`. Open a new terminal before verifying.

### 4. Install Whisper

With the virtual environment activated:

```bash
python -m pip install -U openai-whisper
whisper --help
```

Optionally test transcription on its own, using a real audio file:

```bash
whisper path/to/audio.wav --model base
```

Whisper downloads the selected model on first use, which requires an internet connection.

**Model selection:** `base` is a good starting point. Smaller models (`tiny`) use fewer resources; larger models give better accuracy at the cost of memory and speed.

Further reading: [OpenAI Whisper](https://github.com/openai/whisper)

### 5. Install project dependencies

```bash
python -m pip install -r requirements.txt
```

If the repository uses `pyproject.toml` or another dependency manager, follow that instead. Then verify Whisper imports correctly:

```bash
python -c "import whisper; print('Whisper is ready')"
```

## Google Calendar API Setup

Only required if you want to use the Google Calendar backend. This follows Google's official guide: [Google Calendar API Python quickstart](https://developers.google.com/calendar/api/quickstart/python).

### Step 1: Create a Google Cloud project

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and sign in.
2. Open the project selector and choose **New Project**.
3. Name it (e.g. `Scheduler Voice Assistant`), create it, and select it.

### Step 2: Enable the Google Calendar API

1. Open the [Google Calendar API page](https://console.cloud.google.com/flows/enableapi?apiid=calendar-json.googleapis.com).
2. Confirm the correct project is selected.
3. Click **Enable** and wait for it to finish.

### Step 3: Configure OAuth consent

1. Open [Google Auth Platform](https://console.cloud.google.com/auth/overview).
2. Set the app name and branding.
3. Provide the required support and developer contact emails.
4. Choose an audience. For personal development, **External** in testing mode works; add your own Google account as a **test user**.

Reference: [Configure OAuth consent](https://developers.google.com/workspace/guides/configure-oauth-consent)

### Step 4: Create OAuth client credentials

1. Open the [Clients page](https://console.cloud.google.com/auth/clients) and click **Create Client**.
2. Choose **Desktop app** as the application type and give it a name.
3. Create it and **download the JSON file**.
4. Rename it to exactly `credentials.json`.
5. Place it where the Google Calendar backend expects it (usually the repository root):

```
scheduler-voice-assistant/
├── credentials.json
├── ui/
├── ...
└── requirements.txt
```

Use the path expected by the code; keep the existing repository structure intact.

### Step 5: Install Google API client libraries

If they are not already in `requirements.txt`:

```bash
python -m pip install --upgrade \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib
```

### Step 6: Authorize your account

On first use, a browser window opens so you can sign in and grant calendar access. A `token.json` file may be created to store the authorization locally.You can run the `text.calendar.py` file to complete this part.

```bash
python3 -m test.calendar.py
```

> **Important:** Google Calendar only works if the active `CalendarBackend` actually implements the API integration and uses these credentials. If the project is configured for the local JSON backend, adding credentials will not switch it over.

## Run the Application

Once everything is installed, activate the virtual environment, go to the repository root, and run:

```bash
python3 -m ui.app
```

If `python3` is not the interpreter of your active environment:

```bash
python -m ui.app
```

### Quick-start checklist

- [ ] Repository cloned
- [ ] Terminal is in the repository root
- [ ] Virtual environment activated
- [ ] FFmpeg installed and on `PATH`
- [ ] Whisper installed and importable
- [ ] Project dependencies installed
- [ ] Google credentials configured (if the active backend needs them)

## Platform Notes

### Windows Subsystem for Linux (WSL), recommended on Windows

If WSL is not installed, follow the [official Microsoft WSL guide](https://learn.microsoft.com/windows/wsl/install). Once Ubuntu is running, follow the Linux instructions above.

- Run the project entirely inside the Linux distribution; don't mix Windows and Linux Python installs.
- Keep the virtual environment on the Linux filesystem.
- Use the Linux versions of Python, pip, and FFmpeg.
- Make sure WSL has internet access for packages and Whisper models.
- If you record from a microphone, verify microphone access works in your WSL audio setup.

### Native Linux

Ubuntu and Debian are the primary documented targets. Other distributions may work, but package names and system dependencies can differ.

### macOS

May run natively if the Python, audio, and UI dependencies support your macOS version. Install Python, FFmpeg, Whisper, and project dependencies, then launch as normal. Microphone permissions, audio device selection, and Apple Silicon compatibility may need extra configuration.

### Native Windows

Not a guaranteed supported environment. It may work with a compatible Python, FFmpeg, Whisper, and all project dependencies. If you hit audio or package issues, use WSL.

## Troubleshooting

| Problem                                          | Fix                                                                                                                                                                                                                                                       |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ffmpeg: command not found`                      | FFmpeg is missing or not on `PATH`. Install it, restart your terminal, run `ffmpeg -version`.                                                                                                                                                             |
| `ModuleNotFoundError: No module named 'whisper'` | Activate the venv and run `python -m pip install -U openai-whisper`.                                                                                                                                                                                      |
| `ModuleNotFoundError` for another package        | Run `python -m pip install -r requirements.txt`. If it isn't declared there, check the project's dependency config.                                                                                                                                       |
| Whisper installation fails                       | Upgrade tooling: `python -m pip install --upgrade pip setuptools wheel`, then see the [Whisper install notes](https://github.com/openai/whisper#setup). Whisper depends on PyTorch.                                                                       |
| Whisper is slow                                  | Speed depends on model size, CPU, RAM, and GPU. Try `tiny` or `base` first.                                                                                                                                                                               |
| `credentials.json` not found                     | Confirm the file was downloaded, is named exactly `credentials.json`, and sits where the backend expects it, relative to the working directory.                                                                                                           |
| Google authorization fails                       | Check that the right Cloud project is selected, the Calendar API is enabled, the client type is **Desktop app**, and your account is added as a test user. See [Google's troubleshooting docs](https://developers.google.com/calendar/api/guides/errors). |
| `No module named 'ui'`                           | Run from the repository root: `cd scheduler-voice-assistant && python3 -m ui.app`. Verify the `ui` package exists in your checkout.                                                                                                                       |
| App runs but no Google Calendar events appear    | The active `CalendarBackend` is probably the local JSON one. Inspect the implementation and confirm event creation calls the Google Calendar API.                                                                                                         |

## Security

This project may access personal calendar data. Treat OAuth credentials and tokens as secrets.

- Never commit `credentials.json` or `token.json`.
- Do not publish client secrets, access tokens, or refresh tokens.
- Keep local configuration out of version control.
- If credentials are exposed, revoke the app's access from your Google Account.
- Request only the calendar permissions the application needs.

Make sure your `.gitignore` includes entries like:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/

# Secrets and local OAuth state
credentials.json
token.json

# Local configuration and runtime data
.env
```

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and test them locally.
4. Keep STT, NLU, and calendar backend responsibilities separate.
5. Open a pull request describing your changes.

When adding a speech engine or calendar backend, implement the existing abstraction (`STTEngine`, `CalendarBackend`) rather than coupling unrelated layers.

## License

See the repository's `LICENSE` file for license terms.

---

**Built with:** [OpenAI Whisper](https://github.com/openai/whisper) · [Google Calendar API](https://developers.google.com/calendar/api)
