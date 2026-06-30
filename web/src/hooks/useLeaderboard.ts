import { useEffect, useState } from 'react';
import { supabase, supabaseReady } from '@/lib/supabase';

export interface LeaderboardRow {
  id: string;
  username: string;
  signs_this_week: number;
  total_xp: number;
  streak: number;
}

export function useLeaderboard() {
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!supabaseReady) return;
    setLoading(true);
    supabase
      .from('weekly_leaderboard')
      .select('*')
      .limit(20)
      .then(({ data }) => {
        setRows((data as unknown as LeaderboardRow[]) ?? []);
        setLoading(false);
      });
  }, []);

  return { rows, loading };
}
