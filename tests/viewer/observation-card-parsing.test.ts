// SPDX-License-Identifier: Apache-2.0
//
// The ErrorBoundary wraps <App/> at the root (src/ui/viewer/index.tsx), so an
// exception thrown while rendering one card does not degrade that card — it
// replaces the whole viewer with the "Something went wrong" screen. These
// columns hold JSON serialized into TEXT, and the viewer also renders rows that
// arrive from device sync, older schema versions, or manual DB edits, so a
// malformed or non-array value must not be able to take the UI down.

import { describe, expect, it, spyOn } from 'bun:test';
import { parseStringArray } from '../../src/ui/viewer/components/ObservationCard.js';

function quiet<T>(fn: () => T): T {
  const spy = spyOn(console, 'warn').mockImplementation(() => {});
  try {
    return fn();
  } finally {
    spy.mockRestore();
  }
}

describe('parseStringArray', () => {
  it('parses a well-formed JSON string array', () => {
    expect(parseStringArray('["a","b"]', 'facts')).toEqual(['a', 'b']);
  });

  it('treats empty, null and undefined as an empty list', () => {
    expect(parseStringArray('', 'facts')).toEqual([]);
    expect(parseStringArray(null, 'facts')).toEqual([]);
    expect(parseStringArray(undefined, 'facts')).toEqual([]);
  });

  it('returns [] instead of throwing on malformed JSON', () => {
    for (const bad of ['not json', '[1,2', '{"a":', '["unterminated]']) {
      expect(quiet(() => parseStringArray(bad, 'facts'))).toEqual([]);
    }
  });

  // Valid JSON that is not an array used to reach `.map(stripProjectRoot)` and
  // throw there, which is the same crash by a different route.
  it('returns [] for valid JSON that is not an array', () => {
    for (const notArray of ['"a string"', '42', 'null', 'true', '{"facts":["a"]}']) {
      expect(quiet(() => parseStringArray(notArray, 'files_read'))).toEqual([]);
    }
  });

  it('drops non-string elements rather than passing them to string helpers', () => {
    expect(quiet(() => parseStringArray('["a",1,null,{"x":1},"b"]', 'concepts'))).toEqual(['a', 'b']);
  });

  it('never throws for any of these inputs', () => {
    const inputs = ['', 'x', '[', '{}', '[[]]', '["ok"]', 'null', '[null]'];
    for (const i of inputs) {
      expect(() => quiet(() => parseStringArray(i, 'facts'))).not.toThrow();
    }
  });
});
