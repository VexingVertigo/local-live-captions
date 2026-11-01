import sys

def verify_gpu_support(min_vram_gb: float = 3.5) -> tuple[bool, dict]:
    """
    Checks for a compatible NVIDIA GPU with sufficient VRAM.
    Uses pynvml (or torch fallback).
    """
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            return False, {"error": "No NVIDIA GPU detected on system."}

        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        
        total_vram_gb = round(mem_info.total / (1024 ** 3), 2)
        free_vram_gb = round(mem_info.free / (1024 ** 3), 2)

        if total_vram_gb < min_vram_gb:
            return False, {
                "error": f"GPU '{name}' has {total_vram_gb} GB VRAM. Minimum required: {min_vram_gb} GB."
            }

        return True, {
            "device_name": name,
            "vram_total_gb": total_vram_gb,
            "vram_free_gb": free_vram_gb,
            "driver_version": pynvml.nvmlSystemGetDriverVersion()
        }
    except Exception as nvml_err:
        # Fallback to PyTorch CUDA check
        try:
            import torch
            if not torch.cuda.is_available():
                return False, {"error": "CUDA is not available in PyTorch environment."}
            name = torch.cuda.get_device_name(0)
            total_vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
            if total_vram_gb < min_vram_gb:
                return False, {
                    "error": f"GPU '{name}' has {total_vram_gb} GB VRAM. Minimum required: {min_vram_gb} GB."
                }
            return True, {
                "device_name": name,
                "vram_total_gb": total_vram_gb,
                "vram_free_gb": total_vram_gb
            }
        except Exception as torch_err:
            return False, {"error": f"Hardware detection failed: {str(nvml_err)} | {str(torch_err)}"}

if __name__ == "__main__":
    ok, info = verify_gpu_support()
    print("Compatible:", ok)
    print("Info:", info)