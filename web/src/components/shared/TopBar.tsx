import { useUserStore } from '@/stores/useUserStore';
import { motion, type Variants } from 'framer-motion';

const fireVariants: Variants = {
  rest: { rotate: 0, x: 0, scale: 1, filter: 'brightness(1) drop-shadow(0 0 0px rgba(249,115,22,0))', transition: { duration: 0.3, ease: 'easeOut' } },
  blaze: {
    rotate: [0, -4, 3, -3, 2, 0],
    x:      [0, -1.5, 1, -1, 0.5, 0],
    scale:  [1, 1.09, 1.04, 1.11, 1.05, 1],
    filter: [
      'brightness(1)    drop-shadow(0 0px 0px rgba(249,115,22,0))',
      'brightness(1.25) drop-shadow(0 -3px 8px rgba(249,115,22,0.7))',
      'brightness(1.1)  drop-shadow(0 -2px 4px rgba(249,115,22,0.4))',
      'brightness(1.3)  drop-shadow(0 -4px 10px rgba(249,115,22,0.8))',
      'brightness(1.12) drop-shadow(0 -2px 5px rgba(249,115,22,0.5))',
      'brightness(1)    drop-shadow(0 0px 0px rgba(249,115,22,0))',
    ],
    transition: { duration: 1.9, repeat: Infinity, ease: 'easeInOut' },
  },
};

const sparkleVariants: Variants = {
  rest:    { scale: 1, filter: 'brightness(1) drop-shadow(0 0 0px rgba(94,234,212,0))', transition: { duration: 0.3, ease: 'easeOut' } },
  sparkle: {
    scale:  [1, 1.07, 1, 1.05, 1],
    filter: [
      'brightness(1)   drop-shadow(0 0 0px rgba(94,234,212,0))',
      'brightness(1.6) drop-shadow(0 0 6px rgba(94,234,212,0.8))',
      'brightness(0.9) drop-shadow(0 0 2px rgba(94,234,212,0.3))',
      'brightness(1.5) drop-shadow(0 0 5px rgba(94,234,212,0.7))',
      'brightness(1)   drop-shadow(0 0 0px rgba(94,234,212,0))',
    ],
    transition: { duration: 3.4, repeat: Infinity, ease: 'easeInOut' },
  },
};

export function TopBar() {
  const { streak, xp } = useUserStore();

  return (
    <div className="sticky top-0 z-50 bg-z-bg/90 backdrop-blur-md border-b border-z-purple-deep/50">
      <div className="max-w-lg mx-auto flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <motion.span
            className="text-2xl inline-block"
            whileHover={{ rotate: [0, -15, 15, -10, 0], transition: { duration: 0.4 } }}
          >🤟</motion.span>
          <span
            className="font-bold text-xl tracking-tight"
            style={{
              background: 'linear-gradient(90deg, #A78BFA 0%, #14B8A6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >SignUp</span>
        </div>

        <div className="flex items-center gap-4">
          {/* Streak — fire blazes on hover */}
          <motion.div
            className="flex items-center gap-1.5 bg-z-surface/60 rounded-full px-3 py-1 cursor-default"
            initial="rest"
            whileHover="blaze"
            whileTap={{ scale: 0.92 }}
            variants={{
              rest:  { scale: 1, backgroundColor: 'rgba(34, 21, 72, 0.6)' },
              blaze: { scale: 1.1, backgroundColor: 'rgba(249, 115, 22, 0.16)', transition: { duration: 0.2 } },
            }}
          >
            <motion.span className="text-base inline-block" variants={fireVariants}>🔥</motion.span>
            <span className="font-bold text-sm text-z-orange">{streak}</span>
          </motion.div>

          {/* XP — star sparkles on hover */}
          <motion.div
            className="flex items-center gap-1.5 bg-z-surface/60 rounded-full px-3 py-1 cursor-default"
            initial="rest"
            whileHover="sparkle"
            whileTap={{ scale: 0.92 }}
            variants={{
              rest:    { scale: 1, backgroundColor: 'rgba(34, 21, 72, 0.6)' },
              sparkle: { scale: 1.1, backgroundColor: 'rgba(94, 234, 212, 0.12)', transition: { duration: 0.2 } },
            }}
          >
            <motion.span className="text-base inline-block" variants={sparkleVariants}>✨</motion.span>
            <span className="font-bold text-sm text-z-yellow">{xp} XP</span>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
