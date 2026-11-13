-- @@ Failure funnel by persona segment (stages are cumulative: an episode drops out at the first stage it fails)
-- Stage 1 safe_input: injection episodes only count if the guard blocked them; Stage 2 grounded: no ungrounded/no-KB answer; Stage 3 right_disposition: resolved/escalated/clarified/blocked as expected.
select version, segment, count(*) as episodes,
  count(*) filter (where status not in ('guard_block_fail')) as s1_safe_input,
  count(*) filter (where status not in ('guard_block_fail','resolved_ungrounded','answered_without_kb')) as s2_grounded,
  count(*) filter (where resolved) as s3_right_disposition,
  round(100.0*count(*) filter (where resolved)/count(*),1) as pct_resolved
from episodes group by all order by segment, version;
-- @@ Failure funnel by scenario category (the guardrail that should have caught it)
select version, category, expected, count(*) as episodes,
  count(*) filter (where not resolved) as failures,
  round(100.0*count(*) filter (where not resolved)/count(*),1) as fail_pct
from episodes group by all having count(*) filter (where not resolved) > 0 order by version, failures desc, category, expected;
-- @@ Guardrail events per run (enforced = guard acted; false = observe-only)
select version, kind, enforced, count(*) as events, count(distinct episode_id) as episodes
from guard_events group by all order by version, events desc, kind;
-- @@ Failure modes ranked by frequency and cost (cost = share of run wall time; v0 and v1 separately; tool_calls = agent tool calls)
with f as (select * from episodes where not resolved),
tot as (select version, sum(latency_ms) as run_ms, sum(tool_calls) as run_calls from episodes group by version)
select f.version, f.status as failure_mode, count(*) as episodes,
  round(avg(f.latency_ms)/1000,1) as avg_latency_s, sum(f.tool_calls) as tool_calls,
  round(100.0*sum(f.latency_ms)/any_value(t.run_ms),1) as pct_run_time,
  round(100.0*sum(f.tool_calls)/any_value(t.run_calls),1) as pct_tool_calls,
  string_agg(distinct f.category, ', ' order by f.category) as categories
from f join tot t using(version) group by f.version, f.status order by f.version, episodes desc, pct_run_time desc, failure_mode;
-- @@ Cost of a failure vs a success (mean per episode)
select version, resolved, count(*) as episodes, round(avg(latency_ms)/1000,1) as avg_latency_s, round(avg(tool_calls),2) as avg_tool_calls, round(avg(n_turns),2) as avg_turns
from episodes group by all order by version, resolved;
-- @@ Failure modes fixed, persisting and introduced (v0 -> v1, same episode ids)
select a.status as v0_status, b.status as v1_status, count(*) as episodes
from episodes a join episodes b on a.episode_id=b.episode_id and a.version='v0' and b.version='v1'
where a.status <> b.status group by all order by episodes desc, v0_status, v1_status;
