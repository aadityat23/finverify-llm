import sys
sys.path.insert(0, 'finverify-terminal/sdk')

from finverify import FinVerifyInterceptor, verify_local

# Test 1: Local DVL still works
print('=== TEST 1: Local DVL ===')
r = verify_local('What is the profit margin?', 0.2531)
print(f'  verified: {r.verified_value}, trust: {r.trust_score}, corrected: {r.was_corrected}')

# Test 2: Interceptor with local DVL on raw string
print()
print('=== TEST 2: Interceptor on raw string ===')
fv = FinVerifyInterceptor(use_local_dvl=True)

def fake_llm(prompt):
    return ('Apple reported net revenues of $383.3 billion for FY2023, '
            'with a gross margin of 0.4413 and net income of $97.0 billion. '
            'The EPS was $6.13 on 15.8 billion diluted shares.')

verified_fn = fv.wrap(fake_llm)
response = verified_fn('Tell me about Apple')

vr = response._finverify
print(f'  Trust: {vr.overall_trust}')
print(f'  Numbers found: {vr.numbers_found}')
print(f'  Metrics identified: {vr.metrics_identified}')
print(f'  Corrections: {len(vr.corrections)}')
for c in vr.corrections:
    print(f'    {c["original"]} -> {c["corrected"]} ({c["rule"]})')
print(f'  Original: {vr.original_text[:100]}...')
print(f'  Verified: {vr.verified_text[:100]}...')

# Test 3: Normalizer
print()
print('=== TEST 3: Metric inference ===')
from finverify.normalizer import normalize_metric_name
for name in ['net revenues', 'gross margin', 'EBIT', 'total stockholders equity']:
    print(f'  {name} -> {normalize_metric_name(name)}')
