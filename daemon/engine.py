import torch
from engines.whisper_engine import WhisperASREngine


def detect_hardware_profile(force_cpu: bool = False) -> dict:
    """Inspects CUDA availability and GPU VRAM to recommend the optimal ASR tier."""
    if force_cpu or not torch.cuda.is_available():
        return {
            "device": "cpu",
            "gpu_name": "CPU",
            "vram_gb": 0.0,
            "recommended_tier": "lite",
            "kyutai_model": "kyutai/stt-1b-en_fr",
        }

    props = torch.cuda.get_device_properties(0)
    vram_gb = round(props.total_memory / (1024 ** 3), 2)
    gpu_name = props.name

    if vram_gb < 4.0:
        rec_tier = "lite"
        kyutai_model = "kyutai/stt-1b-en_fr"
    elif vram_gb < 10.0:
        rec_tier = "balanced"
        kyutai_model = "kyutai/stt-1b-en_fr"
    else:
        rec_tier = "stream"
        kyutai_model = "kyutai/stt-2.6b-en"

    return {
        "device": "cuda",
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
        "recommended_tier": rec_tier,
        "kyutai_model": kyutai_model,
    }


def create_asr_engine(tier: str = "auto", force_cpu: bool = False, model_override: str | None = None):
    hw = detect_hardware_profile(force_cpu=force_cpu)
    print(f"[Hardware] Detected {hw['gpu_name']} ({hw['vram_gb']} GB VRAM) -> Recommended tier: '{hw['recommended_tier']}'")

    selected_tier = hw["recommended_tier"] if tier == "auto" else tier.lower()

    if selected_tier == "lite":
        try:
            from engines.parakeet_engine import ParakeetASREngine
            model = model_override or "nemo-parakeet-tdt-0.6b-v2"
            return ParakeetASREngine(model_name=model, force_cpu=force_cpu)
        except ImportError:
            print("[Engine Warning] 'onnx-asr' not installed (pip install onnx-asr[gpu,hub]). Falling back to 'balanced'...")
            selected_tier = "balanced"

    if selected_tier == "stream":
        try:
            from engines.kyutai_engine import KyutaiASREngine
            model = model_override or hw["kyutai_model"]
            return KyutaiASREngine(model_name=model, force_cpu=force_cpu)
        except ImportError:
            print("[Engine Warning] 'moshi' not installed (pip install moshi huggingface-hub). Falling back to 'balanced'...")
            selected_tier = "balanced"

    model = model_override or "large-v3-turbo"
    return WhisperASREngine(model_name=model, force_cpu=force_cpu)