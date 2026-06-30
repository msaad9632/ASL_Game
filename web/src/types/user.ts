export type QuestType = 'sign_correct' | 'complete_lesson' | 'practice_session' | 'streak_days';

export interface Quest {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  xpReward: number;
  signsReward: number;
  progress: number;
  target: number;
  completed: boolean;
  claimed: boolean;
  type: QuestType;
}

export type SkillLevel = 'beginner' | 'intermediate' | 'advanced';

export interface UserProgress {
  xp: number;
  level: number;
  streak: number;
  lastPracticeDate: string | null;
  streakFreezes: number;
  dailyGoalMinutes: number;
  dailyProgressMinutes: number;
  completedLessons: string[];
  signAccuracy: Record<string, SignStats>;
  achievements: string[];
  onboardingComplete: boolean;
  skillLevel: SkillLevel;
  dailyQuests: Quest[];
  questsLastReset: string;
  streakMilestonesAwarded: number[];
  signs: number;
  gold: number;
}

export interface SignStats {
  attempts: number;
  successes: number;
  lastAttempt: number;
  nextReviewAt: number;
  interval: number;
  easeFactor: number;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  unlockedAt?: number;
}
