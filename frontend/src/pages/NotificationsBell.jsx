import { useEffect, useState } from "react";
import { api } from "../api";

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  function load() {
    api.listNotifications().then(setItems).catch(() => {});
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const unreadCount = items.filter((n) => !n.is_read).length;

  async function markRead(n) {
    if (!n.is_read) {
      await api.markNotificationRead(n.id).catch(() => {});
      load();
    }
  }

  async function markAll() {
    await api.markAllNotificationsRead().catch(() => {});
    load();
  }

  return (
    <span style={{ position: "relative", marginLeft: 16 }}>
      <button className="link" onClick={() => setOpen((o) => !o)}>
        Notifications{unreadCount > 0 ? ` (${unreadCount})` : ""}
      </button>

      {open && (
        <div
          style={{
            position: "absolute", right: 0, top: "100%", marginTop: 8, width: 320,
            background: "white", color: "var(--black)", border: "1px solid #DDD",
            borderRadius: 6, boxShadow: "0 6px 18px rgba(0,0,0,0.15)", zIndex: 20,
            maxHeight: 360, overflowY: "auto",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", borderBottom: "1px solid #EEE" }}>
            <strong style={{ fontSize: 13 }}>Notifications</strong>
            {unreadCount > 0 && (
              <button className="btn secondary" style={{ padding: "4px 8px", fontSize: 11 }} onClick={markAll}>
                Mark all read
              </button>
            )}
          </div>
          {items.length === 0 && <div className="hint" style={{ padding: 14 }}>No notifications yet.</div>}
          {items.map((n) => (
            <div
              key={n.id}
              onClick={() => markRead(n)}
              style={{
                padding: "10px 12px", borderBottom: "1px solid #F2F2F2", cursor: "pointer",
                background: n.is_read ? "white" : "var(--accent-tint)", fontSize: 12.5,
              }}
            >
              <div>{n.message}</div>
              <div className="hint" style={{ marginTop: 4 }}>{new Date(n.created_at).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
