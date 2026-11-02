import asyncio
import json
import threading
import sys
import os
import numpy as np
import websockets
from PIL import Image, ImageDraw
import pystray

from engine import StreamingASREngine
from loopback import LoopbackCapture

CONNECTED_CLIENTS = set()
loop = None
engine = None
loopback = None
tray_icon = None

def create_tray_image(color="gray"):
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
            tray_icon.title = f"Local Live Captions - {'Transcribing' if active else 'Idle (0 clients)'}"
        except Exception:
            pass

async def broadcast_transcript(text: str):
    if not CONNECTED_CLIENTS or not text.strip():
        return
    payload = json.dumps({"type": "transcript", "text": text})
    disconnected = set()
    for ws in list(CONNECTED_CLIENTS):
        try:
            await ws.send(payload)
        except Exception:
            disconnected.add(ws)
    CONNECTED_CLIENTS.difference_update(disconnected)

def on_audio_chunk(audio_data):
    if not CONNECTED_CLIENTS or engine is None:
        return
    transcript = engine.process_audio_chunk(audio_data)
    if transcript and loop and not loop.is_closed():
        asyncio.run_coroutine_threadsafe(broadcast_transcript(transcript), loop)

async def client_handler(websocket):
    global loopback
    CONNECTED_CLIENTS.add(websocket)
    update_tray_status(True)

    if len(CONNECTED_CLIENTS) == 1 and loopback is not None:
        loopback.start(on_audio_chunk)

    try:
        await websocket.send(json.dumps({
            "type": "status",
            "status": "connected",
            "message": "AI Engine ready."
        }))
        async for _ in websocket:
            pass
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        if len(CONNECTED_CLIENTS) == 0:
            update_tray_status(False)
            if loopback is not None:
                loopback.stop()

def run_tray():
    global tray_icon
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
    global loop, engine, loopback
    loop = asyncio.get_running_loop()

    engine = StreamingASREngine()
    loopback = LoopbackCapture()

    server = await websockets.serve(
        client_handler,
        "0.0.0.0",
        8765,
        origins=None,
        ping_interval=10,
        ping_timeout=20
    )

    await asyncio.Future()

if __name__ == "__main__":
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        os._exit(0)