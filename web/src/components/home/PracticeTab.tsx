import { motion } from 'framer-motion';
import { SIGNS } from '@/data/signs';
import { useUserStore } from '@/stores/useUserStore';

interface Props {
  onStartPractice: () => void;
  onStartStory: () => void;
}

export function PracticeTab({ onStartPractice, onStartStory }: Props) {
  const { signAccuracy } = useUserStore();

  const signEntries = Object.entries(SIGNS);
  const dueForReview = signEntries.filter(([id]) => {
    const stats = signAccuracy[id];
    if (!stats) return false;
    return stats.nextReviewAt <= Date.now();
  });

  return (
    <div className="px-4 pb-24">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="text-2xl font-bold mb-1 tracking-tight">Review</h2>
        <p className="text-z-gray-300 text-sm mb-6">
          Sharpen your signs with spaced recall
        </p>
      </motion.div>

      {/* Quick session */}
      <motion.button
        onClick={onStartPractice}
        className="w-full rounded-2xl p-5 mb-3 text-left border border-white/5 overflow-hidden relative"
        style={{ background: 'linear-gradient(135deg, #5B21B6, #7C3AED)' }}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
      >
        <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full blur-2xl" />
        <div className="relative flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">Quick Session</h3>
            <p className="text-purple-200 text-sm mt-1">
              {dueForReview.length > 0
                ? `${dueForReview.length} sign${dueForReview.length > 1 ? 's' : ''} to review`
                : 'Warm up with your learned signs'}
            </p>
          </div>
          <span className="text-3xl">🤟</span>
        </div>
      </motion.button>

      {/* Story mode */}
      <motion.button
        onClick={onStartStory}
        className="w-full rounded-2xl p-5 mb-3 text-left border border-white/5 overflow-hidden relative"
        style={{ background: 'linear-gradient(135deg, #0F766E, #14B8A6)' }}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12 }}
      >
        <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full blur-2xl" />
        <div className="relative flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">Coffee Shop Story</h3>
            <p className="text-teal-100 text-sm mt-1">
              Chat with Zippy the barista in ASL
            </p>
          </div>
          <span className="text-3xl">☕</span>
        </div>
      </motion.button>

      {/* Sign grid */}
      <h3 className="font-bold text-sm mb-3 mt-6 text-z-gray-300 uppercase tracking-widest">
        Your vocabulary
      </h3>
      <div className="grid grid-cols-3 gap-2">
        {signEntries.map(([id, sign], i) => {
          const stats = signAccuracy[id];
          const accuracy = stats
            ? Math.round((stats.successes / stats.attempts) * 100)
            : null;

          return (
            <motion.div
              key={id}
              className="bg-z-card border border-white/5 rounded-xl p-3 text-center"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.02 }}
            >
              <p className="font-semibold text-xs truncate text-z-gray-100">
                {sign.name.replace(/_/g, ' ')}
              </p>
              {accuracy !== null ? (
                <p className={`text-[11px] mt-1 font-bold ${
                  accuracy >= 70 ? 'text-z-green' : 'text-z-orange'
                }`}>
                  {accuracy}%
                </p>
              ) : (
                <p className="text-[11px] mt-1 text-z-gray-500">—</p>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
