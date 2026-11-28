// Only public research GET contracts. Never send credentials or infer signals.
export type ResearchSnapshot = {
  candidates: number | null; reviewed: number | null; symbols: string[] | null;
  marketStatus: string; marketScore: number | null; session: string | null;
};
export function apiOrigin(raw: string): string {
  const url = new URL(raw);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new Error('A dedicated HTTPS API origin is required');
  }
  return url.origin;
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid research response');
  return value as Record<string, unknown>;
}
function count(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null;
}
export function parseResearch(readiness: unknown, market: unknown, symbols: unknown): ResearchSnapshot {
  const r = record(readiness), m = record(market), s = record(symbols);
  if (r.mode !== 'research_only' || r.missing_evidence_policy !== 'UNKNOWN' ||
      r.production_recommendations_enabled !== false || r.ai_recommendations_enabled !== false ||
      r.ranking_enabled !== false) throw new Error('Unsupported readiness contract');
  const list = s.symbols;
  const validSymbols = Array.isArray(list) && list.every(x => typeof x === 'string' && /^[A-Z0-9]{1,24}$/.test(x)) &&
    new Set(list).size === list.length && s.count === list.length;
  // No market score displayed until a separate trusted-source contract is reviewed.
  return { candidates: count(r.candidate_equities), reviewed: count(r.canonical_reviewed_rows),
    symbols: validSymbols && s.universe_status === 'secondary_candidate_manifest_validated' ? [...list].sort() : null,
    marketStatus: m.status === 'insufficient_evidence' ? 'Insufficient evidence' : 'Unverified',
    marketScore: null, session: null };
}
export async function loadResearch(raw: string, signal: AbortSignal): Promise<ResearchSnapshot> {
  const origin = apiOrigin(raw);
  async function get(path: string): Promise<unknown> {
    const response = await fetch(origin + path, { method: 'GET', signal, credentials: 'omit', redirect: 'error', headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('Research API unavailable');
    return response.json();
  }
  const [r, m, s] = await Promise.all([get('/v1/research/readiness'), get('/v1/market-health'), get('/v1/symbols')]);
  return parseResearch(r, m, s);
}
