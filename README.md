# ERP Translator

A local Windows desktop MVP that captures visible text (including an RDP window), runs OCR on the local computer, applies an agriculture/packhouse ERP glossary, and displays the English result in an always-on-top window.

Screenshots never leave the computer. The app applies its ERP glossary first, then uses a local Argos Spanish-to-English neural model for unmatched text. No screenshot or recognized text is sent to an online translation service.

Output can be selected in Settings: Spanish, English, French, or Arabic. French and Arabic use local English bridge models so ERP glossary terminology is applied first.

## Requirements

- Windows 10 or 11
- Python 3.11 or newer (install it from python.org if `python --version` does not work)
- [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki), including Spanish language data (`spa`)

## Install

Open PowerShell in this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\install_argos_model.py
```

Install Tesseract. During its installer, select Spanish language data. The usual executable path is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract is not on `PATH`, open **Settings** in the app and browse to that executable. Keep the OCR language as `spa`. To confirm that Spanish data is installed, run:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
```

The output should include `spa`.

The app also supports a project-local Spanish model at `.runtime\tessdata\spa.traineddata`; this is useful when the installer cannot modify its protected system folder.

## Run and test

```powershell
python main.py
```

1. Leave Spanish ERP text visible locally (RDP may be full-screen or windowed).
2. Leave the pointer still over text for about one second to get an automatic compact translation popup. Use the green **Translation Bot: ON** button to pause it; the button turns red and reads **Translation Bot: OFF** while paused.
3. For a precise area, press **Ctrl+Shift+T**, or click **Translate Area**.
4. Drag a rectangle around the text. Press Escape to cancel.
5. Review the OCR source and English glossary translation in the floating result window.
6. Try **Copy English**, **Copy All**, and closing the main window to minimize it to the system tray.

**Translate Clipboard Image** runs the same local OCR flow on an image copied to the Windows clipboard.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Current MVP limitations

- OCR quality depends on font size, contrast, display scaling, and the selected area. Tight selections around readable text work best.
- Hover mode OCRs a small rectangle around the pointer. Dense ERP screens may include neighboring labels; use area selection when you need exact control.
- Tesseract and its Spanish language pack are separate system installations and are not bundled yet.
- Translation quality is strongest for terminology covered by the ERP glossary. The local general-purpose model may still need glossary additions for company-specific language.
- Embedded phrase replacement does not grammatically translate surrounding Spanish.
- Some protected/elevated windows may prevent a non-elevated app from receiving hotkeys or capturing content.
- Packaging with PyInstaller is a later step; run from Python for this milestone.

## Project structure

- `app/gui`: main, selection overlay, results, and settings windows
- `app/services`: local capture, OCR, hotkey, glossary, and translation layers
- `data/glossary.json`: editable ERP terminology and explanations
- `tests`: glossary/translation behavior

User settings and the remembered result-window position are stored in the Windows application configuration directory, not in the repository.
