"""
CLI Tool for Audio/Video Transcription
Supports both Transformers and Faster-Whisper backends
"""
import argparse
import os
import sys
from pathlib import Path

from core.utils.srt_utils import save_srt, save_txt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video files using Vare"
    )
    
    parser.add_argument(
        "input",
        type=str,
        help="Input audio/video file path"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input_name.srt)"
    )
    
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["srt", "txt"],
        default="srt",
        help="Output format (default: srt)"
    )
    
    # Note: Only faster-whisper backend is supported now
    # The --backend argument is kept for backwards compatibility but ignored
    
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=None,
        help="Model name (auto-selected based on backend if not specified)"
    )
    
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="zh",
        help="Language code: zh, en, etc. (default: zh)"
    )
    
    parser.add_argument(
        "-d", "--device",
        type=str,
        choices=["cuda", "cpu"],
        default="cuda",
        help="Device to use (default: cuda)"
    )
    
    parser.add_argument(
        "--dtype",
        type=str,
        choices=["float16", "float32"],
        default="float16",
        help="Compute dtype (default: float16)"
    )
    
    # Legacy args (kept for compatibility, ignored)
    
    # Faster-Whisper backend specific
    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="[Faster-Whisper] Disable Silero VAD"
    )
    
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.5,
        help="[Faster-Whisper] VAD speech threshold (default: 0.5)"
    )
    
    parser.add_argument(
        "--vad-min-silence",
        type=int,
        default=300,
        help="[Faster-Whisper] VAD min silence duration in ms (default: 300)"
    )
    
    parser.add_argument(
        "--vad-max-speech",
        type=float,
        default=15.0,
        help="[Faster-Whisper] VAD max speech duration in seconds (default: 15)"
    )
    
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="[Faster-Whisper] Beam search size (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    
    # Set default model (faster-whisper only)
    if args.model is None:
        args.model = "SoybeanMilk/faster-whisper-Breeze-ASR-25"
    
    # Determine output path
    if args.output is None:
        input_path = Path(args.input)
        args.output = str(input_path.with_suffix(f".{args.format}"))
    
    print("=" * 60)
    print("Vare Transcription Tool")
    print("=" * 60)
    print(f"Backend:  {args.backend}")
    print(f"Input:    {args.input}")
    print(f"Output:   {args.output}")
    print(f"Format:   {args.format}")
    print(f"Model:    {args.model}")
    print(f"Language: {args.language}")
    print(f"Device:   {args.device} ({args.dtype})")
    
    if not getattr(args, 'no_vad', False):
        print(f"VAD:      Enabled (threshold={args.vad_threshold}, "
              f"max_speech={args.vad_max_speech}s)")
    
    print("=" * 60)
    
    try:
        # Initialize backend (faster-whisper only)
        print("\n[1/3] Loading model...")
        
        from features.transcription.engines.faster_whisper import FasterWhisperBackend
        
        backend = FasterWhisperBackend(
            model_name=args.model,
            device=args.device,
            compute_type=args.dtype
        )
        backend.load_model()
        
        # Transcribe
        print("\n[2/3] Transcribing audio...")
        segments = backend.transcribe(
            args.input,
            language=args.language,
            beam_size=args.beam_size,
            vad_filter=not getattr(args, 'no_vad', False),
            vad_parameters={
                "threshold": args.vad_threshold,
                "min_silence_duration_ms": args.vad_min_silence,
                "max_speech_duration_s": args.vad_max_speech,
            }
        )
        
        # Save output
        print("\n[3/3] Saving output...")
        if args.format == "srt":
            save_srt(segments, args.output)
        else:
            save_txt(segments, args.output)
        
        # Clean up
        backend.unload_model()
        
        print("\n" + "=" * 60)
        print("✓ Transcription completed successfully!")
        print(f"✓ Output saved to: {args.output}")
        print(f"✓ Total segments: {len(segments)}")
        
        if segments:
            total_duration = segments[-1].end
            avg_duration = sum(s.end - s.start for s in segments) / len(segments)
            print(f"✓ Total duration: {total_duration:.2f} seconds")
            print(f"✓ Average segment length: {avg_duration:.2f} seconds")
        
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
        
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
