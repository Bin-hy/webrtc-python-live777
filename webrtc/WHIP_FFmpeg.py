import asyncio
import subprocess
import cv2
import numpy as np
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription


async def whip_publish_rtp(rtp_port=5002,
                           whip_url="http://huai-xhy.site:7777/whip/777",
                           camera_index=0,
                           width=640,
                           height=480,
                           fps=30):
    # 启动 FFmpeg 进程（从OpenCV获取帧）
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-vcodec", "libx264",
        "-profile:v", "baseline",
        "-preset", "ultrafast",  # 编码速度优先
        "-tune", "zerolatency",  # 零延迟优化
        "-pix_fmt", "yuv420p",
        "-b:v", "1500k",  # 目标码率 1.5Mbps
        "-maxrate", "2000k",  # 最大码率 2Mbps
        "-bufsize", "1000k",  # 缓冲区大小 1MB
        "-f", "rtp",
        f"rtp://127.0.0.1:{rtp_port}",
        "-sdp_file", "input.sdp"
    ]

    # 启动FFmpeg进程
    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE
    )

    # 初始化摄像头
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    # 启动帧推送线程
    async def capture_and_stream():
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    raise RuntimeError("摄像头读取失败")

                # 将帧写入FFmpeg的标准输入
                ffmpeg_process.stdin.write(frame.tobytes())
        except Exception as e:
            print(f"摄像头捕获错误: {e}")
        finally:
            cap.release()
            ffmpeg_process.stdin.close()

    # 启动摄像头捕获任务
    capture_task = asyncio.create_task(capture_and_stream())

    # 初始化 WebRTC 连接
    pc = RTCPeerConnection()

    try:
        # 添加视频接收器
        transceiver = pc.addTransceiver("video", direction="recvonly")

        # 生成并发送Offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        async with ClientSession() as session:
            async with session.post(
                    whip_url,
                    data=pc.localDescription.sdp,
                    headers={"Content-Type": "application/sdp"}
            ) as response:
                if response.status != 201:
                    raise RuntimeError(f"WHIP推流失败: HTTP {response.status}")
                answer_sdp = await response.text()

        # 处理Answer
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)

        # 保持运行
        print("推流已启动，按Ctrl+C停止...")
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"运行错误: {e}")
    finally:
        # 清理资源
        capture_task.cancel()
        ffmpeg_process.kill()
        await pc.close()
        print("资源已释放")


if __name__ == "__main__":
    asyncio.run(whip_publish_rtp(
        whip_url="http://localhost:7777/whip/777",
        camera_index=0,  # 摄像头设备索引
        width=640,  # 视频宽度
        height=480,  # 视频高度
        fps=30  # 帧率
    ))