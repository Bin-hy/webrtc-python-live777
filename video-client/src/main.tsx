import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import VideoView from  './video.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <VideoView />
  </StrictMode>,
)
