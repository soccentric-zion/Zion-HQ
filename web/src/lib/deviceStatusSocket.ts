export interface DeviceStatusEvent {
  device_id: string
  online: boolean
  last_seen_at: string | null
}

/** Opens /ws/devices and calls `onEvent` for each push. Returns a closer.
 * Reconnects with backoff on drop -- the dev-server proxy in particular
 * closes the socket on every HMR reload. */
export function connectDeviceStatusSocket(onEvent: (e: DeviceStatusEvent) => void): () => void {
  let socket: WebSocket | null = null
  let closedByCaller = false
  let retryDelayMs = 1000

  function open() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${protocol}//${window.location.host}/api/ws/devices`)
    socket.onmessage = (event) => {
      try {
        onEvent(JSON.parse(event.data) as DeviceStatusEvent)
      } catch {
        // ignore malformed frames
      }
    }
    socket.onopen = () => {
      retryDelayMs = 1000
    }
    socket.onclose = () => {
      if (closedByCaller) return
      setTimeout(open, retryDelayMs)
      retryDelayMs = Math.min(retryDelayMs * 2, 15000)
    }
  }

  open()

  return () => {
    closedByCaller = true
    socket?.close()
  }
}
