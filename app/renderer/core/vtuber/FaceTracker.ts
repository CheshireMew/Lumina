import { FaceTrackingData, DEFAULT_FACE_DATA } from "./types";

// MediaPipe Landmark indices for key facial features
const LANDMARK = {
  // Left eye
  LEFT_EYE_TOP: 159,
  LEFT_EYE_BOTTOM: 145,
  LEFT_EYE_LEFT: 33,
  LEFT_EYE_RIGHT: 133,

  // Right eye
  RIGHT_EYE_TOP: 386,
  RIGHT_EYE_BOTTOM: 374,
  RIGHT_EYE_LEFT: 362,
  RIGHT_EYE_RIGHT: 263,

  // Mouth
  MOUTH_TOP: 13,
  MOUTH_BOTTOM: 14,
  MOUTH_LEFT: 61,
  MOUTH_RIGHT: 291,

  // Nose (for head rotation reference)
  NOSE_TIP: 1,

  // Face outline for head rotation
  FACE_LEFT: 234,
  FACE_RIGHT: 454,
  FACE_TOP: 10,
  FACE_BOTTOM: 152,
};

/**
 * FaceTracker Service
 * Uses MediaPipe Face Mesh to track facial expressions
 */
export class FaceTracker {
  private faceMesh: any = null;
  private camera: any = null;
  private videoElement: HTMLVideoElement | null = null;
  private isRunning: boolean = false;
  private onDataCallback: ((data: FaceTrackingData) => void) | null = null;

  /**
   * Start face tracking
   * @param onData Callback for each frame's face data
   */
  async start(onData: (data: FaceTrackingData) => void): Promise<void> {
    if (this.isRunning) return;

    this.onDataCallback = onData;

    // Dynamically import MediaPipe (Lazy Loading)
    const { FaceMesh } = await import("@mediapipe/face_mesh");
    const { Camera } = await import("@mediapipe/camera_utils");

    // Create video element for camera feed
    this.videoElement = document.createElement("video");
    this.videoElement.style.display = "none"; // Hidden, just for processing
    document.body.appendChild(this.videoElement);

    // Initialize FaceMesh
    this.faceMesh = new FaceMesh({
      locateFile: (file: string) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
      },
    });

    this.faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true, // More accurate eye/lip tracking
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    this.faceMesh.onResults((results: any) => {
      if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
        const landmarks = results.multiFaceLandmarks[0];
        const faceData = this.processLandmarks(landmarks);
        this.onDataCallback?.(faceData);
      }
    });

    // Start camera
    this.camera = new Camera(this.videoElement, {
      onFrame: async () => {
        if (this.faceMesh && this.videoElement) {
          await this.faceMesh.send({ image: this.videoElement });
        }
      },
      width: 640,
      height: 480,
    });

    await this.camera.start();
    this.isRunning = true;
    console.log("[FaceTracker] Started");
  }

  /**
   * Stop face tracking
   */
  stop(): void {
    if (this.camera) {
      this.camera.stop();
      this.camera = null;
    }
    if (this.videoElement) {
      this.videoElement.remove();
      this.videoElement = null;
    }
    this.faceMesh = null;
    this.isRunning = false;
    this.onDataCallback = null;
    console.log("[FaceTracker] Stopped");
  }

  /**
   * Convert MediaPipe landmarks to BlendShape values
   */
  private processLandmarks(landmarks: any[]): FaceTrackingData {
    const data = { ...DEFAULT_FACE_DATA };

    // Helper: Calculate distance between two landmarks
    const dist = (a: number, b: number) => {
      const p1 = landmarks[a];
      const p2 = landmarks[b];
      return Math.sqrt(
        Math.pow(p1.x - p2.x, 2) +
          Math.pow(p1.y - p2.y, 2) +
          Math.pow(p1.z - p2.z, 2)
      );
    };

    // Eye Blink Detection
    const leftEyeHeight = dist(LANDMARK.LEFT_EYE_TOP, LANDMARK.LEFT_EYE_BOTTOM);
    const leftEyeWidth = dist(LANDMARK.LEFT_EYE_LEFT, LANDMARK.LEFT_EYE_RIGHT);
    const leftEyeRatio = leftEyeHeight / leftEyeWidth;
    data.eyeBlinkLeft = Math.max(0, Math.min(1, 1 - leftEyeRatio / 0.25));

    const rightEyeHeight = dist(
      LANDMARK.RIGHT_EYE_TOP,
      LANDMARK.RIGHT_EYE_BOTTOM
    );
    const rightEyeWidth = dist(
      LANDMARK.RIGHT_EYE_LEFT,
      LANDMARK.RIGHT_EYE_RIGHT
    );
    const rightEyeRatio = rightEyeHeight / rightEyeWidth;
    data.eyeBlinkRight = Math.max(0, Math.min(1, 1 - rightEyeRatio / 0.25));

    // Mouth Open Detection
    const mouthHeight = dist(LANDMARK.MOUTH_TOP, LANDMARK.MOUTH_BOTTOM);
    const mouthWidth = dist(LANDMARK.MOUTH_LEFT, LANDMARK.MOUTH_RIGHT);
    data.mouthOpen = Math.max(0, Math.min(1, mouthHeight / mouthWidth / 0.6));

    // Head Rotation (simplified)
    const nose = landmarks[LANDMARK.NOSE_TIP];
    const faceLeft = landmarks[LANDMARK.FACE_LEFT];
    const faceRight = landmarks[LANDMARK.FACE_RIGHT];

    // Yaw (left-right rotation)
    const faceCenterX = (faceLeft.x + faceRight.x) / 2;
    data.headRotationY = (nose.x - faceCenterX) * 2; // -1 to 1 range approximately

    // Pitch (up-down nod)
    data.headRotationX = (nose.y - 0.5) * 2; // Simplified

    // Roll (head tilt)
    data.headRotationZ = Math.atan2(
      faceRight.y - faceLeft.y,
      faceRight.x - faceLeft.x
    );

    return data;
  }

  get running(): boolean {
    return this.isRunning;
  }
}

// Singleton instance
export const faceTracker = new FaceTracker();
