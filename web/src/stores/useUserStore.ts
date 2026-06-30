import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserProgress } from '@/types/user';

function defaultProgress(): UserProgress {
  return {
    xp: 0,
    level: 1,
    streak: 0,
    lastPracticeDate: null,
    streakFreezes: 1,
    dailyGoalMinutes: 10,
    dailyProgressMinutes: 0,
    completedLessons: [],
    signAccuracy: {},
    achievements: [],
  };
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

interface UserStore extends UserProgress {
  addXp: (amount: number) => void;
  addDailyMinutes: (minutes: number) => void;
  completeLesson: (lessonId: string) => void;
  recordSign: (signId: string, correct: boolean) => void;
  checkStreak: () => void;
  reset: () => void;
  mergeProgress: (remote: Partial<UserProgress>) => void;
}

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      ...defaultProgress(),

      addXp: (amount: number) => {
        set((s) => {
          const newXp = s.xp + amount;
          const newLevel = Math.floor(newXp / 100) + 1;
          return { xp: newXp, level: newLevel };
        });
      },

      addDailyMinutes: (minutes: number) => {
        set((s) => ({ dailyProgressMinutes: s.dailyProgressMinutes + minutes }));
      },

      completeLesson: (lessonId: string) => {
        set((s) => {
          if (s.completedLessons.includes(lessonId)) return s;
          return { completedLessons: [...s.completedLessons, lessonId] };
        });
        get().checkStreak();
      },

      recordSign: (signId: string, correct: boolean) => {
        set((s) => {
          const prev = s.signAccuracy[signId] ?? {
            attempts: 0,
            successes: 0,
            lastAttempt: 0,
            nextReviewAt: 0,
            interval: 1,
            easeFactor: 2.5,
          };

          let { interval, easeFactor } = prev;
          if (correct) {
            interval = interval === 1 ? 6 : Math.round(interval * easeFactor);
            easeFactor = Math.max(1.3, easeFactor + 0.1);
          } else {
            interval = 1;
            easeFactor = Math.max(1.3, easeFactor - 0.2);
          }

          const now = Date.now();
          return {
            signAccuracy: {
              ...s.signAccuracy,
              [signId]: {
                attempts: prev.attempts + 1,
                successes: prev.successes + (correct ? 1 : 0),
                lastAttempt: now,
                nextReviewAt: now + interval * 24 * 60 * 60 * 1000,
                interval,
                easeFactor,
              },
            },
          };
        });
      },

      checkStreak: () => {
        set((s) => {
          const today = todayStr();
          if (s.lastPracticeDate === today) return s;

          const yesterday = new Date();
          yesterday.setDate(yesterday.getDate() - 1);
          const yesterdayStr = yesterday.toISOString().slice(0, 10);

          let newStreak = s.streak;
          if (s.lastPracticeDate === yesterdayStr) {
            newStreak += 1;
          } else if (s.lastPracticeDate !== today) {
            if (s.streakFreezes > 0 && s.lastPracticeDate) {
              return {
                lastPracticeDate: today,
                streakFreezes: s.streakFreezes - 1,
              };
            }
            newStreak = 1;
          }
          return { streak: newStreak, lastPracticeDate: today };
        });
      },

      reset: () => set(defaultProgress()),

      // Called after sign-in: take the best of local + remote.
      mergeProgress: (remote: Partial<UserProgress>) => {
        set((local) => {
          const merged: Partial<UserProgress> = {};

          if ((remote.xp ?? 0) > local.xp) merged.xp = remote.xp;
          if ((remote.level ?? 1) > local.level) merged.level = remote.level;
          if ((remote.streak ?? 0) > local.streak) merged.streak = remote.streak;

          if (remote.completedLessons) {
            const union = Array.from(new Set([...local.completedLessons, ...remote.completedLessons]));
            merged.completedLessons = union;
          }

          if (remote.signAccuracy) {
            const merged_acc = { ...local.signAccuracy };
            for (const [id, rs] of Object.entries(remote.signAccuracy)) {
              const ls = local.signAccuracy[id];
              if (!ls || rs.lastAttempt > ls.lastAttempt) merged_acc[id] = rs;
            }
            merged.signAccuracy = merged_acc;
          }

          if (remote.lastPracticeDate) merged.lastPracticeDate = remote.lastPracticeDate;

          return merged;
        });
      },
    }),
    {
      name: 'asl-game-progress',
    }
  )
);
