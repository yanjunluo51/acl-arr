"""Public metadata and local availability; never assert original inference identity."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import datetime
import json
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'review-revision/operational-scope-implementation'


def fetch(row):
    model = row['released_result_identity']
    url = 'https://huggingface.co/api/models/'+model
    result = dict(row)
    result['metadata_url'] = url
    result['checked_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Academic scorer identity audit'}), timeout=25) as f:
            data = json.load(f)
        result.update({'public_metadata_status': 'AVAILABLE',
                       'current_public_repository_revision': data.get('sha'),
                       'current_revision_is_original_scoring_revision': False,
                       'gated': data.get('gated'), 'private': data.get('private'),
                       'pipeline_tag': data.get('pipeline_tag'),
                       'weight_metadata': data.get('safetensors'),
                       'model_card_license': data.get('cardData', {}).get('license'),
                       'repository_files': [x['rfilename'] for x in data.get('siblings', [])]})
    except Exception as e:
        result.update({'public_metadata_status': 'UNAVAILABLE_OR_ERROR',
                       'http_status': e.code if isinstance(e, HTTPError) else None,
                       'error_class': type(e).__name__})
    result['admitted_for_E1'] = False
    return result


def main():
    old = json.loads((ROOT/'review-revision/acceptance-review-implementation/real-cost-resource-ledger.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, old['released_reward_scorer_identities']))
    cache = Path.home()/'.cache/huggingface/hub'
    local = sorted(x.name for x in cache.glob('models--*') if x.is_dir())
    candidates = [x for x in rows if ('models--'+x['released_result_identity'].replace('/', '--')) in local]
    memory = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.memsize'], text=True).strip()
    result = {'status': 'HOLD_ORIGINAL_SCORER_REVISION_AND_FULL_EXECUTION_RESOURCES',
              'machine': platform.machine(), 'system': platform.system(), 'physical_memory_bytes': int(memory),
              'inspected_model_cache_root': str(cache), 'inspected_model_cache_directories': local,
              'original_family_models_found_in_inspected_cache': len(candidates),
              'public_metadata_available': sum(r['public_metadata_status']=='AVAILABLE' for r in rows),
              'reward_scorers': rows, 'original_weight_revision_verified': False,
              'original_tokenizer_template_and_precision_verified': False,
              'original_WMT_execution_revisions_verified': False,
              'real_scorer_inference_executed': False, 'fallback_or_proxy_used': False,
              'runtime_savings_claimed': False,
              'scope': 'Current public model metadata is not the original released-score execution revision. Local availability is scoped to the inspected cache; other hardware and paths are unknown.'}
    (OUT/'real-cost-resource-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['status', 'public_metadata_available',
                       'original_family_models_found_in_inspected_cache', 'real_scorer_inference_executed']}))


if __name__ == '__main__':
    main()
