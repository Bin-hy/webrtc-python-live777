async  function connect(){
    let meidaData = await navigator.mediaDevices.getUserMedia({
        video:true,
        audio:true
    })
    const  stracks : MediaStreamTrack[] =meidaData.getTracks()
    const config ={}
    const pc = new RTCPeerConnection(config)


    const mysdp = await pc.createOffer()
    
    
    pc.setLocalDescription()
    // pc.setRemoteDescription()
    pc.onicecandidate = (event)=>{
        // 收集自己的 网络信息 局域网 公网 
        // 发送给 信令服务器
        
    }
    
}