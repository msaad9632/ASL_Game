import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserProgress, SkillLevel, Quest, QuestType } from '@/types/user';
import { generateQuestsForToday } from '@/data/quests';

const STREAK_MILESTONES = [7, 30, 100];
const MILESTONE_GOLD: Record<number, number> = { 7: 5, 30: 15, 100: 50 };

const SKILL_UNLOCK_LESSONS: Record<SkillLevel, string[]> = {
  beginner: [],
  intermediate: ['greetings-1', 'cafe-order'],
  advanced: ['greetings-1', 'cafe-order', 'fingerspelling-1', 'fingerspelling-2'],
};

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
    onboardingComplete: false,
    skillLevel: 'beginner',
    dailyQuests: [],
    questsLastReset: '',
    streakMilestonesAwarded: [],
    signs: 0,
    gold: 0,
  };
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

interface UserStore extends UserProgress {
  addXp: (amount: number) => void;
  addSigns: (amount: number) => void;
  addGold: (amount: number) => void;
  addDailyMinutes: (minutes: number) => void;
  completeLesson: (lessonId: string) => void;
  recordSign: (signId: string, correct: boolean) => void;
  checkStreak: () => number[];
  reset: () => void;
  mergeProgress: (remote: Partial<UserProgress>) => void;
  completeOnboarding: (level: SkillLevel) => void;
  refreshDailyQuests: () => void;
  updateQuestProgress: (type: QuestType, delta?: number) => void;
  claimQuest: (questId: string) => void;
  recordPracticeSession: () => void;
}

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      ...defaultProgress(),

      addXp: (amount) => {
        set((s) => {
          const newXp = s.xp + amount;
          return { xp: newXp, level: Math.floor(newXp / 100) + 1 };
        });
      },

      addSigns: (amount) => set((s) => ({ signs: s.signs + amount })),
      addGold: (amount) => set((s) => ({ gold: s.gold + amount })),

      addDailyMinutes: (minutes) => {
        set((s) => ({ dailyProgressMinutes: s.dailyProgressMinutes + minutes }));
      },

      completeLesson: (lessonId) => {
        set((s) => {
          if (s.completedLessons.includes(lessonId)) return s;
          return { completedLessons: [...s.completedLessons, lessonId] };
        });
        get().checkStreak();
        get().updateQuestProgress('complete_lesson', 1);
      },

      recordSign: (signId, correct) => {
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
        if (correct) get().updateQuestProgress('sign_correct', 1);
      },

      checkStreak: () => {
        const newlyAwarded: number[] = [];
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
              return { lastPracticeDate: today, streakFreezes: s.streakFreezes - 1 };
            }
            newStreak = 1;
          }

          let goldBonus = 0;
          const newMilestones = [...s.streakMilestonesAwarded];
          for (const m of STREAK_MILESTONES) {
            if (newStreak >= m && !newMilestones.includes(m)) {
              newMilestones.push(m);
              goldBonus += MILESTONE_GOLD[m] ?? 0;
              newlyAwarded.push(m);
            }
          }

          return {
            streak: newStreak,
            lastPracticeDate: today,
            streakMilestonesAwarded: newMilestones,
            gold: s.gold + goldBonus,
          };
        });
        get().updateQuestProgress('streak_days');
        return newlyAwarded;
      },

      reset: () => set(defaultProgress()),

      mergeProgress: (remote) => {
        set((local) => {
          const merged: Partial<UserProgress> = {};
          if ((remote.xp ?? 0) > local.xp) merged.xp = remote.xp;
          if ((remote.level ?? 1) > local.level) merged.level = remote.level;
          if ((remote.streak ?? 0) > local.streak) merged.streak = remote.streak;
          if (remote.completedLessons) {
            merged.completedLessons = Array.from(
              new Set([...local.completedLessons, ...remote.completedLessons])
            );
          }
          if (remote.signAccuracy) {
            const acc = { ...local.signAccuracy };
            for (const [id, rs] of Object.entries(remote.signAccuracy)) {
              const ls = local.signAccuracy[id];
              if (!ls || rs.lastAttempt > ls.lastAttempt) acc[id] = rs;
            }
            merged.signAccuracy = acc;
          }
          if (remote.lastPracticeDate) merged.lastPracticeDate = remote.lastPracticeDate;
          return merged;
        });
      },

      completeOnboarding: (level) => {
        const toUnlock = SKILL_UNLOCK_LESSONS[level];
        set((s) => ({
          onboardingComplete: true,
          skillLevel: level,
          completedLessons: Array.from(new Set([...s.completedLessons, ...toUnlock])),
        }));
      },

      refreshDailyQuests: () => {
        const today = todayStr();
        const s = get();
        if (s.questsLastReset === today && s.dailyQuests.length > 0) return;

        const fresh = generateQuestsForToday().map(q => {
          if (q.type === 'streak_days') {
            const prog = Math.min(s.streak, q.target);
            return { ...q, progress: prog, completed: prog >= q.target };
          }
          return q;
        });
        set({ dailyQuests: fresh, questsLastReset: today });
      },

      updateQuestProgress: (type, delta = 1) => {
        set((s) => {
          const updated = s.dailyQuests.map((q: Quest) => {
            if (q.type !== type || q.completed || q.claimed) return q;
            const newProgress = type === 'streak_days'
              ? Math.min(s.streak, q.target)
              : Math.min(q.progress + delta, q.target);
            return { ...q, progress: newProgress, completed: newProgress >= q.target };
          });
          return { dailyQuests: updated };
        });
      },

      claimQuest: (questId) => {
        set((s) => {
          const quest = s.dailyQuests.find((q: Quest) => q.id === questId);
          if (!quest || !quest.completed || quest.claimed) return s;
          const newXp = s.xp + quest.xpReward;
          return {
            dailyQuests: s.dailyQuests.map((q: Quest) =>
              q.id === questId ? { ...q, claimed: true } : q
            ),
            xp: newXp,
            level: Math.floor(newXp / 100) + 1,
            signs: s.signs + quest.signsReward,
          };
        });
      },

      recordPracticeSession: () => {
        get().updateQuestProgress('practice_session', 1);
      },
    }),
    { name: 'asl-game-progress' }
  )
);
