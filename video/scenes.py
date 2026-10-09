"""Scene list for the Fresh Desk / TensorForge 2.0 Phase 2 walkthrough video.

Every scene is a list of beats. A beat is one narration chunk plus what is on screen while it plays:
  slide scenes  -> beat i reveals the first `show` items of the slide
  terminal      -> beat i reveals the first `show` blocks of captured terminal output
  live          -> beat i runs the matching action block in live.cjs
"""

SCENES = [
    # ---------------------------------------------------------------- 1. Intro
    dict(id="title", kind="slide", layout="title",
         kicker="TensorForge 2.0 · Phase 2 MVP",
         title="Fresh Desk",
         subtitle="Multilingual support-ticket classification and routing for RideEat",
         items=["3 locally trained models", "11 categories → 11 teams", "Sinhala · Tamil · English · Singlish",
                "Offline Docker inference"],
         beats=[
             dict(show=0, say="Hello, and welcome to our TensorForge 2.0 Phase 2 walkthrough. "
                              "This is Fresh Desk: a customer support ticket classification and routing system "
                              "for RideEat, the fictional ride-hailing and food delivery platform in the brief."),
             dict(show=4, say="In the next fifteen minutes we will show the working solution, explain the architecture, "
                              "walk through how our three machine learning models were trained, validated and improved, "
                              "and show exactly how we tested the authenticated evaluation API against the official contract."),
         ]),

    dict(id="task", kind="slide", layout="table",
         kicker="The problem",
         title="One ticket in. Three predictions and a team out.",
         items=[
             "category — the primary issue, one of 11 values",
             "secondary_category — a second issue, or null",
             "is_urgent — needs immediate human attention",
             "team — derived from category with a fixed table",
         ],
         table=[("payment_refund", "Payments & Refunds"), ("ride_trip_issue", "Ride Operations"),
                ("lost_item", "Lost & Found"), ("order_missing_wrong", "Food Operations"),
                ("delivery_delay", "Delivery Operations"), ("food_quality", "Restaurant Quality"),
                ("account_promo", "Account Services"), ("safety_conduct", "Trust & Safety"),
                ("app_technical", "Tech Support"), ("general_inquiry", "Front-line Support"),
                ("spam_irrelevant", "Auto-close / Spam Filter")],
         beats=[
             dict(show=1, say="Each ticket arrives with a channel, which is email, chat or call transcript, an optional subject, "
                              "and free text. The text can be English, Sinhala, Tamil, Sinhala or Tamil typed in Latin script, "
                              "emojis, or a mix of all of these. First, we predict the primary category, one of eleven values."),
             dict(show=3, say="Second, a secondary category when the ticket clearly contains two issues, otherwise null. "
                              "And third, whether the ticket is urgent and needs immediate human attention."),
             dict(show=4, say="The team is not predicted. It is derived from the category using the fixed table on the right, "
                              "exactly as the contract defines it. The contract also adds consistency rules: the secondary "
                              "category must differ from the primary, and spam is never urgent and never has a secondary category."),
         ]),

    dict(id="approach", kind="slide", layout="bullets",
         kicker="Our approach",
         title="Our own trained classifiers — not an LLM wrapper",
         items=[
             "Classical ML: TF-IDF word + character n-grams with linear models",
             "Trained only on the organisers' 4,000 labelled RideEat tickets",
             "Three separate models: category · secondary category · urgency",
             "Model files are bundled in the image — no downloads, no external AI calls",
             "Every response validated against the official OpenAPI + JSON Schemas",
         ],
         beats=[
             dict(show=2, say="The guidelines are clear that simply wrapping a large language model is discouraged. "
                              "So every prediction in Fresh Desk comes from classifiers we trained ourselves: "
                              "T F I D F features over words and characters, feeding linear models, "
                              "trained only on the four thousand labelled tickets supplied by the organisers."),
             dict(show=5, say="We train three separate models, one for each prediction target. The fitted pipelines are saved "
                              "as a single artifact and baked into the Docker image, so inference needs no internet, "
                              "no model download and no external A I service. And every response is checked against the official "
                              "OpenAPI contract and JSON Schemas."),
         ]),

    # ---------------------------------------------------------------- 2. Architecture
    dict(id="architecture", kind="slide", layout="architecture",
         kicker="Architecture",
         title="Two entry points, one model, one contract",
         items=["judges", "browser", "api", "model", "jobs", "docker"],
         beats=[
             dict(show=2, say="Here is the architecture. There are two ways in. On the left, the judges' evaluation harness "
                              "calls the API directly with the team API key. Below it, the Fresh Desk dashboard in the browser. "
                              "The browser never holds the key: it calls a same-origin dashboard route, and the server attaches "
                              "the key internally."),
             dict(show=3, say="Every protected request goes through the same checks, in the order the contract requires: "
                              "authentication first, then content type, then payload size, then JSON parsing, and finally field "
                              "validation. An unauthorised request never reaches the parser or the model."),
             dict(show=4, say="Valid tickets go to the ticket model: the three trained pipelines, plus the fixed category to team "
                              "map and the consistency rules. The single and small batch endpoints run this synchronously."),
             dict(show=5, say="Large evaluation runs use asynchronous jobs. The request is validated up front, stored in SQLite, "
                              "and a background worker classifies the tickets, so health checks and live predictions stay responsive."),
             dict(show=6, say="All of this ships as one Docker image that starts with a single docker run command "
                              "and runs with no network access at all."),
         ]),

    # ---------------------------------------------------------------- 3. Live demo
    dict(id="demo_intake", kind="live",
         beats=[
             dict(say="Let's see it working. This is the Fresh Desk home page, running locally from the same FastAPI "
                      "server that serves the API. The status pill in the top right confirms the model is loaded and the "
                      "service is ready."),
             dict(say="We open the desk and create a live chat ticket in Singlish: Sinhala typed with English letters. "
                      "The customer says their order is an hour late, the driver won't answer, and they want a refund."),
             dict(say="The prediction comes back in milliseconds. Primary category: delivery delay, routed to Delivery "
                      "Operations. Secondary category: payment refund, because the customer also asked for their money back. "
                      "And the urgency model flags it as urgent: the customer has waited an hour and cannot reach the driver."),
             dict(say="Next, a safety case. A passenger says the driver is not stopping the car, and they are scared. "
                      "The model routes it to Trust and Safety, with high confidence, and raises the urgent flag."),
             dict(say="Now a message in Tamil script, about an item missing from an order and a request for the money back. "
                      "It goes to Food Operations, with payment refund as the secondary issue. Confidence here is low, so the "
                      "ticket is flagged for human review. There is no translation step: character n-gram features let one "
                      "model read Sinhala, Tamil and English scripts directly."),
             dict(say="And finally an email, with a subject line. The customer's diabetic father is waiting on an insulin "
                      "delivery and the rider's phone is off. Even though the email is written politely, the urgency model "
                      "picks up that this needs immediate attention."),
         ]),

    dict(id="demo_ops", kind="live",
         beats=[
             dict(say="Every classified ticket lands in Live operations, a running view of routes, urgency and review "
                      "status for the session."),
             dict(say="Urgent or low-confidence tickets go to the Support queue. Support staff sign in with a separate "
                      "server-side password. The customer role cannot accept or reroute tickets."),
             dict(say="A support agent reviews the model's signals and accepts the ticket, or picks a different team and "
                      "must give a reason for the override. The model's original prediction is never changed: the "
                      "human decision is stored next to it."),
         ]),

    dict(id="demo_batch", kind="live",
         beats=[
             dict(say="The Batch workbench is the evaluation path in the dashboard. Up to one hundred tickets run "
                      "synchronously, through the predict batch endpoint. Here is the sample batch."),
             dict(say="The predictions come back in the same order as the request, each one echoing its ticket I D."),
             dict(say="Now an evaluation-sized run. We paste three thousand tickets. Above one hundred tickets, the "
                      "workbench switches to an asynchronous batch job: it submits, polls the job status, and fetches the "
                      "results when the job has succeeded."),
             dict(say="All three thousand predictions are back, in order, and can be downloaded as JSON in the same "
                      "format the judges receive from the API."),
         ]),

    # ---------------------------------------------------------------- 4. Training
    dict(id="data", kind="slide", layout="stats",
         kicker="Data",
         title="Organiser data only, with provenance",
         stats=[("4,000", "training tickets"), ("800", "validation tickets"), ("6", "language styles"),
                ("SHA-256", "checksums recorded")],
         items=[
             "Downloaded from the official Drive folder; checksums in datasets/source_manifest.json",
             "Model inputs: channel, subject and text only",
             "Excluded: ticket IDs and the supplied language labels (the API never sends them)",
             "Validation mix: English 280 · Singlish 200 · Sinhala 160 · Tamil 120 · Tanglish 20 · mixed 20",
         ],
         beats=[
             dict(show=1, say="Now, how the models were built. We used only the organisers' data: four thousand training "
                              "tickets and eight hundred validation tickets. The archive was downloaded from the official "
                              "Drive folder, and the SHA two fifty six checksum of every file is recorded in the repository."),
             dict(show=3, say="The models see only what the API will see at evaluation time: channel, subject and text. "
                              "We deliberately excluded ticket I Ds and the language labels in the dataset, because the "
                              "judges' requests never contain them, and a model that relied on them would fail on the holdout."),
             dict(show=4, say="The validation set covers six language styles, from English and Singlish to Sinhala and Tamil "
                              "script, with smaller Tanglish and mixed-script groups."),
         ]),

    dict(id="training", kind="slide", layout="models",
         kicker="Training pipeline",
         title="Three pipelines, tuned separately",
         models=[
             ("Category", "Logistic regression", ["class_weight = balanced, C = 100",
                                                   "word 1–2-grams + char_wb 2–6-grams", "11 classes"]),
             ("Secondary category", "Calibrated linear SVM", ["C = 1, sigmoid calibration (3-fold)",
                                                               "char 2–6-grams, light text cleanup", "threshold 0.2"]),
             ("Urgency", "Logistic regression", ["class_weight = balanced, C = 40",
                                                  "char 2–5-grams, light text cleanup", "threshold 0.3"]),
         ],
         items=["Fixed category → team map and contract consistency rules applied after the models",
                "Human review recommended when primary confidence < 0.5 or the message has ≤ 3 words"],
         beats=[
             dict(show=1, say="Each target has its own pipeline. The category model is a class-balanced logistic regression "
                              "over word unigrams and bigrams plus word-boundary character n-grams of length two to six. "
                              "Character n-grams are what make the model work across scripts and spelling variants, "
                              "such as the many ways people type Singlish."),
             dict(show=2, say="The secondary category model is a linear support vector machine with sigmoid calibration, "
                              "so we get usable probabilities. A secondary category is only returned when its probability is above "
                              "zero point two and it differs from the primary."),
             dict(show=3, say="The urgency model is another balanced logistic regression on character n-grams, with a decision "
                              "threshold of zero point three, chosen to favour catching urgent tickets. For secondary and urgency "
                              "we apply light cleanup: normalising whitespace and removing quoted earlier correspondence and "
                              "synthetic reference numbers."),
             dict(show=5, say="After the models, fixed rules enforce the contract: the team comes from the category table, "
                              "spam is never urgent, and the secondary category cannot repeat the primary. When confidence is "
                              "below fifty percent or the message is three words or fewer, we recommend human review."),
         ]),

    dict(id="improvement", kind="slide", layout="timeline",
         kicker="Validation and improvement",
         title="What we tried, what we kept, what we rejected",
         steps=[
             ("Baseline", "Category 62.9% acc · 64.9 macro-F1", "neutral"),
             ("Internal split", "98–99% on a training-only split — too easy, not trusted", "warn"),
             ("First pick regressed", "60.9% acc on development validation", "bad"),
             ("Boilerplate cleaner", "≈ 56–57% acc — rejected", "bad"),
             ("Primary grid on dev set", "C = 100, unnormalised char_wb → 63.0% · 65.0", "good"),
             ("Urgency threshold sweep", "macro-F1 92.6 → 93.1", "good"),
         ],
         items=[],
         beats=[
             dict(show=1, say="Here is how the models were validated and improved, including what did not work. "
                              "We started from a baseline at sixty two point nine percent category accuracy."),
             dict(show=3, say="Our first round of tuning used an internal split of the training data, where every candidate "
                              "scored ninety-eight to ninety-nine percent. That was a warning sign: the synthetic training tickets "
                              "are very similar to each other. Sure enough, the candidate we picked there dropped to sixty point "
                              "nine percent on the development validation set. So we stopped trusting the internal split for selection."),
             dict(show=4, say="We also tried stripping greeting and sign-off boilerplate from the text. It sounded sensible, "
                              "but accuracy fell to around fifty six percent, so we rejected it. Those polite phrases turn out to carry signal."),
             dict(show=6, say="We then compared regularisation strengths, class weighting and feature settings on the development "
                              "set, kept the best primary configuration at sixty three percent accuracy and sixty five macro F 1, "
                              "and swept the urgency threshold, which lifted urgency macro F 1 from ninety two point six to ninety three "
                              "point one. Every experiment, including the rejected ones, is saved in the repository."),
         ]),

    dict(id="results", kind="slide", layout="results",
         kicker="Evaluation scores",
         title="Development validation (800 tickets)",
         stats=[("63.0%", "category accuracy", "65.0 macro-F1"),
                ("95.5%", "secondary accuracy", "69.2 macro-F1"),
                ("97.5%", "urgency accuracy", "93.1 macro-F1"),
                ("800 / 800", "schema-valid", "official JSON Schemas")],
         bars=[("spam_irrelevant", 1.00), ("ride_trip_issue", 0.77), ("account_promo", 0.73),
               ("delivery_delay", 0.69), ("safety_conduct", 0.67), ("general_inquiry", 0.65),
               ("lost_item", 0.61), ("app_technical", 0.58), ("payment_refund", 0.58),
               ("food_quality", 0.51), ("order_missing_wrong", 0.38)],
         langs=[("Singlish", 0.905), ("Tanglish", 0.65), ("Tamil", 0.617), ("Mixed", 0.55), ("English", 0.539),
                ("Sinhala", 0.463)],
         items=["stats", "bars", "langs"],
         beats=[
             dict(show=1, say="These are the final scores on the eight hundred development validation tickets. "
                              "Category accuracy is sixty three percent, with sixty five macro F 1. Secondary category accuracy "
                              "is ninety five and a half percent, and urgency is ninety seven and a half percent with ninety three "
                              "macro F 1. All eight hundred predictions validate against the official JSON Schemas."),
             dict(show=2, say="Per category, spam is perfect, and ride, account and delivery issues are strong. The weakest is "
                              "order missing or wrong, which is most often confused with payment refund, since those customers "
                              "usually ask for their money back too."),
             dict(show=3, say="By language, Singlish is the strongest at over ninety percent, while Sinhala script is the hardest "
                              "at around forty six percent. We want to be clear: these are development scores, and the validation "
                              "set informed our tuning. The judges' unseen holdout is the real test."),
         ]),

    dict(id="demo_models", kind="live",
         beats=[
             dict(say="The Model lab page in the dashboard shows the same numbers, read directly from the loaded model "
                      "artifact on the server: the three classifiers, their algorithms, their classes and their validation "
                      "scores, together with the fixed routing table."),
         ]),

    # ---------------------------------------------------------------- 5. API & testing
    dict(id="api_auth", kind="terminal", file="auth.txt",
         kicker="Evaluation API · authentication",
         title="Key from the API_KEY environment variable, checked first",
         beats=[
             dict(show=1, say="Now the evaluation API, which the judges call directly. Health is public and needs no key."),
             dict(show=3, say="Every prediction and job endpoint requires the team API key. A missing key or a wrong key "
                              "returns four oh one, with a JSON error body and a W W W Authenticate header, before the request body is "
                              "even read."),
             dict(show=5, say="With the right key, in either the X API Key header or an Authorization Bearer header, we get the "
                              "prediction in exactly the contract's field names. The key is read from the API key environment variable "
                              "at startup, compared in constant time, never logged, and never sent to the browser. If no key is "
                              "configured, the service refuses requests instead of running open."),
         ]),

    dict(id="api_errors", kind="terminal", file="errors.txt",
         kicker="Evaluation API · robustness",
         title="Bad input gets a clean 4xx JSON error — never a 5xx",
         beats=[
             dict(show=2, say="Robustness is part of the scoring, so invalid input always gets a clean JSON error. "
                              "Malformed JSON gets four hundred. An unknown channel or empty text gets four twenty two, "
                              "with details for every failing field."),
             dict(show=4, say="A wrong content type gets four fifteen. In a batch, a duplicate ticket I D fails the whole "
                              "request with four twenty two, and the details carry the index of the bad item."),
             dict(show=5, say="Even unknown routes return JSON, never an HTML page or a stack trace."),
         ]),

    dict(id="api_jobs", kind="terminal", file="jobs.txt",
         kicker="Evaluation API · async batch jobs",
         title="Submit → poll → fetch results",
         beats=[
             dict(show=1, say="For large evaluation runs, the judges submit up to five thousand tickets as an asynchronous job. "
                              "We validate every ticket up front, then return two oh two with a job I D, a Location header and "
                              "Retry After. Sending the same Idempotency Key again returns the same job instead of creating a new one."),
             dict(show=2, say="Asking for results before the job has finished gives four oh nine."),
             dict(show=4, say="Polling the status shows the job succeeded with three thousand of three thousand processed. "
                              "Results come back in request order and can be paged with offset and limit."),
             dict(show=5, say="Unknown job I Ds give four oh four. Jobs are stored in SQLite and kept for twenty four hours, "
                              "well above the six hour minimum. We allow one running and three queued jobs, and if the container "
                              "restarts mid-job, the job ends as failed with the reason interrupted, instead of disappearing."),
         ]),

    dict(id="docker", kind="terminal", file="docker.txt",
         kicker="Container",
         title="Single docker run, no internet at runtime",
         beats=[
             dict(show=2, say="Next, the container. We build the image, then start it with networking completely disabled, "
                              "and the API key passed as an environment variable. It is healthy in about two seconds, "
                              "well inside the hundred and twenty second limit."),
             dict(show=4, say="Inside that offline container, health reports the loaded model, and a Sinhala ticket about a bag "
                              "left in a car is correctly routed to Lost and Found."),
             dict(show=5, say="And to prove there really is no network, a request to the internet from inside the container fails. "
                              "The model never needs it."),
         ]),

    dict(id="docker_run", kind="terminal", file="docker_run.txt",
         kicker="Container",
         title="The documented start command",
         beats=[
             dict(show=2, say="This is the documented single start command, docker run with the port mapping and the API key. "
                              "Health returns two hundred straight away."),
         ]),

    dict(id="tests", kind="terminal", file="tests.txt",
         kicker="How we tested it",
         title="Automated checks against the official contract",
         beats=[
             dict(show=1, say="Finally, how we tested all of this. Thirty nine automated tests cover the API, the job engine "
                              "and the contract. They validate responses against both the OpenAPI file and the organisers' "
                              "draft twenty twenty JSON Schemas."),
             dict(show=2, say="The evaluation script runs all eight hundred validation tickets and checks every prediction against "
                              "the official schemas: eight hundred out of eight hundred pass."),
             dict(show=3, say="And our Postman collection behaves like the judges' harness: thirty five requests covering correct, "
                              "wrong and missing keys, bad input, batches and a full async job, with over two thousand seven hundred "
                              "assertions, and zero failures. The same collection runs against the hosted URL."),
         ]),

    # ---------------------------------------------------------------- 6. Wrap-up
    dict(id="findings", kind="slide", layout="bullets",
         kicker="Findings and limitations",
         title="What we learned",
         items=[
             "Character n-grams carry multilingual text — one model, no translation",
             "Internal splits of synthetic data overstate accuracy; select on held-out data",
             "Primary category (63%) is the main limitation — order vs refund is the hardest boundary",
             "Sinhala-script tickets are the weakest language group",
             "Human review is conservative by design: 485 of 800 validation tickets flagged",
         ],
         beats=[
             dict(show=2, say="To wrap up, our main findings. Character n-grams let one small, fast model handle Sinhala, Tamil, "
                              "English and their Latin-script forms, with no translation step. And internal splits of synthetic "
                              "data badly overstate accuracy, so model selection has to use held-out data."),
             dict(show=4, say="We are also honest about the limits. Primary category accuracy of sixty three percent is the main "
                              "weakness, with missing-order versus refund being the hardest boundary, and Sinhala script being "
                              "the hardest language group."),
             dict(show=5, say="That is why Fresh Desk keeps people in the loop. Review is recommended conservatively, on four "
                              "hundred and eighty five of the eight hundred validation tickets, and a support agent always makes "
                              "the final routing decision for those."),
         ]),

    dict(id="close", kind="slide", layout="title",
         kicker="Thank you",
         title="Fresh Desk",
         subtitle="TensorForge 2.0 · Phase 2 MVP",
         items=["Repository: github.com/geemalfernando/tensorforge-phase2",
                "Report: docs/report.pdf", "Postman collection: postman/",
                "docker run -p 8000:8000 -e API_KEY=<key> <image>"],
         beats=[
             dict(show=4, say="Everything you have seen is in our repository: the training and evaluation scripts, the saved "
                              "experiments, the tests, the Postman collection, the Dockerfile and the report. The hosted "
                              "evaluation endpoint runs this same image. Thank you for watching."),
         ]),
]
