import asyncio
import random
import logging
import cv2
import os
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCConfiguration, RTCSessionDescription
from av import VideoFrame

# 禁用IPv6以避免潜在问题
os.environ['AIORTC_IPv6'] = '0'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WHIP_Publisher")


class CameraStreamTrack(VideoStreamTrack):
    """自定义视频流轨道，直接从摄像头获取帧"""

    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        super().__init__()
        self.camera = cv2.VideoCapture(camera_index)
        if not self.camera.isOpened():
            raise RuntimeError(f"摄像头 {camera_index} 打开失败")

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.camera.set(cv2.CAP_PROP_FPS, fps)
        logger.info("摄像头已就绪 (%dx%d @%dfps)", width, height, fps)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError("无法从摄像头读取帧")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return VideoFrame.from_ndarray(frame, format="rgb24")


async def whip_publish_webrtc():
    try:
        # 正确配置iceServers的格式
        pc = RTCPeerConnection(
            configuration=RTCConfiguration(
                iceServers=[
                    {"urls": "stun:159.75.120.92:3478",
                     "username":"myuser",
                     "credential":"mypassword"
                     },
                ]
            )
        )

        # 添加ICE状态监控
        @pc.on("iceconnectionstatechange")
        async def on_ice_change():
            state = pc.iceConnectionState
            logger.info(f"ICE状态变化: {state}")
            if state == "failed":
                logger.warning("ICE连接失败!")

        # 添加视频轨道
        video_track = CameraStreamTrack()
        pc.addTrack(video_track)

        # 创建并设置offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # 发送WHIP请求
        whip_url = "http://huai-xhy.site:7777/whip/123456789"
        async with ClientSession() as session:
            async with session.post(
                    whip_url,
                    data=pc.localDescription.sdp,
                    headers={"Content-Type": "application/sdp"}
            ) as response:
                if response.status != 201:
                    raise RuntimeError(f"WHIP请求失败: {response.status}")

                answer_sdp = await response.text()
                answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
                await pc.setRemoteDescription(answer)

        # 保持连接
        while pc.iceConnectionState != "failed":
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"发生错误: {str(e)}", exc_info=True)
    finally:
        if pc:
            await pc.close()


if __name__ == "__main__":
    # 设置更详细的日志
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(whip_publish_webrtc())