import {
  HandLandmarker,
  PoseLandmarker,
  FilesetResolver,
} from '@mediapipe/tasks-vision';
import type { Frame, Hand } from './landmarks';
import {
  POSE_LEFT_SHOULDER,
  POSE_RIGHT_SHOULDER,
  POSE_MOUTH_LEFT,
  POSE_MOUTH_RIGHT,
} from './landmarks';

export class Capture {
  private hand: HandLandmarker | null = null;
  private pose: PoseLandmarker | null = null;
  private lastTsMs = -1;
  private _ready = false;
  private _logged = false;

  get ready(): boolean {
    return this._ready;
  }

  async init(): Promise<void> {
    const vision = await FilesetResolver.forVisionTasks(
      'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
    );

    this.hand = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numHands: 2,
      minHandDetectionConfidence: 0.4,
      minHandPresenceConfidence: 0.4,
      minTrackingConfidence: 0.4,
    });

    this.pose = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numPoses: 1,
    });

    this._ready = true;
  }

  process(video: HTMLVideoElement, timestampMs: number): Frame {
    if (!this.hand || !this.pose) {
      throw new Error('Capture not initialized — call init() first');
    }

    if (timestampMs <= this.lastTsMs) {
      timestampMs = this.lastTsMs + 1;
    }
    this.lastTsMs = timestampMs;

    const w = video.videoWidth;
    const h = video.videoHeight;

    if (w === 0 || h === 0) {
      return {
        t: timestampMs / 1000, width: 0, height: 0,
        hands: [], leftShoulder: null, rightShoulder: null, mouth: null,
      };
    }

    const handRes = this.hand.detectForVideo(video, timestampMs);
    const poseRes = this.pose.detectForVideo(video, timestampMs);

    if (!this._logged) {
      console.log('[SignUp] MediaPipe first result — hands:', handRes.landmarks?.length ?? 0,
        'pose:', poseRes.landmarks?.length ?? 0, 'video:', w, 'x', h);
      this._logged = true;
    }

    const frame: Frame = {
      t: timestampMs / 1000,
      width: w,
      height: h,
      hands: [],
      leftShoulder: null,
      rightShoulder: null,
      mouth: null,
    };

    if (handRes.landmarks && handRes.handedness) {
      for (let i = 0; i < handRes.landmarks.length; i++) {
        const lms = handRes.landmarks[i];
        const label = handRes.handedness[i][0].categoryName;
        const points: number[][] = lms.map((lm) => [lm.x * w, lm.y * h, lm.z]);
        frame.hands.push({ handedness: label, points } as Hand);
      }
    }

    if (poseRes.landmarks && poseRes.landmarks.length > 0) {
      const pose = poseRes.landmarks[0];
      const ls = pose[POSE_LEFT_SHOULDER];
      const rs = pose[POSE_RIGHT_SHOULDER];
      frame.leftShoulder = [ls.x * w, ls.y * h];
      frame.rightShoulder = [rs.x * w, rs.y * h];
      const ml = pose[POSE_MOUTH_LEFT];
      const mr = pose[POSE_MOUTH_RIGHT];
      frame.mouth = [(ml.x + mr.x) * 0.5 * w, (ml.y + mr.y) * 0.5 * h];
    }

    return frame;
  }

  close(): void {
    this.hand?.close();
    this.pose?.close();
    this.hand = null;
    this.pose = null;
    this._ready = false;
  }
}
