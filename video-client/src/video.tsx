import React, { useEffect, useRef, useState } from 'react';

interface RTCSessionDescriptionConfig extends RTCSessionDescriptionInit {
  type: RTCSdpType;
  sdp: string;
}

interface IceCandidateData {
  candidate: string;
  sdpMid: string | null;
  sdpMLineIndex: number | null;
  port?: number;
  priority?: number;
  protocol?: string;
  type?: 'host' | 'srflx' | 'relay' | 'prflx';
}

const WebRTCReceiver: React.FC = () => {
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const [showPlayButton, setShowPlayButton] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    // 初始化 WebSocket 连接
    const ws = new WebSocket('ws://localhost:1111');
    wsRef.current = ws;

    // 初始化 PeerConnection
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });
    pcRef.current = pc;

    // ICE Candidate 处理
    pc.onicecandidate = (event) => {
      console.log('ICE candidate:', event.candidate);
      if (event.candidate && ws.readyState === WebSocket.OPEN) {
        const candidateData: IceCandidateData = {
          candidate: event.candidate.candidate,
          sdpMid: event.candidate.sdpMid,
          sdpMLineIndex: event.candidate.sdpMLineIndex,
          port: event.candidate.port,
          priority: event.candidate.priority,
          protocol: event.candidate.protocol,
          type: event.candidate.type as IceCandidateData['type']
        };
        ws.send(JSON.stringify({ type: 'candidate', ...candidateData }));
      }
    };

    // Track 处理
    pc.ontrack = (event) => {
      console.log('Received track:', event.track.kind);
      if (remoteVideoRef.current && event.streams.length > 0) {
        remoteVideoRef.current.srcObject = event.streams[0];
        
        // 处理自动播放
        remoteVideoRef.current.play()
          .catch((error) => {
            console.warn('Autoplay failed:', error);
            setShowPlayButton(true);
          });
      }
    };

    // WebSocket 消息处理
    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'offer':
            await pc.setRemoteDescription(new RTCSessionDescription(data));
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            ws.send(JSON.stringify({
              type: 'answer',
              sdp: answer.sdp
            }));
            break;
            
          case 'candidate':
            await pc.addIceCandidate(new RTCIceCandidate(data));
            break;
        }
      } catch (error) {
        console.error('WebSocket message handling error:', error);
      }
    };

    // 初始化完成发送浏览器就绪通知
    ws.onopen = () => {
      ws.send('browser');
    };

    // Cleanup
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      pc.close();
    };
  }, []);

  const handleManualPlay = () => {
    if (remoteVideoRef.current) {
      remoteVideoRef.current.play()
        .then(() => setShowPlayButton(false))
        .catch(error => console.error('Manual play failed:', error));
    }
  };

  return (
    <div>
      <video
        ref={remoteVideoRef}
        autoPlay
        playsInline
        muted
        style={{
          width: '640px',
          height: '480px',
          backgroundColor: '#000'
        }}
      />
      {showPlayButton && (
        <button 
          onClick={handleManualPlay}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            margin: '20px'
          }}
        >
          点击开始播放
        </button>
      )}
    </div>
  );
};

export default WebRTCReceiver;