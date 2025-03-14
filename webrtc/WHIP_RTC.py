import cv2
import asyncio
import numpy as np
from av import VideoFrame
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, VideoStreamTrack ,RTCSessionDescription
from aiortc.rtcrtpparameters import RTCRtpCodecParameters

# 手动定义 H.264 编解码器参数（兼容 Live777）
H264_CODEC = RTCRtpCodecParameters(
    mimeType="video/H264",
    clockRate=90000,
    payloadType=99,
    parameters={
        "packetization-mode": 1,
        "profile-level-id": "42001f",
    },
)

class OpenCVCaptureTrack(VideoStreamTrack):
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.width = width
        self.height = height

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("摄像头读取失败")

        # BGR 转 YUV420P（H.264 编码需要）
        frame_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
        av_frame = VideoFrame.from_ndarray(frame_yuv, format="yuv420p")
        av_frame.pts = pts
        av_frame.time_base = time_base
        return av_frame

async def whip_publish(server_url="http://localhost:7777/whip/777"):
    pc = RTCPeerConnection()
    # 添加视频轨道并配置 H.264 编码器
    video_track = OpenCVCaptureTrack()
    video_transceiver = pc.addTransceiver(video_track, direction="sendonly")
    video_transceiver.sender.track
    # 强制使用 H.264 编解码器
    for codec in [H264_CODEC]:
        video_transceiver._sender._codecs.append(codec)  # 直接操作内部属性

    # 生成 SDP Offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    # 发送 Offer 到 WHIP 服务器
    async with ClientSession() as session:
        async with session.post(
            server_url,
            data=pc.localDescription.sdp,
            headers={"Content-Type": "application/sdp"}
        ) as response:
            if response.status != 201:
                raise RuntimeError(f"WHIP 推流失败: HTTP {response.status}")
            answer_sdp = await response.text()

    # 处理 SDP Answer
    answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
    await pc.setRemoteDescription(answer)

    # 保持推流
    print("推流已启动，按 Ctrl+C 停止...")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await pc.close()

if __name__ == "__main__":
    asyncio.run(whip_publish())