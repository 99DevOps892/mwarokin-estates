/**
 * STA Agent Dashboard — Frontend Module
 * Real-time CEO monitoring for the Agentic Orchestration Hub
 */
(function () {
  const cfg = window.MWAROKIN_CONFIG || {};
  const client = window.supabaseClient;

  if (!client) {
    console.error('[agent-dashboard] Supabase client not initialized');
    return;
  }

  const BRAIN_URL = `${cfg.supabaseUrl}/functions/v1/agent-brain`;
  const BRIEFING_URL = `${cfg.supabaseUrl}/functions/v1/ceo-briefing`;

  window.AgentDashboard = {
    /** Load full dashboard data */
    async load() {
      const [brainStatus, briefings] = await Promise.all([
        this.getBrainStatus(),
        this.getBriefings(),
      ]);
      return { brain: brainStatus, briefings };
    },

    /** Get agent brain status */
    async getBrainStatus() {
      try {
        const res = await fetch(BRAIN_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'status' }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },

    /** Orchestrate a task through the brain */
    async orchestrate(taskType, domain, input, priority) {
      try {
        const res = await fetch(BRAIN_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'orchestrate',
            task_type: taskType,
            domain: domain,
            input: input,
            priority: priority || 'normal',
          }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },

    /** Decompose a complex task into sub-tasks */
    async decompose(taskType, domain, input) {
      try {
        const res = await fetch(BRAIN_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'decompose',
            task_type: taskType,
            domain: domain,
            input: input,
          }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },

    /** Route a task to the best agent */
    async route(taskType, domain) {
      try {
        const res = await fetch(BRAIN_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'route', task_type: taskType, domain }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },

    /** Generate CEO daily briefing */
    async generateDailyBriefing() {
      try {
        const res = await fetch(BRIEFING_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'daily' }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },

    /** Get recent briefings */
    async getBriefings(limit) {
      try {
        const res = await fetch(BRIEFING_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'list', limit: limit || 5 }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },

    /** Subscribe to live agent events */
    subscribeToEvents(callback) {
      return client
        .channel('agent-events-live')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_events' }, (payload) => {
          callback(payload.new);
        })
        .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'agent_tasks' }, (payload) => {
          callback({ event_type: 'task.updated', ...payload.new });
        })
        .subscribe();
    },

    /** Subscribe to agent registry changes */
    subscribeToAgents(callback) {
      return client
        .channel('agent-registry-live')
        .on('postgres_changes', { event: '*', schema: 'public', table: 'agent_registry' }, (payload) => {
          callback(payload);
        })
        .subscribe();
    },

    /** Send alert to CEO */
    async sendAlert(title, message, severity) {
      try {
        const res = await fetch(BRIEFING_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'alert',
            title,
            message,
            severity: severity || 'medium',
          }),
        });
        return await res.json();
      } catch (e) {
        return { success: false, error: e.message };
      }
    },
  };
})();
