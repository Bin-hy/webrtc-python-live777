import { useState } from 'react';
import "./app.css"
import "../../vrcomponents"

// const live777_base_url = "http://huai-xhy.site:7777/"
// const whepAddress = {
//   whep: true,
//   address: live777_base_url + "whep/home"
// };

interface StreamInfo {
  id: string;
  createdAt: number;
}

function App() {
  // const [mode, setMode] = useState('whep')
  const [whepAddressBase, setLive777BaseUrl] = useState('http://localhost:7777')
  const [roomId, setRoomId] = useState("ar");
  const [availableStreams, setAvailableStreams] = useState<StreamInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAvailableStreams = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${whepAddressBase}/api/streams/`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const streams = data.map((stream: any) => ({
        id: stream.id,
        createdAt: stream.createdAt
      }));
      setAvailableStreams(streams);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch streams');
      console.error("Error fetching streams:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  };

  return (
    <>
      <h1>计算机网络VR在线观看</h1>
      <table>
        <tbody>
          <tr>
            <th>Connection Mode</th>
            {/* <td>
              <select onChange={(e) => setMode(e.target.value)}>
                <option value={'whep'}>WHEP</option>
              </select>
            </td> */}
            <td>
              <input 
                value={whepAddressBase}
                onChange={(e) => setLive777BaseUrl(e.target.value.trim())} 
                placeholder="live777服务器网站" 
              />
              <input 
                value={roomId}
                onChange={(e) => setRoomId(e.target.value.trim())} 
                placeholder="房间号" 
              />
              {/* <button onClick={fetchAvailableStreams} disabled={isLoading}>
                {isLoading ? '加载中...' : '获取可用房间'}
              </button> */}
              <button 
                onClick={fetchAvailableStreams} 
                disabled={isLoading}
                className="fetch-button"
              >
                获取可用房间
            </button>
            </td>
          </tr>
        </tbody>
      </table>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {availableStreams.length > 0 && (
        <div className="streams-container">
          <h3>可用房间列表</h3>
          <div className="streams-header">
            <div className="stream-id">房间ID</div>
            <div className="stream-created">创建时间</div>
          </div>
          {availableStreams.map(stream => (
            <div 
              key={stream.id} 
              className={`stream-item ${roomId === stream.id ? 'active' : ''}`}
              onClick={() => setRoomId(stream.id)}
            >
              <div className="stream-id">{stream.id}</div>
              <div className="stream-created">{formatDate(stream.createdAt)}</div>
            </div>
          ))}
        </div>
      )}

      <vr-rtc {
        ...{
          whep: true,
          address: whepAddressBase + "/whep/" + roomId
        }
      } style={{ width: "1920px" }}></vr-rtc>

    </>
  )
}

export default App
