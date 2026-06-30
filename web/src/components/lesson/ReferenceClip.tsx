import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

interface Props {
  clipUrl: string;
  signName: string;
}

export function ReferenceClip({ clipUrl, signName }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
  }, [clipUrl]);

  return (
    <motion.div
      className="relative rounded-2xl overflow-hidden bg-duo-surface aspect-video"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <video
        ref={videoRef}
        src={clipUrl}
        loop
        muted
        playsInline
        className="w-full h-full object-cover"
      />
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3">
        <p className="text-white text-sm font-bold">{signName.replace(/_/g, ' ')}</p>
        <p className="text-white/70 text-xs">Watch and follow along</p>
      </div>
    </motion.div>
  );
}
