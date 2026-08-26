import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json, error, preflight } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const OLLAMA_URL = Deno.env.get("OLLAMA_URL") || "http://127.0.0.1:11434";

interface BrainRequest {
  action: "orchestrate" | "decompose" | "route" | "execute" | "status";
  task_type?: string;
  domain?: string;
  input?: Record<string, unknown>;
  priority?: string;
  agent_id?: string;
  task_id?: string;
}

serve(async (req: Request) => {
  if (preflight(req)) return preflight(req);

  try {
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body: BrainRequest = await req.json();
    const { action } = body;

    switch (action) {
      case "orchestrate": {
        const taskId = `BRN-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

        // 1. Find best agent for the task
        const { data: agents } = await supabase
          .from("agent_registry")
          .select("*")
          .eq("status", "idle")
          .eq("domain", body.domain || "sta")
          .order("error_rate", { ascending: true })
          .order("avg_response_time_ms", { ascending: true })
          .limit(1);

        if (!agents || agents.length === 0) {
          return json({ success: false, error: "No available agents", taskId }, 503);
        }

        const agent = agents[0];

        // 2. Create task record
        const { data: task } = await supabase
          .from("agent_tasks")
          .insert({
            task_id: taskId,
            assigned_agent_id: agent.agent_id,
            domain: body.domain || "sta",
            task_type: body.task_type || "general",
            priority: body.priority || "normal",
            input: body.input || {},
            status: "assigned",
          })
          .select()
          .single();

        // 3. Update agent status
        await supabase
          .from("agent_registry")
          .update({ status: "busy", current_task_count: agent.current_task_count + 1 })
          .eq("agent_id", agent.agent_id);

        // 4. Execute task via Ollama or edge function
        const result = await executeTask(supabase, agent, body);

        // 5. Update task with result
        await supabase
          .from("agent_tasks")
          .update({
            status: result.success ? "completed" : "failed",
            output: result.output,
            error_message: result.error,
            completed_at: new Date().toISOString(),
            tokens_used: result.tokens || 0,
          })
          .eq("id", task.id);

        // 6. Update agent stats
        await supabase
          .from("agent_registry")
          .update({
            status: "idle",
            current_task_count: Math.max(0, agent.current_task_count - 1),
            total_tasks_completed: agent.total_tasks_completed + 1,
            last_heartbeat: new Date().toISOString(),
          })
          .eq("agent_id", agent.agent_id);

        // 7. Emit completion event
        await supabase.from("agent_events").insert({
          event_type: "task.completed",
          source_agent_id: agent.agent_id,
          target_agent_id: body.agent_id,
          domain: body.domain,
          payload: { taskId, result: result.output },
        });

        return json({ success: true, taskId, agent: agent.agent_id, result: result.output });
      }

      case "decompose": {
        const taskId = `DCP-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

        // Use syllogistic reasoning to decompose complex task
        const prompt = `Decompose this task into sub-tasks. Return JSON array of {task_type, domain, input, priority}.
Task: ${JSON.stringify(body.input)}
Domain: ${body.domain || "sta"}`;

        const ollamaRes = await fetch(`${OLLAMA_URL}/api/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: "qwen3:8b", prompt, stream: false }),
        });

        const ollamaData = await ollamaRes.json();
        let subtasks;
        try {
          const jsonMatch = ollamaData.response.match(/\[[\s\S]*\]/);
          subtasks = jsonMatch ? JSON.parse(jsonMatch[0]) : [{ task_type: body.task_type, domain: body.domain, input: body.input, priority: "normal" }];
        } catch {
          subtasks = [{ task_type: body.task_type, domain: body.domain, input: body.input, priority: "normal" }];
        }

        // Create sub-tasks
        const createdTasks = [];
        for (const st of subtasks) {
          const subtaskId = `${taskId}-${createdTasks.length + 1}`;
          const { data: subtask } = await supabase
            .from("agent_tasks")
            .insert({
              task_id: subtaskId,
              parent_task_id: null,
              orchestrator_id: "sta-hub-001",
              domain: st.domain || body.domain || "sta",
              task_type: st.task_type,
              priority: st.priority || "normal",
              input: st.input || {},
              status: "queued",
            })
            .select()
            .single();
          createdTasks.push(subtask);
        }

        return json({ success: true, taskId, subtasks: createdTasks });
      }

      case "route": {
        // Find best agent based on skills and availability
        const { data: agents } = await supabase
          .from("agent_registry")
          .select("*")
          .eq("domain", body.domain || "sta")
          .in("status", ["idle", "busy"])
          .order("current_task_count", { ascending: true })
          .order("error_rate", { ascending: true });

        if (!agents || agents.length === 0) {
          return json({ success: false, error: "No agents in domain" }, 503);
        }

        // Pick agent with least load that has the skill
        const skillRequired = body.task_type || "general";
        const bestAgent = agents.find((a) => {
          const skills = a.skills as string[];
          return skills.includes(skillRequired) || skills.includes("general");
        }) || agents[0];

        return json({ success: true, agent: bestAgent.agent_id, load: bestAgent.current_task_count });
      }

      case "execute": {
        if (!body.agent_id || !body.task_id) {
          return json({ success: false, error: "agent_id and task_id required" }, 400);
        }

        const { data: agent } = await supabase
          .from("agent_registry")
          .select("*")
          .eq("agent_id", body.agent_id)
          .single();

        const { data: task } = await supabase
          .from("agent_tasks")
          .select("*")
          .eq("id", body.task_id)
          .single();

        if (!agent || !task) {
          return json({ success: false, error: "Agent or task not found" }, 404);
        }

        const result = await executeTask(supabase, agent, { input: task.input, task_type: task.task_type, domain: task.domain });

        await supabase
          .from("agent_tasks")
          .update({
            status: result.success ? "completed" : "failed",
            output: result.output,
            error_message: result.error,
            completed_at: new Date().toISOString(),
          })
          .eq("id", body.task_id);

        return json({ success: true, result: result.output });
      }

      case "status": {
        const { data: registry } = await supabase
          .from("agent_registry")
          .select("agent_id, agent_name, domain, status, current_task_count, total_tasks_completed, error_rate, last_heartbeat");

        const { data: pendingTasks } = await supabase
          .from("agent_tasks")
          .select("id")
          .in("status", ["created", "queued", "assigned"]);

        const { data: runningTasks } = await supabase
          .from("agent_tasks")
          .select("id")
          .eq("status", "running");

        return json({
          success: true,
          agents: registry,
          summary: {
            total_agents: registry?.length || 0,
            idle: registry?.filter((a) => a.status === "idle").length || 0,
            busy: registry?.filter((a) => a.status === "busy").length || 0,
            offline: registry?.filter((a) => a.status === "offline").length || 0,
            pending_tasks: pendingTasks?.length || 0,
            running_tasks: runningTasks?.length || 0,
          },
        });
      }

      default:
        return json({ success: false, error: `Unknown action: ${action}` }, 400);
    }
  } catch (err) {
    return json({ success: false, error: err.message }, 500);
  }
});

async function executeTask(
  supabase: any,
  agent: any,
  body: any
): Promise<{ success: boolean; output?: any; error?: string; tokens?: number }> {
  const model = agent.model_used || "qwen3:8b";
  const skills = (agent.skills as string[]) || [];

  // Route to appropriate handler based on skills
  if (skills.includes("property_search") && body.task_type === "property_search") {
    const { data: properties } = await supabase
      .from("properties")
      .select("id, title, property_type, price, bedrooms, bathrooms, location, city, county, amenities, images")
      .eq("status", "active")
      .ilike("location", `%${body.input?.location || ""}%`)
      .gte("price", body.input?.min_price || 0)
      .lte("price", body.input?.max_price || 999999999)
      .limit(10);

    return { success: true, output: { properties: properties || [], count: properties?.length || 0 } };
  }

  if (skills.includes("payment_split") && body.task_type === "payment_process") {
    const amount = body.input?.amount || 0;
    const feePct = 5.0; // default platform fee
    const platformFee = amount * (feePct / 100);
    const landlordAmount = amount - platformFee;

    return {
      success: true,
      output: {
        total: amount,
        platform_fee: platformFee,
        landlord_amount: landlordAmount,
        fee_percentage: feePct,
        settlement_account: "01192643932500",
        landlord_account: body.input?.landlord_account,
      },
    };
  }

  if (skills.includes("daily_brief") && body.task_type === "daily_brief") {
    // Generate CEO daily briefing
    const [properties, payments, tenants, tasks, agents] = await Promise.all([
      supabase.from("properties").select("id, status").eq("status", "active"),
      supabase.from("payments").select("id, amount, status, created_at").gte("created_at", new Date(Date.now() - 86400000).toISOString()),
      supabase.from("tenants").select("id"),
      supabase.from("agent_tasks").select("id, status").gte("created_at", new Date(Date.now() - 86400000).toISOString()),
      supabase.from("agent_registry").select("agent_id, status"),
    ]);

    const totalRevenue = payments.data?.reduce((sum: number, p: any) => sum + (p.status === "confirmed" ? p.amount : 0), 0) || 0;
    const pendingPayments = payments.data?.filter((p: any) => p.status === "pending").length || 0;
    const completedTasks = tasks.data?.filter((t: any) => t.status === "completed").length || 0;
    const failedTasks = tasks.data?.filter((t: any) => t.status === "failed").length || 0;
    const activeAgents = agents.data?.filter((a: any) => a.status !== "offline").length || 0;

    const briefing = {
      title: `Daily Brief — ${new Date().toLocaleDateString("en-KE")}`,
      summary: `Revenue: KSh ${totalRevenue.toLocaleString()} | ${pendingPayments} pending payments | ${completedTasks}/${tasks.data?.length || 0} tasks completed | ${activeAgents}/${agents.data?.length || 0} agents active`,
      kpis: {
        revenue_ksh: totalRevenue,
        active_properties: properties.data?.length || 0,
        total_tenants: tenants.data?.length || 0,
        pending_payments: pendingPayments,
        tasks_completed: completedTasks,
        tasks_failed: failedTasks,
        agents_online: activeAgents,
        agent_uptime_pct: agents.data?.length ? ((activeAgents / agents.data.length) * 100).toFixed(1) : 0,
      },
      alerts: pendingPayments > 5 ? [{ type: "warning", message: `${pendingPayments} payments pending > 24h` }] : [],
      recommendations: failedTasks > 3 ? [{ type: "action", message: "Investigate agent failures — check Ollama models" }] : [],
    };

    // Store briefing
    await supabase.from("ceo_briefings").insert({
      briefing_type: "daily",
      title: briefing.title,
      summary: briefing.summary,
      kpis: briefing.kpis,
      alerts: briefing.alerts,
      recommendations: briefing.recommendations,
    });

    return { success: true, output: briefing };
  }

  if (skills.includes("syllogistic_reasoning")) {
    // Use Ollama for reasoning tasks
    try {
      const prompt = `You are a Syllogistic Reasoning Agent for Syllogism Technology Africa.
Context: ${JSON.stringify(body.input)}
Task: ${body.task_type}
Think step by step using syllogistic logic (major premise, minor premise, conclusion).`;

      const ollamaRes = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, prompt, stream: false }),
      });

      const data = await ollamaRes.json();
      return {
        success: true,
        output: { reasoning: data.response, model },
        tokens: data.eval_count || 0,
      };
    } catch (e) {
      return { success: false, error: `Ollama unavailable: ${e.message}` };
    }
  }

  // Default: use Ollama for general tasks
  try {
    const prompt = `You are ${agent.agent_name} for Syllogism Technology Africa.
Task: ${body.task_type || "general"}
Input: ${JSON.stringify(body.input)}
Provide a structured JSON response.`;

    const ollamaRes = await fetch(`${OLLAMA_URL}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, prompt, stream: false }),
    });

    const data = await ollamaRes.json();
    return {
      success: true,
      output: { response: data.response, model },
      tokens: data.eval_count || 0,
    };
  } catch {
    return { success: false, error: "Ollama not available — model inference offline" };
  }
}
