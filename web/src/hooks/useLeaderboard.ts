import { useEffect, useState } from 'react';
import { supabase, supabaseReady } from '@/lib/supabase';
import type { Database } from '@/lib/database.types';

type LeaderboardRow = Database['public']['Views']['weekly_leaderboard']['Row'];

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
        setRows(data ?? []);
        setLoading(false);
      });
  }, []);

  return { rows, loading };
}
