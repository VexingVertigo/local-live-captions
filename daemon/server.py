import asyncio
import json
import websockets
from engine import StreamingASREngine
from loopback import LoopbackCapture

CONNECTED_CLIENTS = set()
loop = None

async def broadcast_transcript(text: str):
    if not CONNECTED_CLIENTS or not text.strip():
        return
    print(f"[ASR] -> \"{text}\"")
    payload = json.dumps({"type": "transcript", "text": text})
    disconnected = set()
    for ws in CONNECTED_CLIENTS:
        try:
            await ws.send(payload)
        except Exception:
            disconnected.add(ws)
    CONNECTED_CLIENTS.difference_update(disconnected)

async def client_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[Server] Client connected. Total active: {len(CONNECTED_CLIENTS)}")
    try:
        await websocket.send(json.dumps({
            "type": "status",
            "status": "connected",
            "message": "AI Engine ready. Transcribing desktop audio..."
        }))
        async for message in websocket:
            pass  # Keepalive listener
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        print(f"[Server] Client disconnected. Total active: {len(CONNECTED_CLIENTS)}")

async def main():
    global loop
    loop = asyncio.get_running_loop()

    # 1. Initialize NVIDIA Streaming ASR Engine
    engine = StreamingASREngine()

    # 2. Audio Processing Callback
    def on_audio_chunk(audio_data):
        transcript = engine.process_audio_chunk(audio_data)
        if transcript:
            asyncio.run_coroutine_threadsafe(broadcast_transcript(transcript), loop)

    # 3. Start Loopback Capture
    loopback = LoopbackCapture()
    loopback.start(on_audio_chunk)

    # 4. Start WebSocket Server with Keepalive
    print("[Server] Starting WebSocket server on ws://127.0.0.1:8765")
    async with websockets.serve(
        client_handler,
        "0.0.0.0",
        8765,
        origins=None,
        ping_interval=10,
        ping_timeout=20
    ):
        try:
            await asyncio.Future()
        finally:
            loopback.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Server] Shutting down cleanly.")