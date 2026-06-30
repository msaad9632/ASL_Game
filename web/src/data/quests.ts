import type { Quest, QuestType } from '@/types/user';

interface QuestTemplate {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  xpReward: number;
  signsReward: number;
  target: number;
  type: QuestType;
}

const EASY: QuestTemplate[] = [
  { id: 'e1', title: 'First Signs', description: 'Sign any word correctly 5 times', difficulty: 'easy', xpReward: 20, signsReward: 30, target: 5, type: 'sign_correct' },
  { id: 'e2', title: 'Keep Warm', description: 'Complete a review session', difficulty: 'easy', xpReward: 15, signsReward: 25, target: 1, type: 'practice_session' },
  { id: 'e3', title: 'Daily Drill', description: 'Sign any word correctly 8 times', difficulty: 'easy', xpReward: 25, signsReward: 35, target: 8, type: 'sign_correct' },
  { id: 'e4', title: 'Node Complete', description: 'Complete any lesson node', difficulty: 'easy', xpReward: 30, signsReward: 40, target: 1, type: 'complete_lesson' },
  { id: 'e5', title: 'Warm Up', description: 'Sign 3 words correctly', difficulty: 'easy', xpReward: 15, signsReward: 20, target: 3, type: 'sign_correct' },
  { id: 'e6', title: 'Consistent', description: 'Practice 2 days in a row', difficulty: 'easy', xpReward: 20, signsReward: 30, target: 2, type: 'streak_days' },
];

const MEDIUM: QuestTemplate[] = [
  { id: 'm1', title: 'On a Roll', description: 'Sign 15 words correctly', difficulty: 'medium', xpReward: 40, signsReward: 60, target: 15, type: 'sign_correct' },
  { id: 'm2', title: 'Double Session', description: 'Complete 2 review sessions', difficulty: 'medium', xpReward: 35, signsReward: 55, target: 2, type: 'practice_session' },
  { id: 'm3', title: 'Lesson Spree', description: 'Complete 2 lesson nodes', difficulty: 'medium', xpReward: 50, signsReward: 65, target: 2, type: 'complete_lesson' },
  { id: 'm4', title: 'Streak Builder', description: 'Practice 3 days in a row', difficulty: 'medium', xpReward: 45, signsReward: 60, target: 3, type: 'streak_days' },
  { id: 'm5', title: 'Vocabulary Boost', description: 'Sign 20 words correctly', difficulty: 'medium', xpReward: 40, signsReward: 60, target: 20, type: 'sign_correct' },
];

const HARD: QuestTemplate[] = [
  { id: 'h1', title: 'Sign Master', description: 'Sign 30 words correctly', difficulty: 'hard', xpReward: 80, signsReward: 120, target: 30, type: 'sign_correct' },
  { id: 'h2', title: 'Lesson Champion', description: 'Complete 3 lesson nodes', difficulty: 'hard', xpReward: 90, signsReward: 130, target: 3, type: 'complete_lesson' },
  { id: 'h3', title: 'Dedicated', description: 'Practice 5 days in a row', difficulty: 'hard', xpReward: 100, signsReward: 150, target: 5, type: 'streak_days' },
  { id: 'h4', title: 'Marathon Session', description: 'Complete 4 review sessions', difficulty: 'hard', xpReward: 85, signsReward: 125, target: 4, type: 'practice_session' },
  { id: 'h5', title: 'Word Wizard', description: 'Sign 40 words correctly', difficulty: 'hard', xpReward: 100, signsReward: 140, target: 40, type: 'sign_correct' },
];

function dayOfYear(): number {
  const now = new Date();
  return Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86400000);
}

export function generateQuestsForToday(): Quest[] {
  const d = dayOfYear();
  return [
    EASY[d % EASY.length],
    MEDIUM[(d + 1) % MEDIUM.length],
    HARD[(d + 2) % HARD.length],
  ].map(t => ({ ...t, progress: 0, completed: false, claimed: false }));
}
