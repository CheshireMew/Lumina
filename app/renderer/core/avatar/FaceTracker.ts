import { FaceMesh, Results } from "@mediapipe/face_mesh";
import { Camera } from "@mediapipe/camera_utils";
import { FaceTrackingData } from "./types";
import { events } from "../events";

/**
 * Service to handle MediaPipe FaceMesh and emit tracking events.
 * Singleton pattern recommended.
 */
class FaceTrackerService {
  private faceMesh: FaceMesh | null = null;
  private camera: Camera | null = null;
  private videoElement: HTMLVideoElement | null = null;
  private isRunning = false;
  private debugCanvas: HTMLCanvasElement | null = null;

  constructor() {
    this.onResults = this.onResults.bind(this);
  }

  public async initialize(debugCanvas?: HTMLCanvasElement) {
    if (this.faceMesh) return;
    this.debugCanvas = debugCanvas || null;

    console.log("[FaceTracker] Initializing MediaPipe FaceMesh...");
    this.faceMesh = new FaceMesh({
      locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
      },
    });

    this.faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true, // Improved eyes/lips
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    this.faceMesh.onResults(this.onResults);
  }

  public async start() {
    if (this.isRunning) return;

    if (!this.faceMesh) await this.initialize();

    // Create invisible video element
    this.videoElement = document.createElement("video");
    this.videoElement.style.display = "none";
    document.body.appendChild(this.videoElement);

    console.log("[FaceTracker] Starting Camera...");
    try {
      this.camera = new Camera(this.videoElement, {
        onFrame: async () => {
          if (this.videoElement && this.faceMesh) {
            await this.faceMesh.send({ image: this.videoElement });
          }
        },
        width: 640,
        height: 480,
      });
      await this.camera.start();
      this.isRunning = true;
      console.log("[FaceTracker] Started");
    } catch (e) {
      console.error("[FaceTracker] Failed to start camera:", e);
      throw e;
    }
  }

  public stop() {
    if (!this.isRunning) return;

    console.log("[FaceTracker] Stopping...");
    if (this.camera) {
      this.camera.stop();
      this.camera = null;
    }
    if (this.videoElement) {
      document.body.removeChild(this.videoElement);
      this.videoElement = null;
    }
    this.isRunning = false;
  }

  private onResults(results: Results) {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0)
      return;

    const landmarks = results.multiFaceLandmarks[0];

    // 1. Calculate specific traits (Simplified for now)
    // In a real robust implementation, we would use Facial Action Coding System (FACS) logic
    // OR rely on MediaPipe's new Blendshapes API (if available in this version)
    // Since we are using an older version/basic setup, we do manual calculations.

    // Basic Blink Logic (Distance between eyelids)
    // Left Eye: 159 (top), 145 (bottom)
    // Right Eye: 386 (top), 374 (bottom)
    const leftBlink = this.calculateDistance(landmarks[159], landmarks[145]);
    const rightBlink = this.calculateDistance(landmarks[386], landmarks[374]);

    // Basic Mouth Open Logic
    // Top Lip: 13, Bottom Lip: 14
    const mouthOpen = this.calculateDistance(landmarks[13], landmarks[14]);

    // Normalize (These need calibration in a real app)
    const blinkThreshold = 0.02; // Heuristic
    const mouthThreshold = 0.05;

    const data: FaceTrackingData = {
      headPan: 0, // Need Pose estimation or PnP solver for rotation
      headTilt: 0,
      headRoll: 0,
      eyeBlinkLeft: leftBlink < blinkThreshold ? 1 : 0,
      eyeBlinkRight: rightBlink < blinkThreshold ? 1 : 0,
      jawOpen:
        mouthOpen > mouthThreshold
          ? Math.min((mouthOpen - mouthThreshold) * 10, 1)
          : 0,
      mouthSmile: 0, // Need smile logic
    };

    // If we want more robust rotation (Head Pose), we need 3D PnP solver.
    // For simplicity, we can approx head rotation by nose position relative to face width.
    // Nose tip: 1
    // Left Face Edge: 234, Right Face Edge: 454
    const nose = landmarks[1];
    const leftEdge = landmarks[234];
    const rightEdge = landmarks[454];

    const faceWidth = Math.abs(rightEdge.x - leftEdge.x);
    // Pan: Relative position of nose between cheeks. 0.5 = center.
    // Map 0..1 to -1..1
    data.headPan = ((nose.x - leftEdge.x) / faceWidth - 0.5) * 3; // Amplified

    // Tilt: Nose vs Eyes height (approx)
    // Eye Center: 168 (midpoint between eyes)
    // Nose Tip: 1
    const midEye = landmarks[168];
    const tiltRaw = nose.y - midEye.y;
    // Calibrate: Default distance approx 0.1?
    data.headTilt = (tiltRaw - 0.1) * 5;

    // Emit Event
    // console.log('[FaceTracker]', data); // Debug spam
    events.emit("avatar:face_tracking", data);
  }

  private calculateDistance(
    p1: { x: number; y: number },
    p2: { x: number; y: number }
  ) {
    return Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2));
  }
}

export const faceTracker = new FaceTrackerService();
