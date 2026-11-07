import test from "node:test";
import assert from "node:assert/strict";
import { createPhysics, impact, advance, boundsForObject, hasFootContact, footPositions } from "../physics.mjs";

function poseWithFoot(index, x, y) {
  const pose = new Array(33).fill(null);
  pose[index] = { x, y, visibility: 1 };
  return pose;
}

test("an impact moves the letters down", () => {
  const state = createPhysics();
  impact(state, 1);
  advance(state, 0.016);
  assert.ok(state.drop < 0);
  assert.ok(state.tilt > 0);
});

test("spring returns near equilibrium", () => {
  const state = createPhysics();
  impact(state, 1);
  for (let i = 0; i < 500; i++) advance(state, 0.016);
  assert.ok(Math.abs(state.drop) < 0.001);
  assert.ok(Math.abs(state.speed) < 0.001);
});

test("object bounds are centered correctly", () => {
  assert.deepEqual(boundsForObject(0.5, 0.5, 0.4, 0.2), {
    left: 0.3, right: 0.7, top: 0.4, bottom: 0.6
  });
});

test("descending foot can trigger visual impact", () => {
  const previous = poseWithFoot(31, 0.5, 0.2);
  const current = poseWithFoot(31, 0.5, 0.29);
  assert.equal(hasFootContact(current, previous, boundsForObject(0.5, 0.45, 0.8, 0.4), 0.1), true);
});

test("foot outside letters does not trigger contact", () => {
  assert.equal(hasFootContact(
    poseWithFoot(31, 0.95, 0.29),
    poseWithFoot(31, 0.95, 0.20),
    boundsForObject(0.5, 0.45, 0.4, 0.4),
    0.1
  ), false);
});

test("stationary foot is not an impact", () => {
  const a = poseWithFoot(31, 0.5, 0.29);
  assert.equal(hasFootContact(a, a, boundsForObject(0.5, 0.45, 0.8, 0.4), 0.1), false);
});

test("low-visibility feet do not count", () => {
  const a = poseWithFoot(31, 0.5, 0.29);
  const b = poseWithFoot(31, 0.5, 0.20);
  a[31].visibility = 0.05;
  assert.equal(hasFootContact(a, b, boundsForObject(0.5, 0.45, 0.8, 0.4), 0.1), false);
  assert.equal(footPositions(a).length, 0);
});
