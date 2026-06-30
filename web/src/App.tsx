import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { HomePage } from '@/pages/HomePage';
import { LessonPage } from '@/pages/LessonPage';
import { PracticePage } from '@/pages/PracticePage';
import { StoryPage } from '@/pages/StoryPage';
import { OnboardingFlow } from '@/components/onboarding/OnboardingFlow';
import { COFFEE_SHOP_STORY } from '@/data/stories';
import { useProgressSync } from '@/hooks/useProgressSync';
import { useUserStore } from '@/stores/useUserStore';

type Screen =
  | { type: 'home' }
  | { type: 'onboarding' }
  | { type: 'lesson'; lessonId: string }
  | { type: 'practice'; filterSignIds?: string[]; autoStart?: boolean }
  | { type: 'story'; storyId: string };

export default function App() {
  useProgressSync();
  const { onboardingComplete } = useUserStore();
  const [screen, setScreen] = useState<Screen>(
    onboardingComplete ? { type: 'home' } : { type: 'onboarding' }
  );

  const goHome = () => setScreen({ type: 'home' });

  return (
    <AnimatePresence mode="wait">
      {screen.type === 'onboarding' && (
        <OnboardingFlow key="onboarding" onComplete={goHome} />
      )}

      {screen.type === 'home' && (
        <HomePage
          key="home"
          onStartLesson={(id) => setScreen({ type: 'lesson', lessonId: id })}
          onStartPractice={(opts) => setScreen({ type: 'practice', ...opts })}
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
        <PracticePage
          key="practice"
          onExit={goHome}
          filterSignIds={screen.filterSignIds}
          autoStartExpressive={screen.autoStart}
        />
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
