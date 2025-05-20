# 1. Imports and Basic Setup
import os
import json
import hmac
import hashlib
import asyncio
import websockets
import uvicorn
import ssl
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from langchain_processor import TranscriptProcessor

# Load environment variables and initialize
load_dotenv()
ZOOM_SECRET_TOKEN = os.getenv("ZOOM_SECRET_TOKEN")
CLIENT_ID = os.getenv("ZM_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZM_CLIENT_SECRET")

app = FastAPI()
port = 3000

# Global state
transcript_processor = TranscriptProcessor()
active_connections = {}

# 2. Step 1 - Webhook Handler (Entry Point of RTMS Flow)
@app.post("/webhook")
async def webhook(request: Request):
    """
    Step 1: Handle meeting.rtms_started - Initial entry point
    Step 10: Handle meeting.rtms_stopped - Cleanup
    """
    try:
        body = await request.json()
        print("Webhook received body:", json.dumps(body, indent=2))
    except Exception as e:
        print("Failed to parse JSON body:", e)
        body = {}
    event = body.get("event")
    print("Parsed event:", event)
    payload = body.get("payload", {})

    # URL validation challenge
    if event == "endpoint.url_validation" and payload.get("plainToken"):
        hash_obj = hmac.new(
            ZOOM_SECRET_TOKEN.encode(),
            payload["plainToken"].encode(),
            hashlib.sha256
        )
        print("Responding to URL validation challenge")
        return {
            "plainToken": payload["plainToken"],
            "encryptedToken": hash_obj.hexdigest()
        }

    # Step 1: Handle meeting.rtms_started - Triggers the WebSocket connection flow
    if event == "meeting.rtms_started":
        print("RTMS Started event received")
        meeting_uuid = payload.get("meeting_uuid")
        rtms_stream_id = payload.get("rtms_stream_id")
        server_urls = payload.get("server_urls")
        if all([meeting_uuid, rtms_stream_id, server_urls]):
            asyncio.create_task(
                handle_signaling_connection(meeting_uuid, rtms_stream_id, server_urls)
            )

    # Step 10: Handle meeting.rtms_stopped
    if event == "meeting.rtms_stopped":
        print("RTMS Stopped event received")
        meeting_uuid = payload.get("meeting_uuid")
        if meeting_uuid in active_connections:
            connections = active_connections[meeting_uuid]
            for conn in connections.values():
                if conn and hasattr(conn, "close"):
                    await conn.close()
            active_connections.pop(meeting_uuid, None)

    return {"status": "ok"}

# 3. Helper Functions
def generate_signature(client_id, meeting_uuid, stream_id, client_secret):
    """
    Generate HMAC-SHA256 signature required by Zoom for authentication
    Format: HMAC(client_id,meeting_uuid,rtms_stream_id)
    """
    message = f"{client_id},{meeting_uuid},{stream_id}"
    return hmac.new(client_secret.encode(), message.encode(), hashlib.sha256).hexdigest()

# 4. WebSocket Connection Handlers
async def handle_signaling_connection(meeting_uuid, stream_id, server_url):
    """
    Steps 2-3: Signaling WebSocket Connection and Handshake
    Steps 7-8: Handle keep-alive
    """
    print("Connecting to signaling WebSocket for meeting", meeting_uuid)
    try:
        async with websockets.connect(server_url) as ws:
            if meeting_uuid not in active_connections:
                active_connections[meeting_uuid] = {}
            active_connections[meeting_uuid]["signaling"] = ws

            # Step 2: Send SIGNALING_HAND_SHAKE_REQ
            signature = generate_signature(CLIENT_ID, meeting_uuid, stream_id, CLIENT_SECRET)
            handshake = {
                "msg_type": 1,  # SIGNALING_HAND_SHAKE_REQ
                "protocol_version": 1,
                "meeting_uuid": meeting_uuid,
                "rtms_stream_id": stream_id,
                "sequence": int(asyncio.get_event_loop().time() * 1e9),
                "signature": signature
            }
            await ws.send(json.dumps(handshake))
            print("Sent signaling handshake (SIGNALING_HAND_SHAKE_REQ)")

            while True:
                try:
                    data = await ws.recv()
                    msg = json.loads(data)
                    print("Signaling Message:", json.dumps(msg, indent=2))

                    # Step 3: Handle SIGNALING_HAND_SHAKE_RESP
                    if msg["msg_type"] == 2 and msg["status_code"] == 0:
                        media_urls = msg.get("media_server", {}).get("server_urls", {})
                        media_url = media_urls.get("transcript") or media_urls.get("all")
                        if media_url:
                            # Step 4: Initialize media connection
                            asyncio.create_task(handle_media_connection(media_url, meeting_uuid, stream_id, ws))

                    # Step 7-8: Handle KEEP_ALIVE
                    if msg["msg_type"] == 12:  # KEEP_ALIVE_REQ
                        await ws.send(json.dumps({
                            "msg_type": 13,  # KEEP_ALIVE_RESP
                            "timestamp": msg["timestamp"]
                        }))
                        print("Responded to signaling keep-alive")

                    # Step 11: Handle STREAM_STATE_UPDATE (TERMINATED)
                    if msg["msg_type"] == 7 and msg.get("state") == 4:
                        print("Received STREAM_STATE_UPDATE (TERMINATED)")
                        break

                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    print("Error processing signaling message:", e)
                    break
    except Exception as e:
        print("Signaling socket error:", e)
    finally:
        print("Signaling socket closed")
        if meeting_uuid in active_connections:
            active_connections[meeting_uuid].pop("signaling", None)

async def handle_media_connection(media_url, meeting_uuid, stream_id, signaling_socket):
    """
    Steps 4-5: Media WebSocket Connection and Handshake
    Steps 7-9: Handle keep-alive and transcript data
    """
    print("Connecting to media WebSocket at", media_url)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(media_url, ssl=ssl_context) as media_ws:
            if meeting_uuid in active_connections:
                active_connections[meeting_uuid]["media"] = media_ws

            # Step 4: Send DATA_HAND_SHAKE_REQ
            signature = generate_signature(CLIENT_ID, meeting_uuid, stream_id, CLIENT_SECRET)
            handshake = {
                "msg_type": 3,  # DATA_HAND_SHAKE_REQ
                "protocol_version": 1,
                "meeting_uuid": meeting_uuid,
                "rtms_stream_id": stream_id,
                "signature": signature,
                "media_type": 8,  # TRANSCRIPT
                "payload_encryption": False
            }
            await media_ws.send(json.dumps(handshake))
            print("Sent media handshake (DATA_HAND_SHAKE_REQ)")

            while True:
                try:
                    data = await media_ws.recv()
                    try:
                        msg = json.loads(data)
                        print("Media Message:", json.dumps(msg, indent=2))

                        # Step 5: Handle DATA_HAND_SHAKE_RESP
                        if msg["msg_type"] == 4 and msg["status_code"] == 0:
                            # Step 6: Send STREAM_STATE_UPDATE (ACTIVE)
                            await signaling_socket.send(json.dumps({
                                "msg_type": 7,  # STREAM_STATE_UPDATE
                                "rtms_stream_id": stream_id
                            }))
                            print("Media handshake success, sent STREAM_STATE_UPDATE")

                        # Step 7-8: Handle KEEP_ALIVE
                        if msg["msg_type"] == 12:  # KEEP_ALIVE_REQ
                            await media_ws.send(json.dumps({
                                "msg_type": 13,  # KEEP_ALIVE_RESP
                                "timestamp": msg["timestamp"]
                            }))
                            print("Responded to media keep-alive")

                        # Step 9: Handle MEDIA_DATA_TRANSCRIPT
                        if msg.get("msg_type") == 17:  # MEDIA_DATA_TRANSCRIPT
                            transcript_text = msg["content"].get("data", "")
                            if transcript_text:
                                transcript_processor.process_new_transcript_chunk(transcript_text)
                    except json.JSONDecodeError:
                        print("Non-JSON media data received")
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    print("Error receiving media message:", e)
                    break
    except Exception as e:
        print("Media socket error:", e)
    finally:
        print("Media socket closed")
        if meeting_uuid in active_connections:
            active_connections[meeting_uuid].pop("media", None)

# 5. Main Entry Point
if __name__ == "__main__":
    print(f"Server running at http://localhost:{port}")
    print(f"Webhook endpoint available at http://localhost:{port}/webhook")
    uvicorn.run(app, host="0.0.0.0", port=port)
