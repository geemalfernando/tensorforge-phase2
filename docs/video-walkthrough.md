# 15-minute walkthrough recording plan

This is a recording outline, not a completed video. Keep `.env`, terminal environment dumps, key input, and authorization headers out of the recording. Connect the dashboard before recording.

| Time | Demonstration and explanation |
| --- | --- |
| 00:00–01:00 | Introduce the RideEat classification/routing task. State that predictions use a locally trained model. Show the live URL once deployed. |
| 01:00–03:00 | Demonstrate chat, email subject/body, a Sinhala/Tamil or transliterated message, category/team, secondary issue, urgency, and human-review indicator. Explain these are predictions requiring judgment. |
| 03:00–05:00 | Load a JSON batch. Show synchronous results, urgent/review filters, and JSON download. Submit an evaluation-sized async batch above 2,000 tickets; show polling, completion, and paging. |
| 05:00–06:30 | Show API protection without showing the key: public health, unauthorized prediction, and successful authenticated request with headers redacted. Show malformed JSON and structured validation errors. |
| 06:30–08:00 | Explain browser → FastAPI → local pipelines and async worker → SQLite. Explain queue limits, cancellation, restart handling, and retained results. |
| 08:00–10:30 | Show training code, word/character features, excluded ticket IDs/language labels, three classifiers, thresholds, and precedence rules. Show the training command and generated artifacts. Only claim improvements supported by saved experiments. |
| 10:30–12:30 | Present validation accuracy and macro-F1, per-language/category breakdowns, and common confusions. Explain validation informed tuning and judges' holdout is independent. Explain synthetic-data/native-speaker-review limitations. |
| 12:30–14:00 | Show test results and official-schema validation once available. Demonstrate the single Docker run command, runtime without network, public endpoint, and repository setup. Label any incomplete check accurately. |
| 14:00–15:00 | Recap findings and limitations, point to report and repository links, and describe the human-review workflow and next model-evaluation work. |

Record the screen and narration, trim to 15 minutes, upload as YouTube unlisted, test the link in a signed-out browser, and enter it in the submission checklist.
