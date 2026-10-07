"""Retrain all three classifiers from labeled CSVs using the saved experiment configuration."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.model import MODEL_VERSION, TEAM_BY_CATEGORY, TicketModel, compose_text, make_classifier

DATA_DIR = ROOT / 'datasets'
ARTIFACT_DIR = ROOT / 'artifacts'
SECONDARY_NONE = '__none__'


def read_examples(path: Path) -> Tuple[List[Dict[str, str]], List[str], List[str], List[str]]:
    tickets, categories, secondary, urgent = [], [], [], []
    with path.open(encoding='utf-8-sig', newline='') as source:
        for index, row in enumerate(csv.DictReader(source), start=2):
            category = row['category'].strip()
            second = row['secondary_category'].strip() or SECONDARY_NONE
            flag = row['is_urgent'].strip().lower()
            if category not in TEAM_BY_CATEGORY or (second != SECONDARY_NONE and second not in TEAM_BY_CATEGORY):
                raise ValueError(f'{path.name}:{index}: unknown category label')
            if flag not in ('true', 'false') or second == category:
                raise ValueError(f'{path.name}:{index}: inconsistent labels')
            if not row['text'].strip() or row['channel'] not in ('email', 'chat', 'call_transcript'):
                raise ValueError(f'{path.name}:{index}: invalid ticket')
            tickets.append({'channel': row['channel'], 'subject': row['subject'], 'text': row['text']})
            categories.append(category); secondary.append(second); urgent.append(flag)
    if not tickets:
        raise ValueError('Training/evaluation dataset is empty')
    return tickets, categories, secondary, urgent


def evaluate(labels, predictions):
    return {'accuracy': round(float(accuracy_score(labels, predictions)), 4),
            'macro_f1': round(float(f1_score(labels, predictions, average='macro', zero_division=0)), 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, default=DATA_DIR / 'train.csv')
    parser.add_argument('--validation', type=Path, default=DATA_DIR / 'validation.csv')
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/training.json')
    parser.add_argument('--output-dir', type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    train, category, secondary, urgent = read_examples(args.train)
    validation, validation_category, validation_secondary, validation_urgent = read_examples(args.validation)
    texts = [compose_text(ticket) for ticket in train]
    models = {}
    for target, labels in {'category':category, 'secondary_category':secondary, 'is_urgent':urgent}.items():
        options = {key:value for key,value in config['models'][target].items() if key != 'threshold'}
        pipeline = make_classifier(**options).fit(texts, np.asarray(labels))
        models[target] = pipeline
        print('Fresh fit: '+target+' on '+str(len(labels))+' labeled tickets', flush=True)
    metadata = {
        'source': json.loads((DATA_DIR/'source_manifest.json').read_text()) if (DATA_DIR/'source_manifest.json').exists() else {},
        'train_sha256': hashlib.sha256(args.train.read_bytes()).hexdigest(),
        'validation_sha256': hashlib.sha256(args.validation.read_bytes()).hexdigest(),
        'selected_configurations': config['models'],
        'selection_note': config['selection_note'],
    }
    artifact = {'model_version': MODEL_VERSION, 'category_model':models['category'],
                'secondary_model':models['secondary_category'], 'urgent_model':models['is_urgent'],
                'urgent_threshold':config['models']['is_urgent']['threshold'],
                'secondary_threshold':config['models']['secondary_category']['threshold'],
                'training_metadata':metadata}
    predictions = TicketModel(artifact).predict_many(validation)
    metrics = {'model_version':MODEL_VERSION, 'training_examples':len(train), 'validation_examples':len(validation),
               'validation':{'category':evaluate(validation_category,[p['category'] for p in predictions]),
                             'secondary_category':evaluate(validation_secondary,[p['secondary_category'] or SECONDARY_NONE for p in predictions]),
                             'is_urgent':evaluate(validation_urgent,[str(p['is_urgent']).lower() for p in predictions])},
               'thresholds':{'is_urgent':artifact['urgent_threshold'],'secondary_category':artifact['secondary_threshold']},
               'training_metadata':metadata}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Replace the artifact only after all three fits and validation finish successfully.
    temporary = args.output_dir/'model.joblib.tmp'
    joblib.dump(artifact, temporary, compress=3)
    temporary.replace(args.output_dir/'model.joblib')
    (args.output_dir/'evaluation_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics['validation'],indent=2),flush=True)
    print('Saved fresh artifact to '+str(args.output_dir/'model.joblib'),flush=True)


if __name__ == '__main__':
    main()
