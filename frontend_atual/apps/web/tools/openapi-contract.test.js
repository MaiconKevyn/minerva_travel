import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import {
  FAMILY_PHOTO_MAX_BYTES,
  FAMILY_PHOTO_MAX_HEIGHT,
  FAMILY_PHOTO_MAX_PIXELS,
  FAMILY_PHOTO_MAX_WIDTH,
  MAX_GUIDE_CHILDREN,
  MAX_GUIDE_DESTINATIONS,
  MAX_GUIDE_LANDMARKS,
  MAX_GUIDE_PARENTS,
  MAX_GUIDE_YEAR,
  MAX_VISIBLE_FAMILY_MEMBERS,
  MIN_GUIDE_YEAR,
} from '../src/utils/guide-form.js';

const projectRoot = dirname(fileURLToPath(new URL('../package.json', import.meta.url)));
const contract = JSON.parse(
  readFileSync(join(projectRoot, 'src/contracts/minerva-openapi.json'), 'utf8'),
);
const apiSource = readFileSync(join(projectRoot, 'src/utils/minerva-api.js'), 'utf8');

const operationSchema = (path, method, status = '200') => {
  const operation = contract.paths?.[path]?.[method.toLowerCase()];
  assert.ok(operation, `OpenAPI operation missing: ${method.toUpperCase()} ${path}`);
  const schema = operation.responses?.[status]?.content?.['application/json']?.schema;
  assert.ok(schema, `JSON response schema missing: ${method.toUpperCase()} ${path} ${status}`);
  return schema;
};

const dereference = (schema) => {
  const reference = schema?.$ref;
  if (!reference) return schema;
  const name = reference.split('/').at(-1);
  const component = contract.components?.schemas?.[name];
  assert.ok(component, `OpenAPI component missing: ${name}`);
  return component;
};

const assertRequiredFields = (path, method, fields, status = '200') => {
  const schema = dereference(operationSchema(path, method, status));
  const available = new Set([
    ...Object.keys(schema.properties || {}),
    ...(schema.required || []),
  ]);
  fields.forEach((field) => assert.ok(
    available.has(field),
    `${method.toUpperCase()} ${path} no longer exposes frontend field: ${field}`,
  ));
};

test('frontend API operations and consumed response fields match the backend OpenAPI snapshot', () => {
  const contracts = [
    ['/api/catalog', 'get', ['id', 'title', 'destinations']],
    ['/api/itinerary/recommend', 'post', ['summary', 'selected_landmarks', 'days', 'alternatives']],
    ['/api/itinerary/discover', 'post', ['summary', 'selected_landmarks', 'days', 'alternatives', 'resolved_destination']],
    ['/api/itinerary/routes/suggest', 'post', ['options']],
    ['/api/landmarks/resolve-structured', 'post', ['custom_landmarks', 'selected_landmarks', 'destinations']],
    ['/api/landmarks/parse', 'post', ['custom_landmarks', 'selected_landmarks', 'destinations']],
    ['/api/guides', 'get', ['guides']],
    ['/api/guides/{guide_id}', 'get', ['id', 'title', 'status', 'download_url']],
    ['/api/guides/{guide_id}', 'delete', ['deleted']],
    ['/api/drafts/current', 'get', ['draft'], '200', '/current'],
    ['/api/drafts', 'post', ['id', 'payload', 'revision'], '201'],
    ['/api/drafts/{draft_id}', 'put', ['id', 'payload', 'revision']],
    ['/api/drafts/{draft_id}', 'delete', ['deleted']],
    ['/api/jobs/{job_id}', 'get', ['id', 'status', 'stage', 'progress', 'result', 'error']],
  ];

  contracts.forEach(([path, method, fields, status, explicitSourceToken]) => {
    assertRequiredFields(path, method, fields, status);
    const sourceToken = explicitSourceToken
      || path.replace(/\{[^}]+\}/g, '').replace(/\/$/, '');
    assert.ok(apiSource.includes(sourceToken), `Frontend client no longer calls ${path}`);
  });

  const generation = operationSchema('/api/generate', 'post');
  const variants = (generation.anyOf || []).map(dereference);
  assert.equal(variants.length, 2);
  assert.deepEqual(
    new Set(variants.flatMap((variant) => Object.keys(variant.properties || {}))),
    new Set([
      'request_id',
      'download_url',
      'filename',
      'cover_status',
      'job_id',
      'status',
      'stage',
      'progress',
      'poll_url',
    ]),
  );
  assert.ok(apiSource.includes('/api/generate'));
});

test('shared API errors retain the fields used by frontend feedback', () => {
  const error = contract.components.schemas.ApiErrorResponse;
  assert.deepEqual(
    new Set(error.required),
    new Set(['code', 'message', 'field_errors', 'request_id']),
  );
  assert.ok(error.properties.detail);
});

test('frontend product limits match the backend contract source', () => {
  const limits = contract['x-minerva-contract-limits'];
  assert.deepEqual(limits, {
    image_upload_max_bytes: FAMILY_PHOTO_MAX_BYTES,
    image_upload_max_height: FAMILY_PHOTO_MAX_HEIGHT,
    image_upload_max_pixels: FAMILY_PHOTO_MAX_PIXELS,
    image_upload_max_width: FAMILY_PHOTO_MAX_WIDTH,
    max_guide_children: MAX_GUIDE_CHILDREN,
    max_guide_destinations: MAX_GUIDE_DESTINATIONS,
    max_guide_landmarks: MAX_GUIDE_LANDMARKS,
    max_guide_parents: MAX_GUIDE_PARENTS,
    max_guide_year: MAX_GUIDE_YEAR,
    max_visible_family_members: MAX_VISIBLE_FAMILY_MEMBERS,
    min_guide_year: MIN_GUIDE_YEAR,
  });
});
