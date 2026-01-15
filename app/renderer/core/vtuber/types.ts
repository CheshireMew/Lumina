/**
 * Face Tracking Data Structure
 * Maps MediaPipe landmarks to avatar-friendly BlendShapes
 */
export interface FaceTrackingData {
  // Eye BlendShapes (0-1)
  eyeBlinkLeft: number;
  eyeBlinkRight: number;
  eyeWideLeft: number;
  eyeWideRight: number;

  // Mouth BlendShapes (0-1)
  mouthOpen: number; // Jaw open
  mouthSmileLeft: number;
  mouthSmileRight: number;
  mouthFrownLeft: number;
  mouthFrownRight: number;

  // Eyebrow BlendShapes (0-1)
  browDownLeft: number;
  browDownRight: number;
  browUpLeft: number;
  browUpRight: number;

  // Head Rotation (radians)
  headRotationX: number; // Pitch (nod)
  headRotationY: number; // Yaw (shake)
  headRotationZ: number; // Roll (tilt)
}

/**
 * Default/neutral face data
 */
export const DEFAULT_FACE_DATA: FaceTrackingData = {
  eyeBlinkLeft: 0,
  eyeBlinkRight: 0,
  eyeWideLeft: 0,
  eyeWideRight: 0,
  mouthOpen: 0,
  mouthSmileLeft: 0,
  mouthSmileRight: 0,
  mouthFrownLeft: 0,
  mouthFrownRight: 0,
  browDownLeft: 0,
  browDownRight: 0,
  browUpLeft: 0,
  browUpRight: 0,
  headRotationX: 0,
  headRotationY: 0,
  headRotationZ: 0,
};
