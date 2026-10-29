import { BASE_URL, getToken } from "./api.js";

// Live alerts without polling. The server pushes every new alert (Server-Sent Events).
// EventSource cannot send headers, so the login token goes in the URL (same idea as the video stream).
// Returns a function that closes the connection.
export function listenToAlerts(onAlert, onStatusChange) {
  const source = new EventSource(`${BASE_URL}/api/alerts/stream?token=${getToken()}`);

  source.onopen = () => onStatusChange && onStatusChange(true);
  source.onerror = () => onStatusChange && onStatusChange(false); // the browser reconnects by itself
  source.onmessage = (event) => {
    try {
      onAlert(JSON.parse(event.data));
    } catch (err) {
      console.log("bad alert message", err);
    }
  };

  return () => source.close();
}
