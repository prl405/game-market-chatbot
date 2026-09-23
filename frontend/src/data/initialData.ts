import type { Session } from '../types';

export const INITIAL_SESSIONS: Session[] = [
  {
    id: 'challenge-01',
    title: 'CHALLENGE_01.EXE',
    sessionCode: '#889-MARKET-VAL',
    bannerTitle: 'VIDEO GAME MARKET INTEL // Q3 2024',
    bannerSubtitle:
      'Autonomous analysis active. Cross-referencing global Steam metrics, console telemetry, and engine distribution vectors.',
    createdAt: '2024-09-22T10:40:00Z',
    outline: [
      { id: 'intro', title: 'Intro & Setup', messageId: 'msg-user-1' },
      { id: 'rev-comp', title: 'Global Revenue Comparison', messageId: 'msg-bot-1' },
      { id: 'engine-share', title: 'Indie Engine Market Share', messageId: 'msg-bot-1' },
      { id: 'level-1', title: 'Level 1: Mechanics' },
      { id: 'boss-tactics', title: 'Boss Fight Tactics' },
    ],
    messages: [
      {
        id: 'msg-user-1',
        role: 'user',
        timestamp: '10:42 AM',
        senderTitle: 'USER // 10:42 AM',
        content:
          'Give me the latest revenue breakdown comparing RPG vs FPS global markets, and list the current engine market share for indie developers.',
        status: 'idle',
      },
      {
        id: 'msg-bot-1',
        role: 'assistant',
        timestamp: '10:42 AM',
        senderTitle: 'PIXELBOT 64 // MARKET AI',
        content:
          'Query acknowledged. Initializing global telemetry pull for Q3. The macro landscape shows shifting dominance between high-retention live-service RPGs and perennial blockbuster FPS titles.\n\nGodot has overtaken Unity in indie project initiations following recent licensing shifts, though Unreal retains high-end visual fidelity dominance. Would you like a deeper breakdown of monetisation methods for RPG microtransactions?',
        status: 'idle',
      },
    ],
  },
  {
    id: 'high-score-run',
    title: 'HIGH_SCORE_RUN_01.EXE',
    sessionCode: '#102-HIGHSCORE-01',
    bannerTitle: 'SPEEDRUN & COMBO ANALYSIS // ARCADE SECTOR 7',
    bannerSubtitle:
      'Frame data processing engaged. Tracking input latency, animation cancellation frames, and multiplier bonuses.',
    createdAt: '2024-09-22T09:15:00Z',
    outline: [
      { id: 'run-intro', title: 'Route Optimization' },
      { id: 'run-splits', title: 'Sector 3 Split Time' },
      { id: 'run-bonus', title: 'Combo Multiplier Strat' },
    ],
    messages: [
      {
        id: 'msg-run-u1',
        role: 'user',
        timestamp: '09:15 AM',
        senderTitle: 'USER // 09:15 AM',
        content: 'How do I optimize the frame input window on Sector 3 ledge-cancels?',
        status: 'idle',
      },
      {
        id: 'msg-run-b1',
        role: 'assistant',
        timestamp: '09:16 AM',
        senderTitle: 'PIXELBOT 64 // RUN ADVISOR',
        content:
          'Buffer your dash input exactly at frame 14 before ground collision. This cancels the standard recovery animation by 8 frames and maintains forward horizontal velocity.',
        status: 'idle',
      },
    ],
  },
  {
    id: 'boss-battle',
    title: 'BOSS_BATTLE_STRATEGY.EXE',
    sessionCode: '#404-BOSS-RAID',
    bannerTitle: 'BOSS RAID TACTICAL INTEL // TITAN MECH',
    bannerSubtitle:
      'Vulnerability scanning complete. Weakpoint heat signature detected on ventral cooling port.',
    createdAt: '2024-09-21T18:30:00Z',
    outline: [
      { id: 'boss-p1', title: 'Phase 1: Dual Beam Sweep' },
      { id: 'boss-p2', title: 'Phase 2: Missile Barrage' },
      { id: 'boss-p3', title: 'Phase 3: Enrage Protocol' },
    ],
    messages: [
      {
        id: 'msg-boss-u1',
        role: 'user',
        timestamp: '06:32 PM',
        senderTitle: 'USER // 06:32 PM',
        content: 'What is the optimal DPS rotation against Titan Mech in Phase 2?',
        status: 'idle',
      },
      {
        id: 'msg-boss-b1',
        role: 'assistant',
        timestamp: '06:33 PM',
        senderTitle: 'PIXELBOT 64 // COMBAT TACTICIAN',
        content:
          'During Phase 2, deploy Plasma Railgun charged shots when the core vents steam. Keep moving laterally to evade heat-seeking cluster missiles.',
        status: 'idle',
      },
    ],
  },
];
