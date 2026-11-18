"""Run the selected Demucs model with local libsndfile WAV export."""
from pathlib import Path


def main():
    from demucs import audio, separate
    import soundfile

    def save(wav, path, samplerate, bitrate=320, clip="rescale",
             bits_per_sample=16, as_float=False, preset=2):
        if Path(path).suffix.lower() != ".wav":
            return audio.save_audio(wav, path, samplerate, bitrate, clip,
                                    bits_per_sample, as_float, preset)
        samples = audio.prevent_clip(wav, mode=clip).detach().cpu().numpy().T
        subtype = "FLOAT" if as_float else f"PCM_{bits_per_sample}"
        soundfile.write(str(path), samples, samplerate, subtype=subtype, format="WAV")

    separate.save_audio = save
    separate.main()


if __name__ == "__main__":
    main()
