import { useState } from 'react';
import { motion } from 'framer-motion';
import { useUserStore } from '@/stores/useUserStore';
import { useAuth } from '@/contexts/AuthContext';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import { AuthModal } from '@/components/auth/AuthModal';
import { supabaseReady } from '@/lib/supabase';

export function ProfileTab() {
  const { xp, level, streak, lastPracticeDate, completedLessons, signAccuracy } = useUserStore();
  const { user, username, signOut } = useAuth();
  const { rows, loading: lbLoading } = useLeaderboard();
  const [showAuth, setShowAuth] = useState(false);

  const totalSigns = Object.keys(signAccuracy).length;
  const masteredSigns = Object.values(signAccuracy).filter(
    (s) => s.successes >= 3 && s.successes / s.attempts >= 0.7
  ).length;

  const stats = [
    { label: 'Total XP', value: xp, icon: '✨', color: 'text-z-yellow' },
    { label: 'Level', value: level, icon: '🏆', color: 'text-z-orange' },
    { label: 'Streak', value: `${streak}d`, icon: '🔥', color: 'text-z-orange-bright' },
    { label: 'Completed', value: completedLessons.length, icon: '📖', color: 'text-z-purple-light' },
  ];

  return (
    <div className="px-4 pb-24">
      {/* Auth banner */}
      <motion.div
        className="mb-5"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {user ? (
          <div className="bg-z-card border border-white/5 rounded-2xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-z-purple to-z-purple-deep flex items-center justify-center text-lg">
                🤟
              </div>
              <div>
                <p className="font-bold text-sm">{username ?? '…'}</p>
                <p className="text-z-gray-400 text-xs">Progress syncing</p>
              </div>
            </div>
            <button
              onClick={signOut}
              className="text-xs text-z-gray-400 hover:text-white border border-white/10 rounded-lg px-3 py-1.5 transition-colors"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="bg-z-card border border-white/5 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="font-bold text-sm">Save your progress</p>
              <p className="text-z-gray-400 text-xs">Sign in to sync + join leaderboards</p>
            </div>
            <button
              onClick={() => setShowAuth(true)}
              className="text-xs bg-z-purple text-white rounded-xl px-4 py-2 font-bold"
            >
              Sign in
            </button>
          </div>
        )}
      </motion.div>

      {/* Avatar + mastery */}
      <motion.div
        className="text-center mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
      >
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-z-purple to-z-purple-deep flex items-center justify-center text-4xl mx-auto mb-3 shadow-lg shadow-z-purple/30">
          🤟
        </div>
        <p className="text-z-gray-300 text-sm">
          {masteredSigns > 0
            ? `${masteredSigns} of ${totalSigns} signs mastered`
            : 'Start signing to track progress'}
        </p>
      </motion.div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            className="bg-z-card border border-white/5 rounded-2xl p-4 text-center"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.06 }}
          >
            <span className="text-2xl">{stat.icon}</span>
            <p className={`text-2xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
            <p className="text-[11px] text-z-gray-400 mt-0.5 tracking-wide">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Weekly calendar */}
      <motion.div
        className="bg-z-card border border-white/5 rounded-2xl p-5 mb-5"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.28 }}
      >
        <h3 className="font-bold text-base mb-3 tracking-wide">This Week</h3>
        <div className="flex justify-between">
          {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, i) => {
            const today = new Date();
            const todayIdx = today.getDay() === 0 ? 6 : today.getDay() - 1; // 0=Mon
            const isToday = i === todayIdx;
            const isFuture = i > todayIdx;

            // Work out if this weekday was a practice day based on streak.
            // lastPracticeDate tells us the most recent day; streak tells us
            // how many consecutive days back were active.
            let practiced = false;
            if (lastPracticeDate && streak > 0) {
              const last = new Date(lastPracticeDate);
              const lastIdx = last.getDay() === 0 ? 6 : last.getDay() - 1;
              // How many days ago was the last practice day, within this week?
              const daysAgo = todayIdx - i + (lastIdx < todayIdx ? todayIdx - lastIdx : 0);
              practiced = daysAgo >= 0 && daysAgo < streak && i <= lastIdx;
            }

            return (
              <div key={i} className="flex flex-col items-center gap-1.5">
                <span className="text-[10px] text-z-gray-400 font-semibold">{day}</span>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold ${
                  isToday && lastPracticeDate === today.toISOString().slice(0, 10)
                    ? 'bg-z-purple text-white shadow-md shadow-z-purple/40'
                    : isToday
                      ? 'bg-z-purple/30 text-z-purple-light border border-z-purple/40'
                      : practiced
                        ? 'bg-z-green/20 text-z-green'
                        : isFuture
                          ? 'bg-transparent text-z-gray-500 border border-z-gray-500/20'
                          : 'bg-z-surface/40 text-z-gray-500'
                }`}>
                  {practiced || (isToday && lastPracticeDate === today.toISOString().slice(0, 10))
                    ? '✓'
                    : isToday
                      ? '●'
                      : ''}
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Weekly leaderboard */}
      {supabaseReady && (
        <motion.div
          className="bg-z-card border border-white/5 rounded-2xl p-5"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.36 }}
        >
          <h3 className="font-bold text-base mb-3 tracking-wide">Weekly Leaderboard</h3>
          {lbLoading ? (
            <p className="text-z-gray-400 text-sm text-center py-4">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="text-z-gray-400 text-sm text-center py-4">
              No one on the board yet — be the first!
            </p>
          ) : (
            <div className="space-y-2">
              {rows.slice(0, 10).map((row, i) => (
                <div
                  key={row.id}
                  className={`flex items-center gap-3 px-3 py-2 rounded-xl ${
                    row.id === user?.id ? 'bg-z-purple/20 border border-z-purple/30' : 'bg-white/3'
                  }`}
                >
                  <span className="w-5 text-center text-xs font-bold text-z-gray-400">
                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`}
                  </span>
                  <span className="flex-1 text-sm font-semibold truncate">{row.username}</span>
                  <span className="text-xs text-z-gray-300 tabular-nums">
                    {row.signs_this_week} signs
                  </span>
                  <span className="text-xs text-z-yellow tabular-nums font-bold">
                    {row.total_xp} XP
                  </span>
                </div>
              ))}
            </div>
          )}
          {!user && (
            <p className="text-z-gray-400 text-xs text-center mt-3">
              <button onClick={() => setShowAuth(true)} className="underline text-z-purple-light">
                Sign in
              </button>{' '}
              to appear on the board
            </p>
          )}
        </motion.div>
      )}

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}
