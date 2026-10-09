# 15-minute walkthrough recording plan

This is a recording outline for refreshing the existing 15:26 local video. Keep `.env`, terminal environment dumps, and authorization headers out of the recording. The regular dashboard connects automatically using server configuration; the judge console asks for a key and never saves it to browser storage. Do not show the typed key, even though its field is masked.

| Time | Demonstration and explanation |
| --- | --- |
| 00:00–01:00 | Introduce the RideEat classification/routing task. State that predictions use a locally trained model. Show the live URL and floating **Demo** button. |
| 01:00–03:00 | Open **Demo**. Walk through the judge checklist, required routes, hosted API docs, offline Docker command, repository-access note, training scores, five-page report, and video-refresh status. Explain that correctness, schema compliance, and robustness—not latency—are scored. |
| 03:00–05:00 | Show the key gate without recording the key. After authorization, exercise `/health`, `/predict`, `/predict/batch`, and the async submit/status/results/delete controls. Show HTTP statuses and structured JSON responses; keep headers redacted. |
| 05:00–06:30 | Return to the regular dashboard. Demonstrate chat, email subject/body, a Sinhala/Tamil or transliterated message, category/team, secondary issue, urgency, and human-review indicator. Explain these are predictions requiring judgment. |
| 06:30–08:00 | Load a JSON batch. Show synchronous results and JSON download; switch to Live operations and Support queue to confirm a routing decision. Submit an evaluation-sized async batch above 2,000 tickets; show polling, completion, and paging. |
| 08:00–09:00 | Show API protection without showing the key: public health, unauthorized prediction, and successful authenticated request with headers redacted. Show malformed JSON and structured validation errors. |
| 09:00–10:00 | Explain browser → FastAPI → local pipelines and async worker → SQLite. Explain queue limits, cancellation, restart handling, and retained results. |
| 10:00–12:00 | Show Model lab and training code: word/character features, three classifiers, thresholds, precedence rules, 75/25 split, and generated artifacts. Only claim improvements supported by saved experiments. |
| 12:00–13:30 | Present accuracy and macro-F1, per-language/category breakdowns, and common confusions. Explain that judges' holdout is independent and note synthetic-data/native-speaker-review limitations. |
| 13:30–14:30 | Show test results and official-schema validation. Demonstrate the single Docker run command, runtime without network, and repository setup. Label any incomplete check accurately. |
| 14:30–15:00 | Recap findings and limitations; point to the report and repository links; note the refreshed video must be uploaded unlisted. |

Record the screen and narration, trim to 15 minutes, upload as YouTube unlisted, test the link in a signed-out browser, and enter it in the submission checklist.
