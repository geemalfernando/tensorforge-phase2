"""Build and optionally execute the portable Fresh Desk analytics notebook."""
import argparse
from pathlib import Path
import nbformat as nb
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--kernel',default='python3')
    args=parser.parse_args()
    notebook=nb.v4.new_notebook(metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
    notebook.cells=[
      nb.v4.new_markdown_cell('# Fresh Desk · Model analytics\n\nRecomputes precision, recall, F1, confusion matrices and visualizations for all three classifiers from the saved artifact and supplied validation CSV. No API key or external inference service is used.\n\n**Development evaluation:** this validation set informed tuning; these scores are not independent holdout results. The data are synthetic.'),
      nb.v4.new_code_cell("from pathlib import Path\nimport sys\nROOT = next(path for path in (Path.cwd(), *Path.cwd().parents) if (path / 'app/model.py').exists())\nsys.path.insert(0, str(ROOT))\nimport pandas as pd\nfrom IPython.display import display, Image\nfrom scripts.model_analytics import build_analytics\nanalytics = build_analytics()\nprint('Model:', analytics['model_version'])\nprint('Validation tickets:', analytics['examples'])\nprint('Schema-valid predictions:', analytics['official_schema_valid_predictions'])"),
      nb.v4.new_markdown_cell('## Model configurations\nThe three pipelines share word/character TF-IDF features. Primary and urgency use logistic regression; secondary uses a calibrated linear SVM. Thresholds and parameters are frozen in the repository.'),
      nb.v4.new_code_cell("import json\nsettings = json.loads((ROOT / 'configs/training.json').read_text())\ndisplay(pd.DataFrame(settings['models']).T)"),
      nb.v4.new_markdown_cell('## Overall precision, recall and F1\nMacro averages give each supported class equal weight; weighted averages account for class frequency. Accuracy can hide rare-label failures.'),
      nb.v4.new_code_cell("rows = []\nfor target, report in analytics['classification_reports'].items():\n    rows.append({'model': target, 'accuracy': report['accuracy'], **{'macro_' + key: report['macro avg'][key] for key in ['precision','recall','f1-score']}, **{'weighted_' + key: report['weighted avg'][key] for key in ['precision','recall','f1-score']}})\nsummary = pd.DataFrame(rows).set_index('model')\ndisplay(summary.round(4))\ndisplay(Image(filename=analytics['figures']['model-summary']))"),
      nb.v4.new_markdown_cell('## Every class: precision, recall, F1 and support\nSecondary includes a no-secondary class; not every category has a secondary training label. A score of zero is reported rather than omitted when a supported class receives no correct predictions.'),
      nb.v4.new_code_cell("for target, report in analytics['classification_reports'].items():\n    print('\\n' + target)\n    display(pd.DataFrame({label: values for label, values in report.items() if isinstance(values, dict)}).T.round(4))\ndisplay(Image(filename=analytics['figures']['primary-class-scores']))"),
      nb.v4.new_markdown_cell('## Confusion matrices\nRows are true labels; columns are predictions. Counts use final API predictions after consistency and category precedence rules.'),
      nb.v4.new_code_cell("for target in ['category','secondary_category','is_urgent']:\n    display(Image(filename=analytics['figures'][target + '-confusion']))"),
      nb.v4.new_markdown_cell('## Language analysis\nSmall language groups are uncertain. These results measure the synthetic workshop split and do not establish accuracy on native speakers’ real support messages.'),
      nb.v4.new_code_cell("display(pd.DataFrame(analytics['category_by_language']).T.round(4))\ndisplay(Image(filename=analytics['figures']['language-accuracy']))"),
      nb.v4.new_markdown_cell('## Urgency precision–recall tradeoff\nThe configured operating cutoff is 30%. This plot is before the spam rule; the earlier score tables include the rule.'),
      nb.v4.new_code_cell("display(Image(filename=analytics['figures']['urgency-precision-recall']))"),
      nb.v4.new_markdown_cell('## Human approval and findings\nPrimary confidence below 50% or a message of three or fewer words recommends human review. Urgent tickets also enter the support queue. Support staff inspect the saved probabilities and may accept routing or explain an override. The raw model prediction is preserved. Primary probabilities are not independently calibrated.\n\nThe primary classifier remains the main limitation. The separate judges’ holdout dataset is the independent test.'),
      nb.v4.new_code_cell("print('Human-review recommendations:', analytics['human_review_count'], '/', analytics['examples'])\ndisplay(pd.DataFrame(analytics['top_category_confusions']))\nprint('Exported Markdown:', ROOT / 'docs/model-analytics.md')\nprint('Exported PNG/SVG figures:', ROOT / 'docs/analytics')"),
    ]
    destination=ROOT/'notebooks/model_analytics.ipynb';destination.parent.mkdir(exist_ok=True)
    if args.execute:
        NotebookClient(notebook,timeout=240,kernel_name=args.kernel,resources={'metadata':{'path':str(ROOT)}}).execute()
    nb.write(notebook,destination)
    print('Saved '+str(destination))


if __name__=='__main__':main()
