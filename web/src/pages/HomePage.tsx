import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { TopBar } from '@/components/shared/TopBar';
import { StreakCard } from '@/components/home/StreakCard';
import { LessonTree } from '@/components/home/LessonTree';
import { BottomNav, type Tab } from '@/components/home/BottomNav';
import { PracticeTab } from '@/components/home/PracticeTab';
import { ProfileTab } from '@/components/home/ProfileTab';
import { AlphabetTab } from '@/components/home/AlphabetTab';
import { DailyQuestsCard } from '@/components/home/DailyQuestsCard';
import { useUserStore } from '@/stores/useUserStore';

interface Props {
  onStartLesson: (id: string) => void;
  onStartPractice: (opts?: { filterSignIds?: string[]; autoStart?: boolean }) => void;
  onStartStory: (id: string) => void;
}

export function HomePage({ onStartLesson, onStartPractice, onStartStory }: Props) {
  const [tab, setTab] = useState<Tab>('learn');
  const { refreshDailyQuests } = useUserStore();

  useEffect(() => {
    refreshDailyQuests();
  }, [refreshDailyQuests]);

  return (
    <div className="min-h-screen bg-z-bg">
      <TopBar />

      <div className="max-w-lg mx-auto px-4 pt-4">
        <AnimatePresence mode="wait">
          {tab === 'learn' && (
            <motion.div
              key="learn"
              initial={{ opacity: 0, x: -22, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 22, scale: 0.97 }}
              transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <StreakCard />
              <DailyQuestsCard />
              <LessonTree onSelectLesson={(id) => {
                if (id === 'coffee-story') {
                  onStartStory(id);
                } else {
                  onStartLesson(id);
                }
              }} />
            </motion.div>
          )}

          {tab === 'review' && (
            <motion.div
              key="review"
              initial={{ opacity: 0, x: 22, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -22, scale: 0.97 }}
              transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <PracticeTab
                onStartPractice={() => onStartPractice()}
                onStartWeakPractice={(ids) => onStartPractice({ filterSignIds: ids, autoStart: true })}
                onStartStory={() => onStartStory('coffee-story')}
              />
            </motion.div>
          )}

          {tab === 'alphabet' && (
            <motion.div
              key="alphabet"
              initial={{ opacity: 0, x: 22, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -22, scale: 0.97 }}
              transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <AlphabetTab
                onStartLettersPractice={(ids) => onStartPractice({ filterSignIds: ids })}
              />
            </motion.div>
          )}

          {tab === 'profile' && (
            <motion.div
              key="profile"
              initial={{ opacity: 0, x: 22, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -22, scale: 0.97 }}
              transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <ProfileTab />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <BottomNav active={tab} onChange={setTab} />
    </div>
  );
}
