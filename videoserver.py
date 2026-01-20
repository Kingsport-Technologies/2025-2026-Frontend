#!/usr/bin/env python3
"""
Simple WebRTC server using aiortc that streams the local camera to connected clients.

Dependencies:
  pip install aiortc aiohttp opencv-python av

Run:
  python videoserver.py
Open in your browser:
  http://localhost:8080/
"""

import asyncio
import fractions
import json
import logging
import time
from aiohttp import web
import cv2
import av
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import aiohttp_cors

logging.basicConfig(level=logging.INFO)
pcs = set()

# Open camera once and reuse it for all connections
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not camera.isOpened():
    raise RuntimeError("Cannot open camera")

class CameraVideoTrack(VideoStreamTrack):
    """A video track that returns frames from a OpenCV camera."""
    def __init__(self, camera):
        super().__init__()  # don't forget this!
        self.camera = camera
        self._counter = 0
        self._time_base = fractions.Fraction(1, 30)  # 30 fps

    async def recv(self):
        # Read frame from camera
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self.camera.read)
        if not ret:
            raise RuntimeError("Failed to read frame from camera")

        # Convert BGR (OpenCV) to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create an av.VideoFrame and set timing
        av_frame = av.VideoFrame.from_ndarray(frame, format='rgb24')
        self._counter += 1
        av_frame.pts = self._counter
        av_frame.time_base = self._time_base
        return av_frame

async def index(request):
    return web.FileResponse('templates/webrtc.html')

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])

    pc = RTCPeerConnection()
    pcs.add(pc)
    logging.info('Created PeerConnection %s', pc)

    # cleanup when connection state changes
    @pc.on('connectionstatechange')
    async def on_connectionstatechange():
        logging.info('Connection state is %s', pc.connectionState)
        if pc.connectionState in ('failed', 'closed'):
            await pc.close()
            pcs.discard(pc)

    # Add the camera track to the peer connection
    pc.addTrack(CameraVideoTrack(camera))

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type})

async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    # release camera
    camera.release()

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/', index), web.post('/offer', offer)])
    app.on_shutdown.append(on_shutdown)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        )
    })

    # Apply the CORS configuration to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    web.run_app(app, host='0.0.0.0', port=8081)
