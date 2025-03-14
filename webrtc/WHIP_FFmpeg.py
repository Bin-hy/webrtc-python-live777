import asyncio
import subprocess
from aiohttp import ClientSession
from aiortc import RTCPeerConnection ,RTCSessionDescription

async def whip_publish_rtp(rtp_port=5002, whip_url="http://localhost:7777/whip/777"):
    # 启动 FFmpeg 生成 RTP 流
    ffmpeg_cmd = [
        "ffmpeg",
        "-re",
        "-f", "lavfi",
        "-i", "testsrc=size=640x480:rate=30",
        "-vcodec", "libx264",
        "-x264-params", "level-asymmetry-allowed=1:packetization-mode=1:profile-level-id=42001f",
        "-f", "rtp",
        f"rtp://127.0.0.1:{rtp_port}",
        "-sdp_file", "input.sdp"
    ]
    ffmpeg_process = subprocess.Popen(ffmpeg_cmd)

    # 初始化 WebRTC 连接
    pc = RTCPeerConnection()

    # 添加视频接收器（方向为 recvonly）
    transceiver = pc.addTransceiver("video", direction="recvonly")

    # 生成 SDP Offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    # 发送 Offer 到 WHIP 服务器
    async with ClientSession() as session:
        async with session.post(
            whip_url,
            data=pc.localDescription.sdp,
            headers={"Content-Type": "application/sdp"}
        ) as response:
            if response.status != 201:
                ffmpeg_process.kill()
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
        ffmpeg_process.kill()
        await pc.close()

if __name__ == "__main__":
    asyncio.run(whip_publish_rtp())