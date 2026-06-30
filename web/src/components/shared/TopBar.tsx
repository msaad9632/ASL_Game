import { useUserStore } from '@/stores/useUserStore';
import { motion } from 'framer-motion';

export function TopBar() {
  const { streak, xp } = useUserStore();

  return (
    <div className="sticky top-0 z-50 bg-z-bg/90 backdrop-blur-md border-b border-z-purple-deep/50">
      <div className="max-w-lg mx-auto flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🤟</span>
          <span
            className="font-bold text-xl tracking-tight"
            style={{
              background: 'linear-gradient(90deg, #A78BFA 0%, #14B8A6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >SignUp</span>
        </div>

        <div className="flex items-center gap-5">
          <motion.div
            className="flex items-center gap-1.5 bg-z-surface/60 rounded-full px-3 py-1"
            whileHover={{ scale: 1.05 }}
          >
            <span className="text-base">🔥</span>
            <span className="font-bold text-sm text-z-orange">{streak}</span>
          </motion.div>

          <div className="flex items-center gap-1.5 bg-z-surface/60 rounded-full px-3 py-1">
            <span className="text-base">✨</span>
            <span className="font-bold text-sm text-z-yellow">{xp} XP</span>
          </div>
        </div>
      </div>
    </div>
  );
}
