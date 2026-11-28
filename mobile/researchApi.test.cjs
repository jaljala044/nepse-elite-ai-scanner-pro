const test = require('node:test');
const assert = require('node:assert/strict');
const { apiOrigin, parseResearch } = require('./researchApi.ts');
const readiness = { mode:'research_only', missing_evidence_policy:'UNKNOWN', production_recommendations_enabled:false, ai_recommendations_enabled:false, ranking_enabled:false, candidate_equities:281, canonical_reviewed_rows:0 };
test('HTTPS origin without credentials or path', () => {
  assert.equal(apiOrigin('https://example.org'), 'https://example.org');
  for (const u of ['http://example.org','https://a:b@example.org','https://example.org/path','https://example.org/?x=y']) assert.throws(()=>apiOrigin(u));
});
test('preserve research coverage and withhold market score', () => {
  const r = parseResearch(readiness,{status:'insufficient_evidence',market_health_score:99},{symbols:['API'],count:1,universe_status:'secondary_candidate_manifest_validated'});
  assert.equal(r.marketScore,null); assert.equal(r.reviewed,0); assert.deepEqual(r.symbols,['API']);
});
test('reject live recommendation contract and malformed symbol inventory', () => {
  assert.throws(()=>parseResearch({...readiness,ranking_enabled:true},{},{}));
  assert.equal(parseResearch(readiness,{}, {symbols:['API','API'],count:2,universe_status:'secondary_candidate_manifest_validated'}).symbols,null);
});
