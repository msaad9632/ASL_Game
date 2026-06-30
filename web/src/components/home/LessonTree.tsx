import { motion } from 'framer-motion';
import { LESSON_UNITS } from '@/data/lessons';
import { useUserStore } from '@/stores/useUserStore';
import { LessonNode } from './LessonNode';
import type { LessonNodeStatus } from '@/types/lesson';

interface Props {
  onSelectLesson: (id: string) => void;
}

export function LessonTree({ onSelectLesson }: Props) {
  const { completedLessons } = useUserStore();

  function getNodeStatus(nodeId: string, unitIdx: number, nodeIdx: number): LessonNodeStatus {
    if (completedLessons.includes(nodeId)) return 'completed';

    for (let u = 0; u < LESSON_UNITS.length; u++) {
      for (let n = 0; n < LESSON_UNITS[u].nodes.length; n++) {
        const id = LESSON_UNITS[u].nodes[n].id;
        if (!completedLessons.includes(id)) {
          return u === unitIdx && n === nodeIdx ? 'current' : 'locked';
        }
      }
    }
    return 'locked';
  }

  return (
    <div className="pb-32">
      {LESSON_UNITS.map((unit, unitIdx) => (
        <div key={unit.id} className="mb-10">
          {/* Unit header */}
          <motion.div
            className="rounded-2xl p-4 mb-6 mx-1 border border-white/5 cursor-default"
            style={{
              background: `linear-gradient(135deg, ${unit.color}15, ${unit.color}08)`,
            }}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: unitIdx * 0.12 }}
            whileHover={{
              scale: 1.015,
              borderColor: `${unit.color}30`,
              boxShadow: `0 4px 20px ${unit.color}18`,
              transition: { duration: 0.2 },
            }}
          >
            <h2 className="font-bold text-base tracking-wide" style={{ color: unit.color }}>
              {unit.title}
            </h2>
            <p className="text-xs text-z-gray-300 mt-0.5">{unit.description}</p>
          </motion.div>

          {/* Lesson nodes */}
          <div className="flex flex-col items-center gap-7">
            {unit.nodes.map((node, nodeIdx) => {
              const status = getNodeStatus(node.id, unitIdx, nodeIdx);
              return (
                <LessonNode
                  key={node.id}
                  node={{ ...node, status }}
                  index={unitIdx * 10 + nodeIdx}
                  unitColor={unit.color}
                  onSelect={onSelectLesson}
                />
              );
            })}
          </div>

          {unitIdx < LESSON_UNITS.length - 1 && (
            <div className="flex justify-center my-5">
              <div className="w-px h-8 bg-z-purple-deep/60" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
