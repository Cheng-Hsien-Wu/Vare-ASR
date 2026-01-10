[English](README.md) | [繁體中文](README.zh-TW.md)

# Vare

批次語音轉文字工具，介面簡潔，使用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 引擎。

## 安裝

從 [Releases](https://github.com/Cheng-Hsien-Wu/Vare-ASR/releases) 下載 Windows 執行檔。

或從原始碼執行：

```bash
pip install flet faster-whisper ctranslate2 tokenizers huggingface-hub yt-dlp keyring google-genai openai anthropic
python main.py
```

需要 Python 3.12 以上。

## 功能

- **批次轉錄** - 加入多個檔案，依序處理
- **模型選擇** - 可使用任何 HuggingFace 上 faster-whisper 相容的模型
- **網址支援** - 貼上 YouTube 或媒體網址，自動下載並轉錄
- **LLM 校正** - 使用 Gemini/OpenAI/Claude/Ollama 校正逐字稿（需自備 API Key）
- **SRT 輸出** - 產生標準字幕檔
- **GPU 加速** - 支援 CUDA

## 預設模型

預設使用 [SoybeanMilk/faster-whisper-Breeze-ASR-25](https://huggingface.co/SoybeanMilk/faster-whisper-Breeze-ASR-25)，這是聯發科 [Breeze-ASR-25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25) 的 faster-whisper 版本，針對臺灣繁體中文強化。

## 設定檔位置

設定儲存在 `%APPDATA%\Vare\`。

## 系統需求

- Windows 10/11
- **NVIDIA 顯示卡** (建議使用，以啟用 GPU 加速)
  - 需安裝 [NVIDIA 驅動程式](https://www.nvidia.com/Download/index.aspx)
  - 需安裝系統級 [CUDA Toolkit 12](https://developer.nvidia.com/cuda-downloads) 
- Python 3.10 以上（從原始碼執行時）

## 授權

MIT
