# Fresh Desk — model recalibration

The active model artifact is `tf-phase2-drive-2.1.0`, trained on all 4,800 supplied labeled tickets. The dataset contains 4,000 training rows and 800 additional validation rows. The new evaluation uses a reproducible 75/25 stratified split of `train.csv` only (3,000 fit / 1,000 test); the validation file is held out from scoring and used only in the final full-data fit.

## Held-out results

| Model output | Test accuracy | Macro-F1 |
| --- | ---: | ---: |
| Primary category | 99.00% | 98.92% |
| Secondary category | 99.80% | 98.84% |
| Urgency | 99.90% | 99.71% |

In the test fold, all 150 delivery-delay tickets were classified correctly; none were confused with `lost_item`. Of 50 `lost_item` tickets, 48 were correct and one was predicted as `delivery_delay`. The reported example scenarios also classify correctly: a not-yet-arrived delayed order routes to `delivery_delay`, while a phone left in a ride routes to `lost_item`.

## Visual analysis and reproduction

The executed notebook contains the per-class precision/recall/F1 table, full category confusion matrix, per-language macro-F1 chart, delivery-delay/lost-property comparison, and the smoke checks:

- [Executed 75/25 training and evaluation notebook](../notebooks/retrain_75_25.ipynb)
- Metrics JSON: `../artifacts/evaluation_metrics.json`
- Confusion and breakdown JSON: `../artifacts/evaluation_breakdown.json`

Reproduce the notebook or run `python scripts/train_model.py`. The run uses `random_state=42`, stratifies the 25% test fold by primary category, scores before fitting the final model, then saves the refreshed artifact. The optional `language` field is now included in model features when provided and is not required in API requests.

These scores reflect the synthetic workshop data only. They are not a guarantee of quality on real support messages or the judges' independent evaluation set; Sinhala and Tamil text has not been independently reviewed by native speakers.
