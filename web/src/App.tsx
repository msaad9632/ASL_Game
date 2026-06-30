import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { HomePage } from '@/pages/HomePage';
import { LessonPage } from '@/pages/LessonPage';
import { PracticePage } from '@/pages/PracticePage';
import { StoryPage } from '@/pages/StoryPage';
import { SpeedChallengePage } from '@/pages/SpeedChallengePage';
import { ShopPage } from '@/pages/ShopPage';
import { FriendsPage } from '@/pages/FriendsPage';
import { MultiplayerPage } from '@/pages/MultiplayerPage';
import { OnboardingFlow } from '@/components/onboarding/OnboardingFlow';
import { STORIES } from '@/data/stories';
import { useProgressSync } from '@/hooks/useProgressSync';
import { useUserStore } from '@/stores/useUserStore';

type Screen =
  | { type: 'home' }
  | { type: 'onboarding' }
  | { type: 'lesson'; lessonId: string }
  | { type: 'practice'; filterSignIds?: string[]; autoStart?: boolean }
  | { type: 'story'; storyId: string }
  | { type: 'speed' }
  | { type: 'shop' }
  | { type: 'friends' }
  | { type: 'multiplayer' };

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
          onStartSpeed={() => setScreen({ type: 'speed' })}
          onOpenShop={() => setScreen({ type: 'shop' })}
          onOpenFriends={() => setScreen({ type: 'friends' })}
          onStartMultiplayer={() => setScreen({ type: 'multiplayer' })}
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

      {screen.type === 'story' && (() => {
        const story = STORIES.find((s) => s.id === screen.storyId);
        if (!story) return null;
        return <StoryPage key={`story-${screen.storyId}`} story={story} onExit={goHome} />;
      })()}

      {screen.type === 'speed' && (
        <SpeedChallengePage key="speed" onExit={goHome} />
      )}

      {screen.type === 'shop' && (
        <ShopPage key="shop" onExit={goHome} />
      )}

      {screen.type === 'friends' && (
        <FriendsPage key="friends" onExit={goHome} />
      )}

      {screen.type === 'multiplayer' && (
        <MultiplayerPage key="multiplayer" onExit={goHome} />
      )}
    </AnimatePresence>
  );
}
