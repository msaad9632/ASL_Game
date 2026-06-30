import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCamera } from '@/hooks/useCamera';
import { useRecognition } from '@/hooks/useRecognition';
import { useSounds } from '@/hooks/useSounds';
import { useConfetti } from '@/hooks/useConfetti';
import { ParameterChecklist } from '@/components/lesson/ParameterChecklist';
import { useUserStore } from '@/stores/useUserStore';
import { useAuth } from '@/contexts/AuthContext';
import { logSignAttempt } from '@/hooks/useProgressSync';
import { SIGNS as ENGINE_SIGNS } from '@/engine/signs/index';
import { SIGNS } from '@/data/signs';
import type { StoryScript } from '@/data/stories';
import type { VerifyResult } from '@/engine/verifier';

type Phase = 'intro' | 'dialogue' | 'response' | 'complete';

interface Props {
  story: StoryScript;
  onExit: () => void;
}

export function StoryPage({ story, onExit }: Props) {
  const { addXp, addDailyMinutes, recordSign, completeLesson } = useUserStore();
  const { user } = useAuth();
  const { videoRef, status: camStatus, start: startCam, stop: stopCam } = useCamera();
  const sounds = useSounds();
  const { burst, bigCelebration } = useConfetti();
  const [phase, setPhase] = useState<Phase>('intro');
  const [lineIdx, setLineIdx] = useState(0);
  const [earnedXp, setEarnedXp] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const loopStartedRef = useRef<string | null>(null);

  const currentLine = story.lines[lineIdx];
  const currentEngineSign = currentLine ? ENGINE_SIGNS[currentLine.requiredSignId] : null;
  const currentSignData = currentLine ? SIGNS[currentLine.requiredSignId] : null;

  const handlePass = useCallback(
    (_result: VerifyResult) => {
      if (phase !== 'dialogue') return;
      setPhase('response');
      sounds.correct();
      burst();
      if (currentLine) {
        recordSign(currentLine.requiredSignId, true);
        addDailyMinutes(2);
        addXp(10);
        setEarnedXp((p) => p + 10);
        if (user) logSignAttempt(user.id, currentLine.requiredSignId, true);
      }

      timerRef.current = setTimeout(() => {
        if (lineIdx + 1 < story.lines.length) {
          setLineIdx((p) => p + 1);
          setPhase('dialogue');
        } else {
          setPhase('complete');
          completeLesson(story.id);
          sounds.levelUp();
          bigCelebration();
        }
      }, 2000);
    },
    [phase, lineIdx, currentLine, story, recordSign, addXp, completeLesson]
  );

  const recognition = useRecognition({ onPass: handlePass });

  useEffect(() => {
    recognition.init();
  }, [recognition.init]);

  useEffect(() => {
    if (phase !== 'dialogue') {
      if (loopStartedRef.current) {
        recognition.stopLoop();
        loopStartedRef.current = null;
      }
      return;
    }
    if (
      camStatus === 'active' &&
      (recognition.status === 'ready' || recognition.status === 'running') &&
      currentEngineSign &&
      videoRef.current
    ) {
      if (loopStartedRef.current !== currentEngineSign.name) {
        recognition.stopLoop();
        recognition.startLoop(videoRef.current, currentEngineSign);
        loopStartedRef.current = currentEngineSign.name;
      }
    }
  });

  useEffect(() => {
    return () => {
      clearTimeout(timerRef.current);
      stopCam();
      recognition.stopLoop();
    };
  }, []);

  const handleStart = async () => {
    await startCam();
    setPhase('dialogue');
  };

  const moodEmoji: Record<string, string> = {
    neutral: '😊',
    happy: '😄',
    curious: '🤔',
    surprised: '😲',
  };

  return (
    <div className="min-h-screen bg-z-bg flex flex-col">
      <video
        ref={videoRef}
        style={{ width: 0, height: 0, opacity: 0, position: 'fixed', pointerEvents: 'none' }}
        muted playsInline autoPlay
      />

      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-z-purple-deep/40">
        <button
          onClick={() => { stopCam(); recognition.stopLoop(); onExit(); }}
          className="w-8 h-8 flex items-center justify-center text-z-gray-400 hover:text-white"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
        <h1 className="font-bold text-lg">{story.title}</h1>
        {phase === 'dialogue' && (
          <span className="ml-auto text-sm text-z-gray-400">{lineIdx + 1}/{story.lines.length}</span>
        )}
      </div>

      <div className="flex-1 max-w-lg mx-auto w-full px-4 pb-6 flex flex-col">
        <AnimatePresence mode="wait">
          {/* INTRO */}
          {phase === 'intro' && (
            <motion.div
              key="intro"
              className="flex-1 flex flex-col items-center justify-center gap-5"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="text-6xl">{story.backgroundEmoji}</div>
              <h2 className="text-2xl font-bold">{story.title}</h2>
              <p className="text-z-gray-300 text-center max-w-xs">{story.description}</p>

              <div className="flex items-center gap-3 bg-z-card rounded-2xl p-4 border border-white/5 w-full max-w-xs">
                <span className="text-3xl">{story.npcEmoji}</span>
                <div>
                  <p className="font-bold">{story.npcName}</p>
                  <p className="text-xs text-z-gray-400">Your barista</p>
                </div>
              </div>

              {recognition.status === 'loading' && (
                <p className="text-sm text-z-gray-400 animate-pulse">Loading...</p>
              )}

              <motion.button
                onClick={handleStart}
                disabled={recognition.status === 'loading'}
                className="mt-2 px-8 py-3 rounded-2xl font-bold text-white text-lg disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #7C3AED, #A78BFA)' }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                Start
              </motion.button>
            </motion.div>
          )}

          {/* DIALOGUE */}
          {phase === 'dialogue' && currentLine && (
            <motion.div
              key={`dialogue-${lineIdx}`}
              className="flex-1 flex flex-col gap-4 pt-4"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
            >
              {/* NPC bubble */}
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-2xl bg-z-purple flex items-center justify-center text-2xl shrink-0">
                  {moodEmoji[currentLine.npcMood]}
                </div>
                <div className="bg-z-card border border-white/5 rounded-2xl rounded-tl-md px-4 py-3 flex-1">
                  <p className="text-sm font-bold text-z-purple-glow mb-0.5">{story.npcName}</p>
                  <p className="text-sm text-z-gray-100">{currentLine.npcText}</p>
                </div>
              </div>

              {/* Your turn prompt */}
              <div className="bg-z-surface/50 rounded-2xl p-4 border border-z-purple/30">
                <p className="text-xs text-z-gray-400 uppercase tracking-widest mb-1">Your turn — sign</p>
                <p className="text-xl font-bold text-z-purple-glow">
                  {currentSignData?.name.replace(/_/g, ' ')}
                </p>
                <p className="text-xs text-z-gray-300 mt-1">{currentLine.hint}</p>
              </div>

              {/* Webcam */}
              <WebcamMirror videoRef={videoRef} />

              {/* Params */}
              {recognition.result && (
                <ParameterChecklist
                  params={recognition.result.params}
                  movementKind={currentEngineSign?.movement.kind}
                />
              )}
            </motion.div>
          )}

          {/* NPC RESPONSE */}
          {phase === 'response' && currentLine && (
            <motion.div
              key={`response-${lineIdx}`}
              className="flex-1 flex flex-col items-center justify-center gap-4"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
            >
              <div className="w-16 h-16 rounded-2xl bg-z-purple flex items-center justify-center text-4xl">
                😄
              </div>
              <div className="bg-z-card border border-white/5 rounded-2xl px-6 py-4 text-center max-w-xs">
                <p className="text-sm font-bold text-z-purple-glow mb-1">{story.npcName}</p>
                <p className="text-base">{currentLine.npcResponse}</p>
              </div>
              <p className="text-z-yellow font-bold">+10 XP</p>
            </motion.div>
          )}

          {/* COMPLETE */}
          {phase === 'complete' && (
            <motion.div
              key="complete"
              className="flex-1 flex flex-col items-center justify-center gap-5"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="text-5xl">🎬</div>
              <h2 className="text-2xl font-bold">Story Complete!</h2>
              <p className="text-z-gray-300 text-center">
                You had a full conversation at the coffee shop!
              </p>
              <div className="flex gap-8 text-center">
                <div>
                  <p className="text-2xl font-bold text-z-yellow">{earnedXp}</p>
                  <p className="text-xs text-z-gray-400">XP earned</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-z-green">{story.lines.length}/{story.lines.length}</p>
                  <p className="text-xs text-z-gray-400">exchanges</p>
                </div>
              </div>
              <motion.button
                onClick={onExit}
                className="mt-4 px-8 py-3 rounded-2xl font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #7C3AED, #A78BFA)' }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                Back to Home
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function WebcamMirror({ videoRef }: { videoRef: React.RefObject<HTMLVideoElement | null> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef(0);

  useEffect(() => {
    const draw = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && canvas && video.readyState >= 2) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.save();
          ctx.scale(-1, 1);
          ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
          ctx.restore();
        }
      }
      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, [videoRef]);

  return (
    <div className="relative rounded-2xl overflow-hidden bg-z-surface aspect-video">
      <canvas ref={canvasRef} className="w-full h-full object-cover" />
    </div>
  );
}
