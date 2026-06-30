import { useUserStore } from '@/stores/useUserStore';
import { motion } from 'framer-motion';

export function StreakCard() {
  const { streak, dailyGoalMinutes, dailyProgressMinutes } = useUserStore();
  const progress = Math.min(1, dailyProgressMinutes / dailyGoalMinutes);

  return (
    <motion.div
      className="relative overflow-hidden rounded-3xl p-5 mb-6"
      style={{
        background: 'linear-gradient(135deg, #18103A 0%, #7C3AED 100%)',
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Decorative glow */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-z-purple-light/20 rounded-full blur-3xl" />

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <motion.span
                className="text-3xl"
                animate={{ rotate: [0, -8, 8, -8, 0] }}
                transition={{ duration: 0.6, delay: 0.5 }}
              >
                🔥
              </motion.span>
              <span className="text-2xl font-bold text-white">
                {streak} day{streak !== 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-sm text-z-purple-glow/80">
              {streak === 0 ? 'Start signing today!' : 'Keep the momentum!'}
            </p>
          </div>
          <div className="text-4xl opacity-80">🤟</div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="text-white/70">Today&apos;s goal</span>
            <span className="font-bold text-z-orange-bright">
              {dailyProgressMinutes}/{dailyGoalMinutes} min
            </span>
          </div>
          <div className="h-2.5 bg-white/15 rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg, #F97316, #FDBA74)' }}
              initial={{ width: 0 }}
              animate={{ width: `${progress * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: 0.3 }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
