import { motion } from 'framer-motion';
import type { ParamScore } from '@/engine/verifier';
import { paramCleared } from '@/engine/verifier';

const FRIENDLY_NAMES: Record<string, string> = {
  handshape_dominant: 'Hand shape',
  handshape_nondominant: 'Support hand',
  location: 'Position',
  movement: 'Movement',
  orientation: 'Palm direction',
};

const PARAM_HINTS: Record<string, Record<string, string>> = {
  movement: {
    circular: 'Circle your hand',
    linear: 'Move your hand forward',
    repeated: 'Repeat the motion',
    converge: 'Bring hands together',
  },
};

interface Props {
  params: ParamScore[];
  movementKind?: string;
}

export function ParameterChecklist({ params, movementKind }: Props) {
  return (
    <div className="space-y-2">
      {params.map((param, i) => {
        const cleared = paramCleared(param);
        const pct = Math.min(100, Math.round((param.score / Math.max(param.threshold, 0.01)) * 100));

        return (
          <motion.div
            key={param.name}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 border ${
              cleared
                ? 'bg-z-green/10 border-z-green/30'
                : param.required
                  ? 'bg-z-red/8 border-z-red/20'
                  : 'bg-z-surface/30 border-white/5'
            }`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <div className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
              cleared
                ? 'bg-z-green text-white'
                : param.required
                  ? 'bg-z-red/30 text-z-red'
                  : 'bg-z-gray-500/30 text-z-gray-400'
            }`}>
              {cleared ? '✓' : param.required ? '✗' : '—'}
            </div>

            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold ${
                cleared ? 'text-z-green' : param.required ? 'text-z-gray-100' : 'text-z-gray-400'
              }`}>
                {FRIENDLY_NAMES[param.name] || param.name}
              </p>
              {!cleared && param.required && param.name === 'movement' && movementKind && (
                <p className="text-xs text-z-gray-300 mt-0.5">
                  {PARAM_HINTS.movement?.[movementKind] || 'Keep moving!'}
                </p>
              )}
            </div>

            <div className="w-20 h-2 bg-z-surface rounded-full overflow-hidden">
              <motion.div
                className={`h-full rounded-full ${
                  cleared ? 'bg-z-green' : param.required ? 'bg-z-purple-light' : 'bg-z-gray-400'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>

            <span className={`text-xs font-mono w-8 text-right ${
              cleared ? 'text-z-green' : 'text-z-gray-400'
            }`}>
              {Math.round(param.score * 100)}%
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}
