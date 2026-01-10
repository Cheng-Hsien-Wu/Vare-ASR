[English](README.md) | [繁體中文](README.zh-TW.md)

# Vare

Batch speech-to-text transcription with a clean GUI. Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) under the hood.

## install

Download the Windows executable from [Releases](https://github.com/Cheng-Hsien-Wu/Vare-ASR/releases).

Or run from source:

```bash
pip install flet faster-whisper ctranslate2 tokenizers huggingface-hub yt-dlp keyring google-genai openai anthropic
python main.py
```

Requires Python 3.12+.

## features

- **Batch transcription** - queue multiple files and process them one by one
- **Model selection** - use any faster-whisper compatible model from HuggingFace
- **URL support** - paste a YouTube/media URL, the app downloads and transcribes it
- **LLM post-processing** - use Gemini/OpenAI/Claude/Ollama to correct transcripts (bring your own API key)
- **SRT output** - generates standard subtitle files
- **GPU acceleration** - CUDA support for faster processing

## default model

[SoybeanMilk/faster-whisper-Breeze-ASR-25](https://huggingface.co/SoybeanMilk/faster-whisper-Breeze-ASR-25), a faster-whisper conversion of MediaTek's [Breeze-ASR-25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25) - optimized for Traditional Chinese.

## config

Settings are stored in `%APPDATA%\Vare\`.

## requirements

- Windows 10/11
- NVIDIA GPU recommended
- Python 3.12+ (if running from source)

## license

MIT
