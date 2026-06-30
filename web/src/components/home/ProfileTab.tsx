import { useState } from 'react';
import { motion, type Variant } from 'framer-motion';
import { useUserStore } from '@/stores/useUserStore';
import { useAuth } from '@/contexts/AuthContext';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import { AuthModal } from '@/components/auth/AuthModal';
import { supabaseReady } from '@/lib/supabase';

const FIRE_REST: Variant = { rotate: 0, x: 0, scale: 1, filter: 'brightness(1) drop-shadow(0 0 0px rgba(249,115,22,0))', transition: { duration: 0.3, ease: 'easeOut' } };

const FIRE_HOVER: Variant = {
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
};

const SPARKLE_REST: Variant = { scale: 1, filter: 'brightness(1) drop-shadow(0 0 0px rgba(94,234,212,0))', transition: { duration: 0.3, ease: 'easeOut' } };

const SPARKLE_HOVER: Variant = {
  scale:  [1, 1.07, 1, 1.05, 1],
  filter: [
    'brightness(1)   drop-shadow(0 0 0px rgba(94,234,212,0))',
    'brightness(1.6) drop-shadow(0 0 6px rgba(94,234,212,0.8))',
    'brightness(0.9) drop-shadow(0 0 2px rgba(94,234,212,0.3))',
    'brightness(1.5) drop-shadow(0 0 5px rgba(94,234,212,0.7))',
    'brightness(1)   drop-shadow(0 0 0px rgba(94,234,212,0))',
  ],
  transition: { duration: 3.4, repeat: Infinity, ease: 'easeInOut' },
};

const CONFETTI = [
  { x: -26, y: -30, rot: -130, color: '#A78BFA', w: 5, h: 3 },
  { x: -36, y: -16, rot: -158, color: '#F97316', w: 4, h: 4 },
  { x: -20, y: -40, rot: -92,  color: '#5EEAD4', w: 3, h: 5 },
  { x: -40, y: -26, rot: -58,  color: '#FDBA74', w: 5, h: 3 },
  { x: -15, y: -22, rot: -176, color: '#7C3AED', w: 4, h: 4 },
  { x:  26, y: -30, rot:  130, color: '#14B8A6', w: 5, h: 3 },
  { x:  36, y: -16, rot:  158, color: '#A78BFA', w: 4, h: 4 },
  { x:  20, y: -40, rot:  92,  color: '#F97316', w: 3, h: 5 },
  { x:  40, y: -26, rot:  58,  color: '#FDBA74', w: 5, h: 3 },
  { x:  15, y: -22, rot:  176, color: '#7C3AED', w: 4, h: 4 },
];

function TrophyIcon({ burst }: { burst: number }) {
  return (
    <div className="relative inline-flex items-center justify-center">
      <motion.span
        className="text-2xl inline-block"
        variants={{
          rest:  { scale: 1, y: 0, rotate: 0, transition: { duration: 0.25, ease: 'easeOut' } },
          hover: { scale: 1.18, y: -3, rotate: [-5, 5, -3, 0], transition: { duration: 0.4 } },
        }}
      >
        🏆
      </motion.span>

      {burst > 0 && (
        <div key={burst} className="absolute inset-0 pointer-events-none">
          {CONFETTI.map((p, i) => (
            <motion.div
              key={i}
              className="absolute rounded-sm"
              style={{
                width: p.w, height: p.h, background: p.color,
                top: '50%', left: '50%',
                marginLeft: -p.w / 2, marginTop: -p.h / 2,
                zIndex: 20,
              }}
              initial={{ x: 0, y: 0, opacity: 1, rotate: 0, scale: 0 }}
              animate={{ x: p.x, y: p.y, opacity: [1, 1, 0], rotate: p.rot, scale: [0, 1.2, 0.9] }}
              transition={{ duration: 0.9, ease: 'easeOut', delay: i * 0.025 }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function cardVariants(glowColor: string) {
  return {
    rest:  { scale: 1, y: 0, boxShadow: '0 0 0 rgba(0,0,0,0)', transition: { duration: 0.22 } },
    hover: { scale: 1.05, y: -4, boxShadow: `0 10px 28px ${glowColor}`, transition: { duration: 0.22 } },
  };
}

export function ProfileTab() {
  const { xp, level, streak, lastPracticeDate, completedLessons, signAccuracy } = useUserStore();
  const { user, username, signOut } = useAuth();
  const { rows, loading: lbLoading } = useLeaderboard();
  const [showAuth, setShowAuth] = useState(false);
  const [levelBurst, setLevelBurst] = useState(0);

  const totalSigns = Object.keys(signAccuracy).length;
  const masteredSigns = Object.values(signAccuracy).filter(
    (s) => s.successes >= 3 && s.successes / s.attempts >= 0.7
  ).length;

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
        <motion.div
          className="w-20 h-20 rounded-3xl bg-gradient-to-br from-z-purple to-z-purple-deep flex items-center justify-center text-4xl mx-auto mb-3 shadow-lg shadow-z-purple/30 cursor-default"
          whileHover={{ rotate: [0, -12, 12, -8, 0], scale: 1.08, transition: { duration: 0.45 } }}
          whileTap={{ scale: 0.95 }}
        >
          🤟
        </motion.div>
        <p className="text-z-gray-300 text-sm">
          {masteredSigns > 0
            ? `${masteredSigns} of ${totalSigns} signs mastered`
            : 'Start signing to track progress'}
        </p>
      </motion.div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 mb-6">

        {/* Total XP */}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0 }}>
          <motion.div
            className="bg-z-card border border-white/5 rounded-2xl p-4 text-center cursor-default"
            initial="rest" animate="rest" whileHover="hover"
            variants={cardVariants('rgba(94,234,212,0.22)')}
          >
            <motion.span className="text-2xl inline-block" variants={{ rest: SPARKLE_REST, hover: SPARKLE_HOVER }}>
              ✨
            </motion.span>
            <p className="text-2xl font-bold mt-1 text-z-yellow">{xp}</p>
            <p className="text-[11px] text-z-gray-400 mt-0.5 tracking-wide">Total XP</p>
          </motion.div>
        </motion.div>

        {/* Level */}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.06 }}>
          <motion.div
            className="bg-z-card border border-white/5 rounded-2xl p-4 text-center cursor-default"
            initial="rest" animate="rest" whileHover="hover"
            onHoverStart={() => setLevelBurst((b) => b + 1)}
            variants={cardVariants('rgba(250,204,21,0.32)')}
          >
            <TrophyIcon burst={levelBurst} />
            <p className="text-2xl font-bold mt-1 text-z-orange">{level}</p>
            <p className="text-[11px] text-z-gray-400 mt-0.5 tracking-wide">Level</p>
          </motion.div>
        </motion.div>

        {/* Streak */}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.12 }}>
          <motion.div
            className="bg-z-card border border-white/5 rounded-2xl p-4 text-center cursor-default"
            initial="rest" animate="rest" whileHover="hover"
            variants={cardVariants('rgba(249,115,22,0.22)')}
          >
            <motion.span className="text-2xl inline-block" variants={{ rest: FIRE_REST, hover: FIRE_HOVER }}>
              🔥
            </motion.span>
            <p className="text-2xl font-bold mt-1 text-z-orange-bright">{streak}d</p>
            <p className="text-[11px] text-z-gray-400 mt-0.5 tracking-wide">Streak</p>
          </motion.div>
        </motion.div>

        {/* Completed */}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.18 }}>
          <motion.div
            className="bg-z-card border border-white/5 rounded-2xl p-4 text-center cursor-default"
            initial="rest" animate="rest" whileHover="hover"
            variants={cardVariants('rgba(96,165,250,0.32)')}
          >
            <motion.span
              className="text-2xl inline-block"
              variants={{
                rest:  { y: 0, rotate: 0, transition: { duration: 0.25, ease: 'easeOut' } },
                hover: { y: -5, rotate: [0, -7, 6, -4, 0], transition: { duration: 0.55, ease: 'easeInOut' } },
              }}
            >📖</motion.span>
            <p className="text-2xl font-bold mt-1 text-z-purple-light">{completedLessons.length}</p>
            <p className="text-[11px] text-z-gray-400 mt-0.5 tracking-wide">Completed</p>
          </motion.div>
        </motion.div>

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
            const todayIdx = today.getDay() === 0 ? 6 : today.getDay() - 1;
            const isToday = i === todayIdx;
            const isFuture = i > todayIdx;

            let practiced = false;
            if (lastPracticeDate && streak > 0) {
              const last = new Date(lastPracticeDate);
              const lastIdx = last.getDay() === 0 ? 6 : last.getDay() - 1;
              const daysAgo = todayIdx - i + (lastIdx < todayIdx ? todayIdx - lastIdx : 0);
              practiced = daysAgo >= 0 && daysAgo < streak && i <= lastIdx;
            }

            return (
              <div key={i} className="flex flex-col items-center gap-1.5">
                <span className="text-[10px] text-z-gray-400 font-semibold">{day}</span>
                <div className={`relative w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold ${
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
                  {isToday && (
                    <motion.div
                      className="absolute inset-0 rounded-xl border-2 border-z-purple-light"
                      animate={{ scale: [1, 1.6, 1], opacity: [0.8, 0, 0.8] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    />
                  )}
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
