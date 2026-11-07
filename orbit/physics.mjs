/** ORBIT-01: lightweight screen-space interaction model.
 * Intentionally NOT a physical collision solver or 3D depth estimator.
 */

export const DEFAULT_PHYSICS = Object.freeze({ drop: 0, speed: 0, tilt: 0, spin: 0 });

export function createPhysics() {
  return { ...DEFAULT_PHYSICS };
}

export function impact(physics, intensity = 1) {
  const power = Math.max(0.1, Math.min(2.0, Number(intensity) || 1));
  physics.speed -= power * 5.4;
  physics.spin += power * 1.3;
  return physics;
}

export function advance(physics, seconds) {
  const dt = Math.min(0.05, Math.max(0, seconds));
  physics.speed += (-24 * physics.drop - 8 * physics.speed) * dt;
  physics.drop += physics.speed * dt;
  physics.spin += (-15 * physics.tilt - 7 * physics.spin) * dt;
  physics.tilt += physics.spin * dt;
  if (Math.abs(physics.drop) < 0.0001 && Math.abs(physics.speed) < 0.0001) {
    physics.drop = 0;
    physics.speed = 0;
  }
  return physics;
}

export function boundsForObject(centerX, centerY, widthNorm, heightNorm) {
  return {
    left: centerX - widthNorm / 2,
    right: centerX + widthNorm / 2,
    top: centerY - heightNorm / 2,
    bottom: centerY + heightNorm / 2,
  };
}

/** Returns foot coordinates in normalized video-space, if visible. */
export function footPositions(landmarks) {
  if (!Array.isArray(landmarks)) return [];
  return [31, 32, 27, 28]
    .map(index => landmarks[index])
    .filter(point => point && Number.isFinite(point.x) && Number.isFinite(point.y)
      && (point.visibility === undefined || point.visibility >= 0.35));
}

/** Approximate descending foot contact with the upper portion of the text.
 * Requires prior foot points; intentionally errs on the side of no contact.
 */
export function hasFootContact(current, previous, bounds, deltaSeconds) {
  if (!Array.isArray(current) || !Array.isArray(previous) || deltaSeconds <= 0) return false;
  const indices = [31, 32, 27, 28];
  return indices.some(index => {
    const foot = current[index];
    const before = previous[index];
    if (!foot || !before || (foot.visibility ?? 1) < 0.35) return false;
    const vx = foot.x;
    const descendingSpeed = (foot.y - before.y) / deltaSeconds;
    const horizontal = vx >= bounds.left - 0.035 && vx <= bounds.right + 0.035;
    const nearSurface = foot.y >= bounds.top - 0.075 && foot.y <= bounds.top + 0.09;
    return horizontal && nearSurface && descendingSpeed > 0.10;
  });
}
