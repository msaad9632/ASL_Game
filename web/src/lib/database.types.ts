export type Json = string | number | boolean | null | { [key: string]: Json } | Json[];

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: { id: string; username: string; created_at: string };
        Insert: { id: string; username: string };
        Update: { username?: string };
      };
      user_progress: {
        Row: {
          user_id: string;
          xp: number;
          level: number;
          streak: number;
          longest_streak: number;
          last_practice_date: string | null;
          completed_lessons: string[];
          sign_accuracy: Json;
          updated_at: string;
        };
        Insert: Partial<Database['public']['Tables']['user_progress']['Row']> & { user_id: string };
        Update: Partial<Database['public']['Tables']['user_progress']['Row']>;
      };
      sign_attempts: {
        Row: { id: number; user_id: string; sign_id: string; passed: boolean; attempted_at: string };
        Insert: { user_id: string; sign_id: string; passed: boolean };
        Update: never;
      };
      friendships: {
        Row: { requester_id: string; addressee_id: string; status: 'pending' | 'accepted'; created_at: string };
        Insert: { requester_id: string; addressee_id: string };
        Update: { status: 'pending' | 'accepted' };
      };
    };
    Views: {
      weekly_leaderboard: {
        Row: { id: string; username: string; signs_this_week: number; total_xp: number; streak: number };
      };
    };
    Functions: Record<string, never>;
    Enums: Record<string, never>;
  };
}
