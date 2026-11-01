import asyncio
import json
import websockets
from hardware import verify_gpu_support
from engine import StreamingASREngine
from loopback import LoopbackCapture

# Connected WebSocket clients (YouTube extension or Desktop HUD)
connected_clients = set()
last_broadcast_text = ""

async def broadcast_transcript(text: str):
    global last_broadcast_text
    if not text or text == last_broadcast_text:
        return
    last_broadcast_text = text
    payload = json.dumps({"type": "transcript", "text": text})
    
    if connected_clients:
        # Broadcast to all open tabs / overlays simultaneously
        await asyncio.gather(
            *[client.send(payload) for client in connected_clients.copy()],
            return_exceptions=True
        )

async def client_handler(websocket):
    connected_clients.add(websocket)
    print(f"[Server] Client connected. Total active: {len(connected_clients)}")
    try:
        # Send instant initial state
        if last_broadcast_text:
            await websocket.send(json.dumps({"type": "transcript", "text": last_broadcast_text}))

        async for message in websocket:
            # Handle client control pings
            try:
                msg = json.loads(message)
                if msg.get("action") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print(f"[Server] Client disconnected. Total active: {len(connected_clients)}")

async def main():
    print("=" * 60)
    print(" Local Live Captions Daemon — NVIDIA Streaming ASR Hub ")
    print("=" * 60)

    # 1. Hardware Pre-flight
    compatible, hw_info = verify_gpu_support()
    if not compatible:
        print(f"\n[ERROR] Hardware check failed:\n -> {hw_info.get('error')}")
        print("This application requires an NVIDIA RTX GPU with at least 3.5 GB VRAM.\n")
        return

    print(f"[OK] GPU Detected: {hw_info['device_name']} ({hw_info['vram_free_gb']} GB free VRAM)")

    # 2. Initialize Streaming Engine
    loop = asyncio.get_running_loop()
    engine = StreamingASREngine()

    def on_audio_chunk(audio_data):
        # Transcribe incoming audio slice
        transcript = engine.process_audio_chunk(audio_data)
        if transcript:
            # Push transcript into the async event loop
            asyncio.run_coroutine_threadsafe(broadcast_transcript(transcript), loop)

    # 3. Start Desktop Audio Loopback
    loopback = LoopbackCapture()
    loopback.start(on_audio_chunk)

    # 4. Start WebSocket Server
    print("[Server] Starting WebSocket server on ws://127.0.0.1:8765")
    async with websockets.serve(client_handler, "127.0.0.1", 8765):
        try:
            await asyncio.Future()  # Run forever
        finally:
            loopback.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Server] Shutting down cleanly.")