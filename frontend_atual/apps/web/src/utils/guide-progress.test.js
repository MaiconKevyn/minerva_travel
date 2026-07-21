import assert from 'node:assert/strict';
import test from 'node:test';
import {
  builderSessionIdFromLocation,
  clearGuideProgressSnapshot,
  guideProgressStorageKey,
  readGuideProgressSnapshot,
  replaceBuilderSessionInLocation,
  selectNewestGuideProgress,
  writeGuideProgressSnapshot,
} from './guide-progress.js';

const memoryStorage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
};

test('guide progress snapshots are versioned and scoped to one authenticated owner', () => {
  const storage = memoryStorage();
  const payload = { current_step: 4, family_name: 'Silva' };
  writeGuideProgressSnapshot(storage, 'owner:a@example.com', payload, '2026-07-21T10:00:00Z');

  assert.deepEqual(readGuideProgressSnapshot(storage, 'owner:a@example.com')?.payload, payload);
  assert.equal(readGuideProgressSnapshot(storage, 'owner:b@example.com'), null);
  assert.notEqual(
    guideProgressStorageKey('owner:a@example.com'),
    guideProgressStorageKey('owner:b@example.com'),
  );

  clearGuideProgressSnapshot(storage, 'owner:a@example.com');
  assert.equal(readGuideProgressSnapshot(storage, 'owner:a@example.com'), null);
});

test('newest valid checkpoint wins and malformed local data is ignored', () => {
  const storage = memoryStorage();
  const ownerId = 'owner-1';
  storage.setItem(guideProgressStorageKey(ownerId), '{broken');
  assert.equal(readGuideProgressSnapshot(storage, ownerId), null);

  const draft = {
    updated_at: '2026-07-21T10:00:00Z',
    payload: { current_step: 3 },
  };
  const snapshot = writeGuideProgressSnapshot(
    storage,
    ownerId,
    { current_step: 7, builder_session_id: 'session123' },
    '2026-07-21T10:01:00Z',
  );
  assert.deepEqual(selectNewestGuideProgress({ draft, snapshot }), {
    source: 'local',
    payload: { current_step: 7, builder_session_id: 'session123' },
  });
  assert.equal(
    selectNewestGuideProgress({
      draft: { ...draft, updated_at: '2026-07-21T10:02:00Z' },
      snapshot,
    }).source,
    'server',
  );

  const futureLocal = writeGuideProgressSnapshot(
    storage,
    ownerId,
    { current_step: 6 },
    '2030-01-01T00:00:00Z',
    4,
  );
  assert.equal(selectNewestGuideProgress({
    draft: { revision: 5, updated_at: '2026-07-21T10:00:00Z', payload: { current_step: 7 } },
    snapshot: futureLocal,
  }).source, 'server');
  assert.equal(selectNewestGuideProgress({
    draft: { revision: 4, updated_at: '2026-07-21T10:00:00Z', payload: { current_step: 3 } },
    snapshot: futureLocal,
  }).source, 'local');
});

test('builder session URL is addressable and rejects unsafe identifiers', () => {
  let replacement = '';
  const history = {
    state: { preserved: true },
    replaceState: (_state, _title, url) => { replacement = url; },
  };
  const location = { href: 'https://minerva.test/create?from=profile#guide' };

  assert.equal(replaceBuilderSessionInLocation('session123', location, history), 'session123');
  assert.equal(replacement, '/create?from=profile&builder=session123#guide');
  assert.equal(
    builderSessionIdFromLocation({ href: `https://minerva.test${replacement}` }),
    'session123',
  );
  assert.equal(
    builderSessionIdFromLocation({ href: 'https://minerva.test/create?builder=../../secret' }),
    '',
  );
});
