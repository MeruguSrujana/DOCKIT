const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function authHeaders() {
  const token = localStorage.getItem("dockit_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;

    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}

    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return null;

  return res.json();
}

export const api = {

  // =========================================================
  // AUTH
  // =========================================================

  async login(username, password) {
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);

    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: form,
    });

    return handle(res);
  },

  async me() {
    const res = await fetch(`${BASE}/auth/me`, {
      headers: authHeaders(),
    });

    return handle(res);
  },

  // =========================================================
  // CASES
  // =========================================================

  async listCases() {
    const res = await fetch(`${BASE}/cases`, {
      headers: authHeaders(),
    });

    return handle(res);
  },

  async createCase(payload) {
    const res = await fetch(`${BASE}/cases`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    return handle(res);
  },

  async getCase(id) {
    const res = await fetch(`${BASE}/cases/${id}`, {
      headers: authHeaders(),
    });

    return handle(res);
  },

  // =========================================================
  // DOCUMENTS
  // =========================================================

  async listDocuments(caseId) {
    const res = await fetch(
      `${BASE}/documents/case/${caseId}`,
      {
        headers: authHeaders(),
      }
    );

    return handle(res);
  },

  async createDocument(payload) {
    const res = await fetch(`${BASE}/documents`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    return handle(res);
  },

  async getDocumentContent(docId, versionId) {
    const url = versionId
      ? `${BASE}/documents/${docId}/content?version_id=${versionId}`
      : `${BASE}/documents/${docId}/content`;
    const res = await fetch(url, { headers: authHeaders() });
    return handle(res);
  },

  async transitionDocument(docId, payload) {
    const res = await fetch(
      `${BASE}/documents/${docId}/transition`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify(payload),
      }
    );

    return handle(res);
  },

  async newVersion(docId, payload) {
    const res = await fetch(
      `${BASE}/documents/${docId}/versions`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify(payload),
      }
    );

    return handle(res);
  },

  async verifyVersion(docId, versionId) {
    const res = await fetch(
      `${BASE}/documents/${docId}/versions/${versionId}/verify`,
      {
        method: "POST",
        headers: authHeaders(),
      }
    );

    return handle(res);
  },

  // =========================================================
  // STANDARDIZED TEMPLATES
  // =========================================================

  async listTemplates() {
    const res = await fetch(
      `${BASE}/templates`,
      {
        headers: authHeaders(),
      }
    );

    return handle(res);
  },

  async getTemplate(templateId) {
    const res = await fetch(
      `${BASE}/templates/${templateId}`,
      {
        headers: authHeaders(),
      }
    );

    return handle(res);
  },

  // =========================================================
  // EVIDENCE
  // =========================================================

  async listEvidence(caseId) {
    const res = await fetch(
      `${BASE}/evidence/case/${caseId}`,
      {
        headers: authHeaders(),
      }
    );

    return handle(res);
  },

  async createEvidence(payload) {
    const res = await fetch(`${BASE}/evidence`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    return handle(res);
  },

  async transitionEvidence(evId, payload) {
    const res = await fetch(
      `${BASE}/evidence/${evId}/transition`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify(payload),
      }
    );

    return handle(res);
  },

  // =========================================================
  // TIMELINE
  // =========================================================

  async timeline(caseId, documentId) {
    const url = documentId
      ? `${BASE}/events/case/${caseId}?document_id=${documentId}`
      : `${BASE}/events/case/${caseId}`;

    const res = await fetch(url, {
      headers: authHeaders(),
    });

    return handle(res);
  },

  // =========================================================
  // READINESS
  // =========================================================

  async readiness(caseId) {
    const res = await fetch(
      `${BASE}/readiness/case/${caseId}`,
      {
        headers: authHeaders(),
      }
    );

    return handle(res);
  },

  // =========================================================
  // MOCK GOVERNMENT INTEGRATIONS
  // =========================================================

  async adapterCctnsReceive(caseId, documentId) {
    const res = await fetch(
      `${BASE}/adapters/mock-cctns/receive`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify({
          case_id: caseId,
          document_id: documentId,
        }),
      }
    );

    return handle(res);
  },

  async adapterEcourtsSend(caseId, documentId) {
    const res = await fetch(
      `${BASE}/adapters/mock-ecourts/send`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify({
          case_id: caseId,
          document_id: documentId,
        }),
      }
    );

    return handle(res);
  },

  // =========================================================
  // USERS (for owner / assignee pickers)
  // =========================================================

  async listUsers() {
    const res = await fetch(`${BASE}/users`, { headers: authHeaders() });
    return handle(res);
  },

  // =========================================================
  // CASE MANAGEMENT (owner / retention / disposal / active)
  // =========================================================

  async assignCaseOwner(caseId, ownerId) {
    const res = await fetch(`${BASE}/cases/${caseId}/owner`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ owner_id: ownerId }),
    });
    return handle(res);
  },

  async setCaseRetention(caseId, retentionDate) {
    const res = await fetch(`${BASE}/cases/${caseId}/retention`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ retention_date: retentionDate }),
    });
    return handle(res);
  },

  async disposeCase(caseId, disposalStatus, reason) {
    const res = await fetch(`${BASE}/cases/${caseId}/dispose`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ disposal_status: disposalStatus, reason }),
    });
    return handle(res);
  },

  async setCaseActiveStatus(caseId, isActive, reason) {
    const res = await fetch(`${BASE}/cases/${caseId}/active-status`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ is_active: isActive, reason }),
    });
    return handle(res);
  },

  // =========================================================
  // PARTIES (Initiate & Collect)
  // =========================================================

  async listCaseParties(caseId) {
    const res = await fetch(`${BASE}/parties/case/${caseId}`, { headers: authHeaders() });
    return handle(res);
  },

  async createParty(payload) {
    const res = await fetch(`${BASE}/parties`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  // =========================================================
  // NOTES (Initiate & Collect)
  // =========================================================

  async listCaseNotes(caseId) {
    const res = await fetch(`${BASE}/notes/case/${caseId}`, { headers: authHeaders() });
    return handle(res);
  },

  async createNote(payload) {
    const res = await fetch(`${BASE}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  // =========================================================
  // TASKS (Manage & Review)
  // =========================================================

  async listCaseTasks(caseId) {
    const res = await fetch(`${BASE}/tasks/case/${caseId}`, { headers: authHeaders() });
    return handle(res);
  },

  async listMyTasks() {
    const res = await fetch(`${BASE}/tasks/mine`, { headers: authHeaders() });
    return handle(res);
  },

  async createTask(payload) {
    const res = await fetch(`${BASE}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  async updateTask(taskId, payload) {
    const res = await fetch(`${BASE}/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  // =========================================================
  // COMMENTS (Manage & Review)
  // =========================================================

  async listCaseComments(caseId, documentId) {
    const url = documentId
      ? `${BASE}/comments/case/${caseId}?document_id=${documentId}`
      : `${BASE}/comments/case/${caseId}`;
    const res = await fetch(url, { headers: authHeaders() });
    return handle(res);
  },

  async createComment(payload) {
    const res = await fetch(`${BASE}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  // =========================================================
  // NOTIFICATIONS (Deliver & Execute)
  // =========================================================

  async listNotifications(unreadOnly = false) {
    const res = await fetch(`${BASE}/notifications?unread_only=${unreadOnly}`, {
      headers: authHeaders(),
    });
    return handle(res);
  },

  async markNotificationRead(notificationId) {
    const res = await fetch(`${BASE}/notifications/${notificationId}/read`, {
      method: "POST",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async markAllNotificationsRead() {
    const res = await fetch(`${BASE}/notifications/read-all`, {
      method: "POST",
      headers: authHeaders(),
    });
    return handle(res);
  },

  // =========================================================
  // SEARCH (Store & Archive)
  // =========================================================

  async search(query) {
    const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`, {
      headers: authHeaders(),
    });
    return handle(res);
  },

  // =========================================================
  // CASE ACCESS CONTROL (Admin-only: per-case collaborators, restriction)
  // =========================================================

  async listCollaborators(caseId) {
    const res = await fetch(`${BASE}/cases/${caseId}/collaborators`, { headers: authHeaders() });
    return handle(res);
  },

  async addCollaborator(caseId, userId, roleLabel) {
    const res = await fetch(`${BASE}/cases/${caseId}/collaborators`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ user_id: userId, role_label: roleLabel }),
    });
    return handle(res);
  },

  async removeCollaborator(caseId, collaboratorId) {
    const res = await fetch(`${BASE}/cases/${caseId}/collaborators/${collaboratorId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async setCaseRestricted(caseId, isRestricted) {
    const res = await fetch(`${BASE}/cases/${caseId}/restrict`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ is_restricted: isRestricted }),
    });
    return handle(res);
  },

  async getCaseFlow(caseId) {
    const res = await fetch(`${BASE}/cases/${caseId}/flow`, { headers: authHeaders() });
    return handle(res);
  },

  // =========================================================
  // ADMIN REVIEWS (content-blind approval gate)
  // =========================================================

  async listAdminReviews(statusFilter = "pending") {
    const res = await fetch(`${BASE}/admin-reviews?status_filter=${statusFilter}`, { headers: authHeaders() });
    return handle(res);
  },

  async decideAdminReview(reviewId, status, reason) {
    const res = await fetch(`${BASE}/admin-reviews/${reviewId}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status, reason }),
    });
    return handle(res);
  },

  // =========================================================
  // DISCLOSURES (the only path to defence access)
  // =========================================================

  async requestDisclosure(caseId, documentId, reason) {
    const res = await fetch(`${BASE}/disclosures`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ case_id: caseId, document_id: documentId, reason }),
    });
    return handle(res);
  },

  async listCaseDisclosures(caseId) {
    const res = await fetch(`${BASE}/disclosures/case/${caseId}`, { headers: authHeaders() });
    return handle(res);
  },

  async decideDisclosure(disclosureId, status, reason) {
    const res = await fetch(`${BASE}/disclosures/${disclosureId}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status, reason }),
    });
    return handle(res);
  },

  async listReleasedDocuments(caseId) {
    const res = await fetch(`${BASE}/disclosures/case/${caseId}/released`, { headers: authHeaders() });
    return handle(res);
  },

  // =========================================================
  // MATTERS (procedural / event-based classification)
  // =========================================================

  async listCaseMatters(caseId) {
    const res = await fetch(`${BASE}/matters/case/${caseId}`, { headers: authHeaders() });
    return handle(res);
  },

  async createMatter(payload) {
    const res = await fetch(`${BASE}/matters`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  async getMatterDocuments(matterId) {
    const res = await fetch(`${BASE}/matters/${matterId}/documents`, { headers: authHeaders() });
    return handle(res);
  },

  async getMatterEvidence(matterId) {
    const res = await fetch(`${BASE}/matters/${matterId}/evidence`, { headers: authHeaders() });
    return handle(res);
  },

  async assignDocumentMatter(documentId, matterId) {
    const res = await fetch(`${BASE}/matters/assign/document/${documentId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ matter_id: matterId }),
    });
    return handle(res);
  },

  async assignEvidenceMatter(evidenceId, matterId) {
    const res = await fetch(`${BASE}/matters/assign/evidence/${evidenceId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ matter_id: matterId }),
    });
    return handle(res);
  },

  // =========================================================
  // INBOX (documents transferred to me, awaiting acknowledgment)
  // =========================================================

  async listInbox() {
    const res = await fetch(`${BASE}/documents/inbox`, { headers: authHeaders() });
    return handle(res);
  },

  // =========================================================
  // DOCUMENT LOCK / OWNER-APPROVED ACCESS
  // =========================================================

  async getLockStatus(docId) {
    const res = await fetch(`${BASE}/documents/${docId}/lock-status`, { headers: authHeaders() });
    return handle(res);
  },

  async requestDocumentAccess(documentId, reason, requestedMode) {
    const res = await fetch(`${BASE}/document-access`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ document_id: documentId, reason, requested_mode: requestedMode || "view" }),
    });
    return handle(res);
  },

  async listAccessRequestsForDocument(documentId) {
    const res = await fetch(`${BASE}/document-access/document/${documentId}`, { headers: authHeaders() });
    return handle(res);
  },

  async listMyPendingOwnerRequests() {
    const res = await fetch(`${BASE}/document-access/mine/pending`, { headers: authHeaders() });
    return handle(res);
  },

  async decideDocumentAccess(requestId, status, reason, grantedMode, grantedDays) {
    const res = await fetch(`${BASE}/document-access/${requestId}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        status, reason,
        granted_mode: grantedMode || null,
        granted_days: grantedDays || null,
      }),
    });
    return handle(res);
  },

  async revokeDocumentAccess(requestId) {
    const res = await fetch(`${BASE}/document-access/${requestId}/revoke`, {
      method: "POST",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async listAuthorizedOfficers(documentId) {
    const res = await fetch(`${BASE}/document-access/document/${documentId}/authorized-officers`, {
      headers: authHeaders(),
    });
    return handle(res);
  },

  // =========================================================
  // JURISDICTION (District -> Mandal -> Police Station / Revenue Office)
  // =========================================================

  async listDistricts() {
    const res = await fetch(`${BASE}/jurisdiction/districts`, { headers: authHeaders() });
    return handle(res);
  },

  async listMandals(district) {
    const res = await fetch(`${BASE}/jurisdiction/mandals?district=${encodeURIComponent(district)}`, { headers: authHeaders() });
    return handle(res);
  },

  async listPoliceStations(district, mandal) {
    const res = await fetch(
      `${BASE}/jurisdiction/police-stations?district=${encodeURIComponent(district)}&mandal=${encodeURIComponent(mandal)}`,
      { headers: authHeaders() }
    );
    return handle(res);
  },

  async listRevenueOffices(district, mandal) {
    const res = await fetch(
      `${BASE}/jurisdiction/revenue-offices?district=${encodeURIComponent(district)}&mandal=${encodeURIComponent(mandal)}`,
      { headers: authHeaders() }
    );
    return handle(res);
  },

  // =========================================================
  // MATTERS — extra endpoints
  // =========================================================

  async getMatterWitnesses(matterId) {
    const res = await fetch(`${BASE}/matters/${matterId}/witnesses`, { headers: authHeaders() });
    return handle(res);
  },

  async setMatterStatus(matterId, status) {
    const res = await fetch(`${BASE}/matters/${matterId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status }),
    });
    return handle(res);
  },
};