import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '@/stores/useUserStore';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabase';

interface FriendProfile {
  id: string;
  username: string;
  display_name: string | null;
  xp: number;
  streak: number;
}

interface Props {
  onExit: () => void;
}

export function FriendsPage({ onExit }: Props) {
  const { user } = useAuth();
  const { friends, addFriend, removeFriend } = useUserStore();

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<FriendProfile[]>([]);
  const [friendProfiles, setFriendProfiles] = useState<FriendProfile[]>([]);
  const [searching, setSearching] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [loadedFriends, setLoadedFriends] = useState(false);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const { data } = await supabase
        .from('profiles')
        .select('id, username, display_name, xp, streak')
        .ilike('username', `%${query.trim()}%`)
        .neq('id', user?.id ?? '')
        .limit(10);
      setResults((data as FriendProfile[]) ?? []);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const loadFriendProfiles = async () => {
    if (loadedFriends || friends.length === 0) { setLoadedFriends(true); return; }
    try {
      const { data } = await supabase
        .from('profiles')
        .select('id, username, display_name, xp, streak')
        .in('id', friends);
      setFriendProfiles((data as FriendProfile[]) ?? []);
    } catch { /* empty */ }
    setLoadedFriends(true);
  };

  useEffect(() => { loadFriendProfiles(); }, []);

  const handleAdd = async (profile: FriendProfile) => {
    addFriend(profile.id);
    if (user) {
      await supabase.from('friendships').upsert({
        user_id: user.id,
        friend_id: profile.id,
      });
    }
    showToast(`Added ${profile.username} 🤝`);
    setFriendProfiles((p) => [...p.filter((f) => f.id !== profile.id), profile]);
  };

  const handleRemove = async (profileId: string) => {
    removeFriend(profileId);
    if (user) {
      await supabase.from('friendships').delete()
        .eq('user_id', user.id).eq('friend_id', profileId);
    }
    setFriendProfiles((p) => p.filter((f) => f.id !== profileId));
    showToast('Friend removed');
  };

  return (
    <div className="min-h-screen bg-z-bg flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-z-purple-deep/40">
        <button onClick={onExit} className="w-8 h-8 flex items-center justify-center text-z-gray-400 hover:text-white transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="font-bold text-lg flex-1">Friends</h1>
        <span className="text-sm text-z-gray-400">{friends.length} friends</span>
      </div>

      <div className="flex-1 max-w-lg mx-auto w-full px-4 pt-4 pb-24">
        {/* Search */}
        <div className="flex gap-2 mb-5">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search by username…"
            className="flex-1 bg-z-card border border-white/10 rounded-2xl px-4 py-2.5 text-sm focus:outline-none focus:border-z-purple/60 placeholder:text-z-gray-500"
          />
          <motion.button
            onClick={handleSearch}
            disabled={searching}
            className="px-4 py-2.5 bg-z-purple rounded-2xl text-sm font-bold text-white disabled:opacity-50"
            whileTap={{ scale: 0.96 }}
          >
            {searching ? '…' : 'Search'}
          </motion.button>
        </div>

        {/* Search results */}
        <AnimatePresence>
          {results.length > 0 && (
            <motion.div className="mb-5" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
              <p className="text-xs text-z-gray-400 uppercase tracking-widest mb-2">Results</p>
              <div className="space-y-2">
                {results.map((p) => {
                  const isFriend = friends.includes(p.id);
                  return (
                    <div key={p.id} className="flex items-center gap-3 bg-z-card border border-white/8 rounded-2xl px-4 py-3">
                      <div className="w-10 h-10 rounded-xl bg-z-purple/20 flex items-center justify-center text-xl">🤟</div>
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm truncate">{p.display_name ?? p.username}</p>
                        <p className="text-xs text-z-gray-400">@{p.username} · {p.xp} XP</p>
                      </div>
                      <motion.button
                        onClick={() => isFriend ? handleRemove(p.id) : handleAdd(p)}
                        className={`text-xs px-3 py-1.5 rounded-xl font-bold ${
                          isFriend ? 'border border-white/15 text-z-gray-300' : 'bg-z-purple text-white'
                        }`}
                        whileTap={{ scale: 0.96 }}
                      >
                        {isFriend ? 'Friends ✓' : '+ Add'}
                      </motion.button>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Friend list */}
        <div>
          <p className="text-xs text-z-gray-400 uppercase tracking-widest mb-2">Your Friends</p>
          {friends.length === 0 ? (
            <div className="text-center py-10">
              <p className="text-4xl mb-3">🤝</p>
              <p className="text-z-gray-300 text-sm">No friends yet</p>
              <p className="text-z-gray-500 text-xs mt-1">Search for users above to add them</p>
            </div>
          ) : (
            <div className="space-y-2">
              {friendProfiles.map((p) => (
                <motion.div
                  key={p.id}
                  className="flex items-center gap-3 bg-z-card border border-white/8 rounded-2xl px-4 py-3"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div className="w-10 h-10 rounded-xl bg-z-purple/20 flex items-center justify-center text-xl">🤟</div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm truncate">{p.display_name ?? p.username}</p>
                    <div className="flex items-center gap-2 text-xs text-z-gray-400 mt-0.5">
                      <span>🔥 {p.streak}</span>
                      <span>·</span>
                      <span>⭐ {p.xp} XP</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(p.id)}
                    className="w-7 h-7 flex items-center justify-center text-z-gray-500 hover:text-z-red transition-colors"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                </motion.div>
              ))}
              {/* Show IDs for friends whose profiles haven't loaded */}
              {friends.filter((id) => !friendProfiles.some((p) => p.id === id)).map((id) => (
                <div key={id} className="flex items-center gap-3 bg-z-card border border-white/8 rounded-2xl px-4 py-3 opacity-60">
                  <div className="w-10 h-10 rounded-xl bg-z-surface flex items-center justify-center text-xl">🤟</div>
                  <div className="flex-1">
                    <div className="h-3 w-24 bg-z-surface rounded animate-pulse" />
                    <div className="h-2 w-16 bg-z-surface rounded animate-pulse mt-1.5" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-z-card border border-white/10 rounded-2xl px-5 py-3 text-sm font-semibold shadow-xl z-50 whitespace-nowrap"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
