import asyncio
import json
import websockets
from aiortc import VideoStreamTrack,RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from av import VideoFrame
import cv2

class OpenCVCaptureTrack(VideoStreamTrack):
    def __init__(self, cap):
        super().__init__()
        self.cap = cap

    async def recv(self):
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("无法读取帧")
        print(f"成功读取视频帧，尺寸：{frame.shape}")  # 添加日志
        return VideoFrame.from_ndarray(frame, format="bgr24")

async def run_webrtc():
    pc = RTCPeerConnection()
    # import cv2
    # gstreamer_str = "udpsrc address=230.1.1.1 port=1720 multicast-iface=eno0 ! application/x-rtp, media=video, encoding-name=H264 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! video/x-raw,width=1280,height=720,format=BGR ! appsink drop=1"
    # cap = cv2.VideoCapture(gstreamer_str, cv2.CAP_GSTREAMER)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    try:
        video_track = OpenCVCaptureTrack(cap)
        pc.addTrack(video_track)

        async with websockets.connect("ws://localhost:1111") as ws:
            print("已连接到信令服务器")
            await ws.send("python")

            # 生成并修复 SDP
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            await ws.send(json.dumps({"type": "offer", "sdp": pc.localDescription.sdp}))

            @pc.on("icecandidate")
            def on_ice_candidate(candidate):
                print("load candidate")
                if candidate:
                    print("发送端的 ICE Candidate:",candidate)
                ws.send(json.dumps({
                    "type": "candidate",
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex
                }))
            # 处理后续消息
            async for message in ws:
                data = json.loads(message)
                if data["type"] == "answer":
                    await pc.setRemoteDescription(RTCSessionDescription(sdp=data["sdp"], type="answer"))
                elif data["type"] == "candidate":
                    try:
                        ice_candidate = RTCIceCandidate(
                            candidate=data["candidate"],
                            sdpMid=data["sdpMid"],
                            sdpMLineIndex=data["sdpMLineIndex"],
                            port=data.get("port", 0),
                            priority=data.get("priority", 0),
                            protocol=data.get("protocol", "udp"),
                            type=data.get("type", "host")
                        )
                        await pc.addIceCandidate(ice_candidate)
                        print("已添加 ICE Candidate")
                    except Exception as e:
                        print(f"添加 ICE Candidate 失败: {e}")

    except Exception as e:
        print(f"连接异常: {e}")
    finally:
        await pc.close()
        cap.release()

if __name__ == "__main__":
    asyncio.run(run_webrtc())