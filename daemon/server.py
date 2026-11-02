import argparse
import asyncio
import json
import os
import sys
import threading
import numpy as np
import websockets

from engine import StreamingASREngine

# Global tracking
CONNECTED_CLIENTS = set()
STREAMING_CLIENTS = set()
loop = None
engine = None
loopback = None
tray_icon = None
inference_lock = None


def create_tray_image(color="gray"):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fill_color = (0, 200, 83) if color == "green" else (120, 120, 120)
    draw.ellipse([8, 8, 56, 56], fill=fill_color)
    draw.text((22, 18), "CC", fill="white")
    return img


def update_tray_status(active: bool):
    global tray_icon
    if tray_icon:
        try:
            tray_icon.icon = create_tray_image("green" if active else "gray")
            tray_icon.title = f"Local Live Captions - {'Transcribing' if active else 'Idle'}"
        except Exception:
            pass


async def broadcast_loopback_transcript(payload_data):
    """Sends local loopback audio transcripts only to passive listeners (e.g. browser)."""
    if not payload_data:
        return

    text = payload_data.get("text", "") if isinstance(payload_data, dict) else str(payload_data)
    speaker = payload_data.get("speaker", 0) if isinstance(payload_data, dict) else 0

    if not text.strip():
        return

    payload = json.dumps({"type": "transcript", "text": text, "speaker": speaker})

    # Only send to passive clients; active streaming clients get their own isolated transcripts
    passive_clients = [ws for ws in CONNECTED_CLIENTS if ws not in STREAMING_CLIENTS]
    disconnected = set()
    for ws in passive_clients:
        try:
            await ws.send(payload)
        except Exception:
            disconnected.add(ws)

    CONNECTED_CLIENTS.difference_update(disconnected)


def on_loopback_audio(audio_data):
    """Callback for local desktop soundcard loopback."""
    if not CONNECTED_CLIENTS or engine is None or loop is None or loop.is_closed():
        return

    async def _process():
        async with inference_lock:
            res = await loop.run_in_executor(None, engine.process_audio_chunk, audio_data, "local_loopback")
        if res:
            await broadcast_loopback_transcript(res)

    asyncio.run_coroutine_threadsafe(_process(), loop)


async def client_handler(websocket):
    global loopback
    client_id = f"client_{id(websocket)}"
    CONNECTED_CLIENTS.add(websocket)
    update_tray_status(True)

    # Start loopback capture if on desktop and first passive client connects
    if loopback is not None and len(CONNECTED_CLIENTS) == 1:
        loopback.start(on_loopback_audio)

    try:
        await websocket.send(json.dumps({
            "type": "status",
            "status": "connected",
            "message": "AI Engine ready."
        }))

        async for message in websocket:
            # 1. Binary payload: Client (Android TV) is streaming its own PCM audio
            if isinstance(message, bytes):
                STREAMING_CLIENTS.add(websocket)
                async with inference_lock:
                    result = await loop.run_in_executor(
                        None, engine.process_audio_chunk, message, client_id
                    )

                if result:
                    await websocket.send(json.dumps({
                        "type": "transcript",
                        "text": result["text"],
                        "speaker": result["speaker"]
                    }))

            # 2. String/JSON payload: Heartbeats or UI pings
            elif isinstance(message, str):
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except Exception:
                    pass

    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        STREAMING_CLIENTS.discard(websocket)
        engine.remove_session(client_id)

        if len(CONNECTED_CLIENTS) == 0:
            update_tray_status(False)
            if loopback is not None:
                loopback.stop()


def run_tray():
    global tray_icon
    import pystray

    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Local Live Captions", lambda: None, enabled=False),
        pystray.MenuItem("Exit", on_exit)
    )
    tray_icon = pystray.Icon("LocalLiveCaptions", create_tray_image("gray"), "Local Live Captions - Idle", menu)
    tray_icon.run()


async def main():
    global loop, engine, loopback, inference_lock

    parser = argparse.ArgumentParser(description="Local Live Captions Daemon")
    parser.add_argument("--host", default="0.0.0.0", help="Binding IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    parser.add_argument("--no-loopback", action="store_true", help="Disable local soundcard loopback (for Linux server / compute node)")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray icon (headless mode)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU int8 execution")
    args = parser.parse_args()

    loop = asyncio.get_running_loop()
    inference_lock = asyncio.Lock()

    engine = StreamingASREngine(force_cpu=args.cpu)

    # Initialize loopback only if requested and supported
    if not args.no_loopback:
        try:
            from loopback import LoopbackCapture
            loopback = LoopbackCapture()
            print("[Server] Local soundcard loopback initialized.")
        except Exception as e:
            print(f"[Server Warning] Could not initialize local loopback ({e}). Running in network ingestion mode.")
            loopback = None
    else:
        loopback = None
        print("[Server] Running in pure network compute mode (loopback disabled).")

    # Start system tray on Windows if not running headless
    if sys.platform == "win32" and not args.no_tray:
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()

    server = await websockets.serve(
        client_handler,
        args.host,
        args.port,
        origins=None,
        ping_interval=10,
        ping_timeout=20,
        max_size=10 * 1024 * 1024
    )

    print(f"[Server] WebSocket listening on ws://{args.host}:{args.port}")
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        os._exit(0)