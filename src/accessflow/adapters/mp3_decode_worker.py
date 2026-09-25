"""Single isolated native decoding job; accepts no transcripts or inference prompts."""

import io
import json
from pathlib import Path
import sys
import wave

from .mp3_decode import admitted_paths, AudioDecodeError, MAX_CLIP_BYTES, MAX_TURN_BYTES, MAX_SECONDS, SAMPLE_RATE


def convert(request_path):
    import av

    request_path = Path(request_path)
    if request_path.stat().st_size > 65536:
        raise AudioDecodeError("Oversized decode request")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    paths = admitted_paths(request["root"], request["references"])
    byte_count = total_samples = 0
    clip_frames = []
    output = request_path.parent / "turn.wav"
    with output.open("xb") as raw, wave.open(raw, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        def append(frame):
            nonlocal total_samples
            total_samples += frame.samples
            if total_samples > SAMPLE_RATE * MAX_SECONDS:
                raise AudioDecodeError("Decoded turn exceeds duration bound")
            data = frame.to_ndarray().astype("<i2", copy=False).tobytes()
            if len(data) != frame.samples * 2:
                raise AudioDecodeError("Unexpected PCM frame format")
            wav.writeframesraw(data)

        for path in paths:
            # Read a bounded byte snapshot. Forcing MP3 over BytesIO prevents a
            # disguised playlist/container from opening network or external files.
            if path.stat().st_size > MAX_CLIP_BYTES:
                raise AudioDecodeError("MP3 clip exceeds size bound")
            with path.open("rb") as stream:
                encoded = stream.read(MAX_CLIP_BYTES + 1)
            byte_count += len(encoded)
            if len(encoded) > MAX_CLIP_BYTES or byte_count > MAX_TURN_BYTES:
                raise AudioDecodeError("Encoded turn exceeds size bound")
            before = total_samples
            with av.open(io.BytesIO(encoded), mode="r", format="mp3") as container:
                if len(container.streams.audio) != 1:
                    raise AudioDecodeError("MP3 must contain one audio stream")
                resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
                for frame in container.decode(audio=0):
                    for normalized in resampler.resample(frame):
                        append(normalized)
                for normalized in resampler.resample(None):
                    append(normalized)
            if total_samples == before:
                raise AudioDecodeError("MP3 contains no decoded audio")
            clip_frames.append(total_samples - before)
    (request_path.parent / "result.json").write_text(json.dumps({"clip_frames": clip_frames}), encoding="utf-8")


def main():
    try:
        if len(sys.argv) != 2:
            return 2
        convert(sys.argv[1])
    except Exception:
        return 2  # Parent reports a stable failure; no raw native error/path leaks.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
