# Implementation Plan: AI Agent Facial Expressions & Highlighting

This document outlines the architecture, components, and task split for implementing human-like facial animations and UI highlighting for active/inactive AI agents.

## Goal Description
The objective is to replace the current geometric orb representations of agents with human-like faces capable of facial expressions and lip-syncing when speaking. Furthermore, the UI will be updated so that all agents are visible on-screen, but only the active agent is highlighted prominently, while inactive agents appear busy or idle in the background.

## User Review Required

> [!IMPORTANT]
> **Animation Asset Choice**: We need to decide on the format for the faces before development begins. 
> - **Option 1: Lottie / Rive (Recommended)**: Best for smooth, lightweight 2D vector animations (idle, speaking, busy states).
> - **Option 2: Sprite Sheets / Video Loops**: Easiest to implement if using AI-generated video avatars.
> - **Option 3: 3D (Three.js / ReadyPlayerMe)**: Most complex, but provides real-time viseme-based lip syncing.
> 
> *Please confirm which asset approach you prefer so Person B can prepare the right dependencies.*

## Proposed Division of Labor

To ensure parallel development without merge conflicts, the work is divided into two distinct scopes: **State/Layout (Person A)** and **Component/Animation (Person B)**.

---

### Person A: State Orchestration & Layout
*Focus: Managing the macro-level UI layout and tracking the global state of the agents (who is active, who is speaking).*

#### [MODIFY] `frontend/src/components/chat/AssistantPresence.jsx` (or main view)
- Refactor to display **all** agents simultaneously instead of just one.
- Implement the "Spotlight" layout logic:
  - The `activeAgent` is rendered prominently (e.g., larger size, central position, full opacity).
  - Non-active agents are rendered in a secondary position (e.g., a side panel or background row) with reduced scale and opacity.
- Pass the appropriate `state` prop (`speaking`, `idle`, or `busy`) down to each agent's face component based on global state.

#### [MODIFY] `frontend/src/components/chat/ExpertTeamPanel.jsx`
- Update the switching logic to trigger the layout transition when a user manually clicks to switch the active agent.

#### State Management
- Track `allAgents` (list of available agents in the session).
- Track `activeAgentId` and `speakingStatus` (hooking into voice/TTS events so the system knows exactly when the active agent is producing audio).

---

### Person B: Visuals, Components, & Animation
*Focus: Creating the micro-level UI, specifically the human-like faces and their animation states.*

#### [NEW] `frontend/src/components/chat/AgentFace.jsx`
- Create a new component to replace `AgentOrb.jsx`.
- **Props**: `agentId`, `state` (speaking, idle, busy), `isHighlighted` (boolean).
- **Animation Logic**: 
  - `speaking`: Triggers the talking animation/lip-sync loop.
  - `idle`: Default active state (subtle breathing, occasional blinking).
  - `busy`: Inactive state (looking down, typing, or reading).
- Apply dynamic CSS transitions for scaling and glowing when `isHighlighted` changes from false to true.

#### [MODIFY] `frontend/src/components/chat/AgentOrb.jsx` (Optional)
- Either deprecate this file or keep it as a fallback for agents that don't have facial assets yet.

#### [NEW] `frontend/src/assets/animations/`
- Set up the folder structure and import the chosen animation assets (Lottie JSONs, Rive files, or MP4s) for the different agent states.

## Verification Plan

### Manual Verification
1. **State Switching**: Click between different agents. Verify that the newly selected agent transitions smoothly to the "Spotlight" and the previous agent shrinks to the "busy" background state.
2. **Speaking Trigger**: Trigger an AI response. Verify that the highlighted agent transitions from `idle` to `speaking`, and their mouth movements match the audio duration.
3. **No Clashes Check**: Both developers should be able to merge their PRs. Person A's layout will seamlessly consume Person B's `AgentFace` component since the prop contract (`state`, `isHighlighted`) was agreed upon beforehand.
