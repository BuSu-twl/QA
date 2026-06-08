================================================
        QA Assistant - Offline Version
================================================

[Quick Start]

  Option 1: Double click "start.bat"
    -> Auto start program and open browser

  Option 2: Double click "QAAssistant.exe"
    -> Manually visit http://localhost:5000 in browser

[Login Password]
  xxx

[Files]

  QAAssistant.exe    Main program
  start.bat          Quick start script
  data/              Knowledge base (editable)
    question.xlsx    Questions
    answer.xlsx      Answers
  templates/         Page templates (editable)
  audio/             Pre-generated voice files (offline TTS)
  models/            Voice models (optional)

[Edit Knowledge Base]
  1. Open data/question.xlsx to edit questions
  2. Open data/answer.xlsx to edit answers
  3. Click "Refresh KB" button on page, or restart program

[Pre-generate Audio (Recommended)]
  Run before packaging for offline high-quality voice:
    python generate_audio.py

[Voice Priority]
  1. Pre-generated audio files (offline, best quality)
  2. Windows built-in voice Pyttsx3/SAPI5 (offline, decent quality)
  3. Edge-TTS online (requires internet, best quality)

[Notes]
  - Make sure port 5000 is available
  - Press Ctrl+C in console to stop
  - Restart after editing knowledge base

================================================
