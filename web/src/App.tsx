import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { HomePage } from '@/pages/HomePage';
import { LessonPage } from '@/pages/LessonPage';
import { PracticePage } from '@/pages/PracticePage';
import { StoryPage } from '@/pages/StoryPage';
import { COFFEE_SHOP_STORY } from '@/data/stories';
import { useProgressSync } from '@/hooks/useProgressSync';

type Screen =
  | { type: 'home' }
  | { type: 'lesson'; lessonId: string }
  | { type: 'practice' }
  | { type: 'story'; storyId: string };

export default function App() {
  useProgressSync();
  const [screen, setScreen] = useState<Screen>({ type: 'home' });

  const goHome = () => setScreen({ type: 'home' });

  return (
    <AnimatePresence mode="wait">
      {screen.type === 'home' && (
        <HomePage
          key="home"
          onStartLesson={(id) => setScreen({ type: 'lesson', lessonId: id })}
          onStartPractice={() => setScreen({ type: 'practice' })}
          onStartStory={(id) => setScreen({ type: 'story', storyId: id })}
        />
      )}
      {screen.type === 'lesson' && (
        <LessonPage
          key={`lesson-${screen.lessonId}`}
          lessonId={screen.lessonId}
          onExit={goHome}
        />
      )}
      {screen.type === 'practice' && (
        <PracticePage key="practice" onExit={goHome} />
      )}
      {screen.type === 'story' && (
        <StoryPage
          key={`story-${screen.storyId}`}
          story={COFFEE_SHOP_STORY}
          onExit={goHome}
        />
      )}
    </AnimatePresence>
  );
}
