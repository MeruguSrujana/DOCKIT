import { useEffect, useState } from "react";
import { api } from "../api";

const TASK_NEXT_ACTIONS = {
  pending: [["in_progress", "Start"], ["cancelled", "Cancel"]],
  in_progress: [["done", "Mark Done"], ["cancelled", "Cancel"]],
  done: [],
  cancelled: [],
};

export default function TasksTab({ caseId }) {
  const [tasks, setTasks] = useState([]);
  const [comments, setComments] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);

  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: "", description: "", assigned_to_id: "", due_date: "" });

  const [commentText, setCommentText] = useState("");

  function load() {
    api.listCaseTasks(caseId).then(setTasks).catch((e) => setError(e.message));
    api.listCaseComments(caseId).then(setComments).catch((e) => setError(e.message));
    api.listUsers().then(setUsers).catch(() => {});
  }
  useEffect(load, [caseId]);

  async function addTask(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createTask({
        case_id: caseId,
        title: taskForm.title,
        description: taskForm.description || null,
        assigned_to_id: taskForm.assigned_to_id || null,
        due_date: taskForm.due_date ? new Date(taskForm.due_date).toISOString() : null,
      });
      setTaskForm({ title: "", description: "", assigned_to_id: "", due_date: "" });
      setShowTaskForm(false);
      load();
    } catch (err) { setError(err.message); }
  }

  async function setStatus(task, status) {
    setError(null);
    try {
      await api.updateTask(task.id, { status });
      load();
    } catch (err) { setError(err.message); }
  }

  async function addComment(e) {
    e.preventDefault();
    if (!commentText.trim()) return;
    setError(null);
    try {
      await api.createComment({ case_id: caseId, content: commentText });
      setCommentText("");
      load();
    } catch (err) { setError(err.message); }
  }

  function userName(id) {
    return users.find((u) => u.id === id)?.full_name || "—";
  }

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Tasks</h3>
        <button className="btn" onClick={() => setShowTaskForm((s) => !s)}>
          {showTaskForm ? "Cancel" : "+ New Task"}
        </button>
      </div>

      {showTaskForm && (
        <div className="card">
          <form onSubmit={addTask}>
            <label>Title</label>
            <input value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} required />
            <label>Description</label>
            <input value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} placeholder="Optional" />
            <label>Assign To</label>
            <select value={taskForm.assigned_to_id} onChange={(e) => setTaskForm({ ...taskForm, assigned_to_id: e.target.value })}>
              <option value="">— unassigned —</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.role.replaceAll("_", " ")})</option>)}
            </select>
            <label>Due Date</label>
            <input type="date" value={taskForm.due_date} onChange={(e) => setTaskForm({ ...taskForm, due_date: e.target.value })} />
            <button className="btn">Create Task</button>
          </form>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Task</th><th>Assigned To</th><th>Due</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>
                  <strong>{t.title}</strong>
                  {t.description && <div className="hint">{t.description}</div>}
                </td>
                <td>{userName(t.assigned_to_id)}</td>
                <td>{t.due_date ? new Date(t.due_date).toLocaleDateString() : "—"}</td>
                <td><span className="badge">{t.status.replaceAll("_", " ")}</span></td>
                <td>
                  {(TASK_NEXT_ACTIONS[t.status] || []).map(([action, label]) => (
                    <button key={action} className="btn secondary" style={{ marginRight: 6 }}
                            onClick={() => setStatus(t, action)}>{label}</button>
                  ))}
                </td>
              </tr>
            ))}
            {tasks.length === 0 && <tr><td colSpan={5} className="hint" style={{ padding: 14 }}>No tasks yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginTop: 28 }}>Discussion</h3>

      <div className="card">
        <form onSubmit={addComment}>
          <textarea rows={2} value={commentText} onChange={(e) => setCommentText(e.target.value)} placeholder="Add a comment for the team..." required />
          <button className="btn" style={{ marginTop: 8 }}>Post Comment</button>
        </form>
      </div>

      {comments.map((c) => (
        <div key={c.id} className="card" style={{ marginBottom: 10 }}>
          <div>{c.content}</div>
          <div className="hint" style={{ marginTop: 8 }}>
            {c.author_name} · {new Date(c.created_at).toLocaleString()}
          </div>
        </div>
      ))}
      {comments.length === 0 && <div className="hint">No comments yet.</div>}
    </div>
  );
}
