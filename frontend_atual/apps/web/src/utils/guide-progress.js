export const GUIDE_PROGRESS_SCHEMA_VERSION = 1;

const STORAGE_PREFIX = 'minerva:guide-progress';
const BUILDER_QUERY_PARAMETER = 'builder';
const BUILDER_SESSION_ID_PATTERN = /^[A-Za-z0-9]{8,128}$/;

const normalizedOwnerId = (ownerId) => String(ownerId || '').trim();

export const normalizeBuilderSessionId = (sessionId) => {
  const normalized = String(sessionId || '').trim();
  return BUILDER_SESSION_ID_PATTERN.test(normalized) ? normalized : '';
};

export const guideProgressStorageKey = (ownerId) => {
  const normalized = normalizedOwnerId(ownerId);
  return normalized ? `${STORAGE_PREFIX}:${encodeURIComponent(normalized)}` : '';
};

const validTimestamp = (value) => {
  const timestamp = Date.parse(String(value || ''));
  return Number.isFinite(timestamp) ? timestamp : 0;
};

export const readGuideProgressSnapshot = (storage, ownerId) => {
  const key = guideProgressStorageKey(ownerId);
  if (!storage || !key) return null;

  try {
    const parsed = JSON.parse(storage.getItem(key) || 'null');
    if (
      !parsed
      || parsed.schema_version !== GUIDE_PROGRESS_SCHEMA_VERSION
      || parsed.owner_id !== normalizedOwnerId(ownerId)
      || !parsed.payload
      || typeof parsed.payload !== 'object'
      || Array.isArray(parsed.payload)
      || !validTimestamp(parsed.updated_at)
    ) return null;
    return parsed;
  } catch {
    return null;
  }
};

export const writeGuideProgressSnapshot = (
  storage,
  ownerId,
  payload,
  updatedAt = new Date().toISOString(),
  draftRevision = null,
) => {
  const key = guideProgressStorageKey(ownerId);
  if (!storage || !key || !payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return null;
  }
  const snapshot = {
    schema_version: GUIDE_PROGRESS_SCHEMA_VERSION,
    owner_id: normalizedOwnerId(ownerId),
    updated_at: updatedAt,
    draft_revision: Number.isInteger(draftRevision) ? draftRevision : null,
    payload,
  };
  storage.setItem(key, JSON.stringify(snapshot));
  return snapshot;
};

export const clearGuideProgressSnapshot = (storage, ownerId) => {
  const key = guideProgressStorageKey(ownerId);
  if (storage && key) storage.removeItem(key);
};

export const selectNewestGuideProgress = ({ draft = null, snapshot = null } = {}) => {
  const serverPayload = draft?.payload && typeof draft.payload === 'object'
    ? draft.payload
    : null;
  const localPayload = snapshot?.payload && typeof snapshot.payload === 'object'
    ? snapshot.payload
    : null;
  if (!serverPayload && !localPayload) return null;

  const serverUpdatedAt = validTimestamp(draft?.updated_at);
  const localUpdatedAt = validTimestamp(snapshot?.updated_at);
  const serverRevision = Number(draft?.revision);
  const localRevision = Number(snapshot?.draft_revision);
  if (JSON.stringify(serverPayload) === JSON.stringify(localPayload)) {
    return { source: 'server', payload: serverPayload };
  }
  if (Number.isInteger(serverRevision) && Number.isInteger(localRevision)) {
    if (serverRevision > localRevision) return { source: 'server', payload: serverPayload };
    if (serverRevision === localRevision) return { source: 'local', payload: localPayload };
  }
  if (localPayload && (!serverPayload || localUpdatedAt > serverUpdatedAt)) {
    return { source: 'local', payload: localPayload };
  }
  return { source: 'server', payload: serverPayload };
};

export const builderSessionIdFromLocation = (location = globalThis.location) => {
  try {
    const url = new URL(location.href);
    return normalizeBuilderSessionId(url.searchParams.get(BUILDER_QUERY_PARAMETER));
  } catch {
    return '';
  }
};

export const replaceBuilderSessionInLocation = (
  sessionId,
  location = globalThis.location,
  history = globalThis.history,
) => {
  try {
    const url = new URL(location.href);
    const normalized = normalizeBuilderSessionId(sessionId);
    if (normalized) url.searchParams.set(BUILDER_QUERY_PARAMETER, normalized);
    else url.searchParams.delete(BUILDER_QUERY_PARAMETER);
    history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
    return normalized;
  } catch {
    return '';
  }
};
