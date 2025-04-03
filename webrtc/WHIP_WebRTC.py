import asyncio
import random
import logging
import cv2
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole
from av import VideoFrame
import re
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WHIP_Publisher")


class CameraStreamTrack(VideoStreamTrack):
    """
    自定义视频流轨道，直接从摄像头获取帧
    """

    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        super().__init__()
        self.camera = cv2.VideoCapture(camera_index)
        if not self.camera.isOpened():
            raise RuntimeError(f"摄像头 {camera_index} 打开失败")

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.camera.set(cv2.CAP_PROP_FPS, fps)
        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.last_frame_time = 0
        logger.info("摄像头已就绪 (%dx%d @%dfps)", width, height, fps)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        # 控制帧率
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_frame_time
        if elapsed < self.frame_interval:
            await asyncio.sleep(self.frame_interval - elapsed)
        self.last_frame_time = now

        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError("无法从摄像头读取帧")

        # 转换颜色空间从BGR到RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base

        return av_frame

    def __del__(self):
        if self.camera.isOpened():
            self.camera.release()


async def whip_publish_webrtc(
        live777_base_url="http://huai-xhy.site:7777",
        live_stream_id=None,
        camera_index=0,
        width=640,
        height=480,
        fps=30
):
    pc = None
    session_id = None

    # 如果没有提供stream_id，生成一个随机ID
    if live_stream_id is None:
        live_stream_id = str(random.randint(100000000, 999999999))

    whip_url = f"{live777_base_url}/whip/{live_stream_id}"
    logger.info("WHIP URL: %s", whip_url)

    try:
        # 创建WebRTC连接
        pc = RTCPeerConnection()

        # 添加摄像头视频轨道
        video_track = CameraStreamTrack(camera_index, width, height, fps)
        pc.addTrack(video_track)

        # 创建offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # 发送WHIP请求
        async with ClientSession() as session:
            async with session.post(
                    whip_url,
                    data=pc.localDescription.sdp,
                    headers={"Content-Type": "application/sdp"}
            ) as response:
                if response.status != 201:
                    error_detail = await response.text()
                    logger.error("WHIP 失败: HTTP %d - %s", response.status, error_detail)
                    raise RuntimeError(f"WHIP 失败: HTTP {response.status}")

                # 处理响应
                location_header = response.headers.get('Location', '')
                logger.info("Location header: %s", location_header)

                # 解析session_id
                match = re.search(r'/session/([^/]+)/([^/]+)$', location_header)
                if match:
                    live_stream_id = match.group(1)
                    session_id = match.group(2)
                    logger.info("解析到 Stream ID: %s, Session ID: %s", live_stream_id, session_id)
                else:
                    logger.warning("无法从Location解析Session ID: %s", location_header)

                answer_sdp = await response.text()

        # 设置远程描述
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)

        logger.info("WebRTC推流成功！Stream ID: %s", live_stream_id)

        # 保持连接
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error("发生异常: %s", str(e), exc_info=True)
    finally:
        logger.info("开始清理资源...")

        # 关闭WebRTC连接
        if pc is not None:
            await pc.close()
            logger.info("WebRTC连接已关闭")

        # 发送DELETE请求通知服务器
        if session_id and live_stream_id:
            delete_url = f"{live777_base_url}/session/{live_stream_id}/{session_id}"
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

    # 使用随机stream_id启动推流
    # asyncio.run(whip_publish_webrtc(live777_base_url="http://localhost:7777"))
    asyncio.run(whip_publish_webrtc())

def run (live777Url:str = "http://huai-xhy.site:7777"): # 我的live777部署位置
    asyncio.run(whip_publish_webrtc(live777_base_url=live777Url))
