"""Evaluate a fixed 75/25 training-data split, then fit deployment models on all labels."""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

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
            tickets.append({
                'channel': row['channel'],
                'language': row.get('language', '').strip(),
                'subject': row['subject'],
                'text': row['text'],
            })
            categories.append(category); secondary.append(second); urgent.append(flag)
    if not tickets:
        raise ValueError('Training/evaluation dataset is empty')
    return tickets, categories, secondary, urgent


def evaluate(labels, predictions):
    return {'accuracy': round(float(accuracy_score(labels, predictions)), 4),
            'macro_f1': round(float(f1_score(labels, predictions, average='macro', zero_division=0)), 4)}


def _fit_models(tickets, categories, secondary, urgent, config):
    texts = [compose_text(ticket) for ticket in tickets]
    models = {}
    for target, labels in {
        'category': categories,
        'secondary_category': secondary,
        'is_urgent': urgent,
    }.items():
        options = {key:value for key,value in config['models'][target].items() if key != 'threshold'}
        pipeline = make_classifier(**options).fit(texts, np.asarray(labels))
        models[target] = pipeline
        print('Fresh fit: '+target+' on '+str(len(labels))+' labeled tickets', flush=True)
    return models


def _make_artifact(models, config, metadata):
    return {
        'model_version': MODEL_VERSION,
        'category_model': models['category'],
        'secondary_model': models['secondary_category'],
        'urgent_model': models['is_urgent'],
        'urgent_threshold': config['models']['is_urgent']['threshold'],
        'secondary_threshold': config['models']['secondary_category']['threshold'],
        'training_metadata': metadata,
    }


def _summarize_holdout(tickets, categories, secondary, urgent, artifact):
    predictions = TicketModel(artifact).predict_many(tickets)
    actual = {
        'category': categories,
        'secondary_category': secondary,
        'is_urgent': urgent,
    }
    predicted = {
        'category': [item['category'] for item in predictions],
        'secondary_category': [
            item['secondary_category'] or SECONDARY_NONE for item in predictions
        ],
        'is_urgent': [str(item['is_urgent']).lower() for item in predictions],
    }
    labels = list(TEAM_BY_CATEGORY)
    confusions = Counter(
        (truth, guess)
        for truth, guess in zip(actual['category'], predicted['category'])
        if truth != guess
    )
    language_scores = {}
    for language in sorted({ticket['language'] for ticket in tickets}):
        indices = [
            index for index, ticket in enumerate(tickets)
            if ticket['language'] == language
        ]
        language_scores[language] = {
            'count': len(indices),
            **evaluate(
                [actual['category'][index] for index in indices],
                [predicted['category'][index] for index in indices],
            ),
        }
    return {
        'validation': {
            target: evaluate(actual[target], predicted[target])
            for target in actual
        },
        'classification_reports': {
            target: classification_report(
                actual[target], predicted[target], output_dict=True, zero_division=0
            )
            for target in actual
        },
        'category_report': classification_report(
            actual['category'], predicted['category'],
            labels=labels, output_dict=True, zero_division=0,
        ),
        'category_confusion_matrix': {
            'labels': labels,
            'rows_actual_columns_predicted': confusion_matrix(
                actual['category'], predicted['category'], labels=labels
            ).tolist(),
        },
        'category_by_language': language_scores,
        'top_category_confusions': [
            {'actual': truth, 'predicted': guess, 'count': count}
            for (truth, guess), count in confusions.most_common(10)
        ],
        'predicted_categories': predicted['category'],
    }


def run_training(
    train_path=DATA_DIR / 'train.csv',
    validation_path=DATA_DIR / 'validation.csv',
    config_path=ROOT / 'configs/training.json',
    output_dir=ARTIFACT_DIR,
    test_size=0.25,
    random_state=42,
):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    train_tickets, categories, secondary, urgent = read_examples(train_path)
    final_validation, final_categories, final_secondary, final_urgent = read_examples(
        validation_path
    )
    fit_indices, test_indices = train_test_split(
        np.arange(len(train_tickets)),
        test_size=test_size,
        random_state=random_state,
        stratify=categories,
    )
    fit_tickets = [train_tickets[index] for index in fit_indices]
    holdout_tickets = [train_tickets[index] for index in test_indices]
    fit_labels = (
        [categories[index] for index in fit_indices],
        [secondary[index] for index in fit_indices],
        [urgent[index] for index in fit_indices],
    )
    holdout_labels = (
        [categories[index] for index in test_indices],
        [secondary[index] for index in test_indices],
        [urgent[index] for index in test_indices],
    )

    print('Training holdout models on {} examples'.format(len(fit_tickets)), flush=True)
    holdout_models = _fit_models(fit_tickets, *fit_labels, config)
    holdout_metadata = {
        'selected_configurations': config['models'],
    }
    holdout_artifact = _make_artifact(
        holdout_models, config, holdout_metadata
    )
    summary = _summarize_holdout(
        holdout_tickets, *holdout_labels, holdout_artifact
    )

    metadata = {
        'source': json.loads((DATA_DIR / 'source_manifest.json').read_text(encoding='utf-8'))
        if (DATA_DIR / 'source_manifest.json').exists() else {},
        'dataset_sha256': {
            'train': hashlib.sha256(train_path.read_bytes()).hexdigest(),
            'validation': hashlib.sha256(validation_path.read_bytes()).hexdigest(),
        },
        'selected_configurations': config['models'],
        'selection_note': config['selection_note'],
        'evaluation_split': {
            'method': 'stratified random split by primary category from train.csv only',
            'test_size': test_size,
            'random_state': random_state,
            'fit_examples': len(fit_indices),
            'test_examples': len(test_indices),
            'validation_file_used_for_test_scoring': False,
        },
        'holdout_metrics': summary['validation'],
    }

    all_tickets = train_tickets + final_validation
    all_labels = (
        categories + final_categories,
        secondary + final_secondary,
        urgent + final_urgent,
    )
    print('Refitting deployment models on {} labeled examples'.format(len(all_tickets)), flush=True)
    final_models = _fit_models(all_tickets, *all_labels, config)
    artifact = _make_artifact(final_models, config, metadata)

    metrics = {
        'model_version': MODEL_VERSION,
        'training_examples': len(all_tickets),
        'validation_examples': len(test_indices),
        'evaluation_note': (
            'Metrics are from the untouched 25% stratified test fold of train.csv. '
            'After scoring, the deployment artifact was refit on train.csv plus '
            'validation.csv; do not evaluate that final artifact on these same examples.'
        ),
        'evaluation_split': metadata['evaluation_split'],
        'validation': summary['validation'],
        'classification_reports': summary['classification_reports'],
        'category_report': summary['category_report'],
        'category_confusion_matrix': summary['category_confusion_matrix'],
        'category_by_language': summary['category_by_language'],
        'top_category_confusions': summary['top_category_confusions'],
        'thresholds': {
            'is_urgent': artifact['urgent_threshold'],
            'secondary_category': artifact['secondary_threshold'],
        },
        'training_metadata': metadata,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = output_dir / 'model.joblib.tmp'
    joblib.dump(artifact, temporary, compress=3)
    temporary.replace(output_dir / 'model.joblib')
    (output_dir / 'evaluation_metrics.json').write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    breakdown = {
        key: metrics[key]
        for key in (
            'model_version', 'evaluation_note', 'evaluation_split',
            'validation', 'classification_reports', 'category_report',
            'category_confusion_matrix', 'category_by_language',
            'top_category_confusions',
        )
    }
    (output_dir / 'evaluation_breakdown.json').write_text(
        json.dumps(breakdown, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    print(json.dumps(metrics['validation'], indent=2), flush=True)
    print('Saved fresh artifact to {}'.format(output_dir / 'model.joblib'), flush=True)
    return metrics, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, default=DATA_DIR / 'train.csv')
    parser.add_argument('--validation', type=Path, default=DATA_DIR / 'validation.csv')
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/training.json')
    parser.add_argument('--output-dir', type=Path, default=ARTIFACT_DIR)
    parser.add_argument('--test-size', type=float, default=0.25)
    parser.add_argument('--random-state', type=int, default=42)
    args = parser.parse_args()
    run_training(
        args.train, args.validation, args.config, args.output_dir,
        args.test_size, args.random_state,
    )


if __name__ == '__main__':
    main()
