import asyncio
import random
import logging
from fractions import Fraction

import cv2
import os
import time
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCConfiguration, RTCSessionDescription, RTCIceServer
from av import VideoFrame
from aiortc.contrib.media import MediaBlackhole

# 禁用IPv6以避免潜在问题
os.environ['AIORTC_IPv6'] = '0'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WHIP_Publisher")


class CameraStreamTrack(VideoStreamTrack):
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        super().__init__()
        self.camera = cv2.VideoCapture(camera_index)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.camera.set(cv2.CAP_PROP_FPS, fps)
        self.frame_interval = 1.0 / fps
        self.last_frame_time = time.time()

    async def recv(self):
        # 控制帧率
        now = time.time()
        elapsed = now - self.last_frame_time
        if elapsed < self.frame_interval:
            await asyncio.sleep(self.frame_interval - elapsed)
        self.last_frame_time = now

        # 读取并转换帧
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError("摄像头读取失败")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
        av_frame = VideoFrame.from_ndarray(frame, format="yuv420p")

        av_frame.pts = int(now * 1000)  # 毫秒时间戳
        av_frame.time_base = Fraction(1, 1000)

        return av_frame

    def __del__(self):
        if self.camera.isOpened():
            self.camera.release()

async def whip_publish_webrtc(
        live777_base_url="http://huai-xhy.site:7777",
        live_stream_id=None,
):
    pc = None
    # 如果没有提供stream_id，生成一个随机ID
    if live_stream_id is None:
        live_stream_id = str(random.randint(100000000, 999999999))
    try:
        # 配置ICE服务器（STUN+TURN）
        pc = RTCPeerConnection(
            configuration=RTCConfiguration(
                iceServers=[
                    # # TURN服务器（需要认证）
                    RTCIceServer(
                        # urls= "stun:stun.l.google.com:19302"
                        urls="stun:159.75.120.92:3478",
                        username="myuser",
                        credential="mypassword"
                    )
                ]
            )
        )

        # 添加ICE状态监控
        @pc.on("iceconnectionstatechange")
        async def on_ice_change():
            state = pc.iceConnectionState
            logger.info(f"ICE状态变化: {state}")
            if state == "failed":
                logger.error("ICE连接失败!")

        # 添加候选收集监控
        @pc.on("icecandidate")
        def on_ice_candidate(candidate):
            if candidate:
                logger.debug(f"发现候选: {candidate.candidate}")

        # 添加视频轨道
        video_track = CameraStreamTrack()
        pc.addTrack(video_track)

        # 创建并设置offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # 发送WHIP请求
        whip_url = f"{live777_base_url}/whip/{live_stream_id}"
        async with ClientSession() as session:
            async with session.post(
                    whip_url,
                    data=pc.localDescription.sdp,
                    headers={"Content-Type": "application/sdp"}
            ) as response:
                if response.status != 201:
                    error = await response.text()
                    logger.error(f"WHIP请求失败: {response.status} - {error}")
                    raise RuntimeError(f"WHIP请求失败: {response.status}")

                # 处理响应
                location = response.headers.get('Location', '')
                logger.info(f"WHIP Location: {location}")

                answer_sdp = await response.text()
                answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
                await pc.setRemoteDescription(answer)

        logger.info("WebRTC连接已建立")

        # 保持连接
        while pc.iceConnectionState not in ["failed", "disconnected", "closed"]:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"发生错误: {str(e)}", exc_info=True)
    finally:
        logger.info("开始清理资源...")

        # 关闭WebRTC连接
        if pc is not None:
            await pc.close()
            logger.info("WebRTC连接已关闭")

        # 发送DELETE请求通知服务器
        if live_stream_id:
            delete_url = f"{live777_base_url}/api/streams/{live_stream_id}"
            logger.info("发送DELETE请求到: %s", delete_url)
            try:
                async with ClientSession() as session:
                    async with session.delete(delete_url) as resp:
                        if resp.status == 204:
                            logger.info("成功终止服务器端会话")
                        else:
                            logger.error("DELETE请求失败: HTTP %d", resp.status)
            except Exception as e:
                logger.error("发送DELETE请求时出错: %s", str(e))


if __name__ == "__main__":
    # 设置更详细的日志
    logging.basicConfig(level=logging.DEBUG)

    # 运行推流
    asyncio.run(whip_publish_webrtc())

async def connect_push():
    asyncio.run(whip_publish_webrtc())