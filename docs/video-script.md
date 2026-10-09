# Video walkthrough script

Narration for the Phase 2 walkthrough video, one section per scene. The start times match the generated MP4. To record the video in your own voice, read each section while its scene is on screen.

| Start | Scene | On screen |
| --- | --- | --- |
| 00:00 | Fresh Desk | Slide |
| 00:30 | One ticket in. Three predictions and a team out. | Slide |
| 01:16 | Our own trained classifiers — not an LLM wrapper | Slide |
| 01:53 | Two entry points, one model, one contract | Slide |
| 02:58 | Demo: intake | Live dashboard |
| 04:25 | Demo: ops | Live dashboard |
| 04:56 | Demo: batch | Live dashboard |
| 05:34 | Organiser data only, with provenance | Slide |
| 06:14 | Three pipelines, tuned separately | Slide |
| 07:19 | What we tried, what we kept, what we rejected | Slide |
| 08:26 | Development validation (800 tickets) | Slide |
| 09:17 | Demo: models | Live dashboard |
| 09:34 | Key from the API_KEY environment variable, checked first | Terminal capture |
| 10:15 | Bad input gets a clean 4xx JSON error — never a 5xx | Terminal capture |
| 10:44 | Submit → poll → fetch results | Terminal capture |
| 11:32 | Single docker run, no internet at runtime | Terminal capture |
| 12:02 | The documented start command | Terminal capture |
| 12:11 | Automated checks against the official contract | Terminal capture |
| 12:51 | What we learned | Slide |
| 13:34 | Fresh Desk | Slide |

Total length: 13:50.

## 00:00 — Fresh Desk

Hello, and welcome to our TensorForge 2.0 Phase 2 walkthrough. This is Fresh Desk: a customer support ticket classification and routing system for RideEat, the fictional ride-hailing and food delivery platform in the brief.

In the next fifteen minutes we will show the working solution, explain the architecture, walk through how our three machine learning models were trained, validated and improved, and show exactly how we tested the authenticated evaluation API against the official contract.

## 00:30 — One ticket in. Three predictions and a team out.

Each ticket arrives with a channel, which is email, chat or call transcript, an optional subject, and free text. The text can be English, Sinhala, Tamil, Sinhala or Tamil typed in Latin script, emojis, or a mix of all of these. First, we predict the primary category, one of eleven values.

Second, a secondary category when the ticket clearly contains two issues, otherwise null. And third, whether the ticket is urgent and needs immediate human attention.

The team is not predicted. It is derived from the category using the fixed table on the right, exactly as the contract defines it. The contract also adds consistency rules: the secondary category must differ from the primary, and spam is never urgent and never has a secondary category.

## 01:16 — Our own trained classifiers — not an LLM wrapper

The guidelines are clear that simply wrapping a large language model is discouraged. So every prediction in Fresh Desk comes from classifiers we trained ourselves: TF-IDF features over words and characters, feeding linear models, trained only on the four thousand labelled tickets supplied by the organisers.

We train three separate models, one for each prediction target. The fitted pipelines are saved as a single artifact and baked into the Docker image, so inference needs no internet, no model download and no external AI service. And every response is checked against the official OpenAPI contract and JSON Schemas.

## 01:53 — Two entry points, one model, one contract

Here is the architecture. There are two ways in. On the left, the judges' evaluation harness calls the API directly with the team API key. Below it, the Fresh Desk dashboard in the browser. The browser never holds the key: it calls a same-origin dashboard route, and the server attaches the key internally.

Every protected request goes through the same checks, in the order the contract requires: authentication first, then content type, then payload size, then JSON parsing, and finally field validation. An unauthorised request never reaches the parser or the model.

Valid tickets go to the ticket model: the three trained pipelines, plus the fixed category to team map and the consistency rules. The single and small batch endpoints run this synchronously.

Large evaluation runs use asynchronous jobs. The request is validated up front, stored in SQLite, and a background worker classifies the tickets, so health checks and live predictions stay responsive.

All of this ships as one Docker image that starts with a single docker run command and runs with no network access at all.

## 02:58 — Demo: intake

Let's see it working. This is the Fresh Desk home page, running locally from the same FastAPI server that serves the API. The status pill in the top right confirms the model is loaded and the service is ready.

We open the desk and create a live chat ticket in Singlish: Sinhala typed with English letters. The customer says their order is an hour late, the driver won't answer, and they want a refund.

The prediction comes back in milliseconds. Primary category: delivery delay, routed to Delivery Operations. Secondary category: payment refund, because the customer also asked for their money back. And the urgency model flags it as urgent: the customer has waited an hour and cannot reach the driver.

Next, a safety case. A passenger says the driver is not stopping the car, and they are scared. The model routes it to Trust and Safety, with high confidence, and raises the urgent flag.

Now a message in Tamil script, about an item missing from an order and a request for the money back. It goes to Food Operations, with payment refund as the secondary issue. Confidence here is low, so the ticket is flagged for human review. There is no translation step: character n-gram features let one model read Sinhala, Tamil and English scripts directly.

And finally an email, with a subject line. The customer's diabetic father is waiting on an insulin delivery and the rider's phone is off. Even though the email is written politely, the urgency model picks up that this needs immediate attention.

## 04:25 — Demo: ops

Every classified ticket lands in Live operations, a running view of routes, urgency and review status for the session.

Urgent or low-confidence tickets go to the Support queue. Support staff sign in with a separate server-side password. The customer role cannot accept or reroute tickets.

A support agent reviews the model's signals and accepts the ticket, or picks a different team and must give a reason for the override. The model's original prediction is never changed: the human decision is stored next to it.

## 04:56 — Demo: batch

The Batch workbench is the evaluation path in the dashboard. Up to one hundred tickets run synchronously, through the predict batch endpoint. Here is the sample batch.

The predictions come back in the same order as the request, each one echoing its ticket ID.

Now an evaluation-sized run. We paste three thousand tickets. Above one hundred tickets, the workbench switches to an asynchronous batch job: it submits, polls the job status, and fetches the results when the job has succeeded.

All three thousand predictions are back, in order, and can be downloaded as JSON in the same format the judges receive from the API.

## 05:34 — Organiser data only, with provenance

Now, how the models were built. We used only the organisers' data: four thousand training tickets and eight hundred validation tickets. The archive was downloaded from the official Drive folder, and the SHA-256 checksum of every file is recorded in the repository.

The models see only what the API will see at evaluation time: channel, subject and text. We deliberately excluded ticket IDs and the language labels in the dataset, because the judges' requests never contain them, and a model that relied on them would fail on the holdout.

The validation set covers six language styles, from English and Singlish to Sinhala and Tamil script, with smaller Tanglish and mixed-script groups.

## 06:14 — Three pipelines, tuned separately

Each target has its own pipeline. The category model is a class-balanced logistic regression over word unigrams and bigrams plus word-boundary character n-grams of length two to six. Character n-grams are what make the model work across scripts and spelling variants, such as the many ways people type Singlish.

The secondary category model is a linear support vector machine with sigmoid calibration, so we get usable probabilities. A secondary category is only returned when its probability is above zero point two and it differs from the primary.

The urgency model is another balanced logistic regression on character n-grams, with a decision threshold of zero point three, chosen to favour catching urgent tickets. For secondary and urgency we apply light cleanup: normalising whitespace and removing quoted earlier correspondence and synthetic reference numbers.

After the models, fixed rules enforce the contract: the team comes from the category table, spam is never urgent, and the secondary category cannot repeat the primary. When confidence is below fifty percent or the message is three words or fewer, we recommend human review.

## 07:19 — What we tried, what we kept, what we rejected

Here is how the models were validated and improved, including what did not work. We started from a baseline at sixty two point nine percent category accuracy.

Our first round of tuning used an internal split of the training data, where every candidate scored ninety-eight to ninety-nine percent. That was a warning sign: the synthetic training tickets are very similar to each other. Sure enough, the candidate we picked there dropped to sixty point nine percent on the development validation set. So we stopped trusting the internal split for selection.

We also tried stripping greeting and sign-off boilerplate from the text. It sounded sensible, but accuracy fell to around fifty six percent, so we rejected it. Those polite phrases turn out to carry signal.

We then compared regularisation strengths, class weighting and feature settings on the development set, kept the best primary configuration at sixty three percent accuracy and sixty five macro-F1, and swept the urgency threshold, which lifted urgency macro-F1 from ninety two point six to ninety three point one. Every experiment, including the rejected ones, is saved in the repository.

## 08:26 — Development validation (800 tickets)

These are the final scores on the eight hundred development validation tickets. Category accuracy is sixty three percent, with sixty five macro-F1. Secondary category accuracy is ninety five and a half percent, and urgency is ninety seven and a half percent with ninety three macro-F1. All eight hundred predictions validate against the official JSON Schemas.

Per category, spam is perfect, and ride, account and delivery issues are strong. The weakest is order missing or wrong, which is most often confused with payment refund, since those customers usually ask for their money back too.

By language, Singlish is the strongest at over ninety percent, while Sinhala script is the hardest at around forty six percent. We want to be clear: these are development scores, and the validation set informed our tuning. The judges' unseen holdout is the real test.

## 09:17 — Demo: models

The Model lab page in the dashboard shows the same numbers, read directly from the loaded model artifact on the server: the three classifiers, their algorithms, their classes and their validation scores, together with the fixed routing table.

## 09:34 — Key from the API_KEY environment variable, checked first

Now the evaluation API, which the judges call directly. Health is public and needs no key.

Every prediction and job endpoint requires the team API key. A missing key or a wrong key returns 401, with a JSON error body and a WWW-Authenticate header, before the request body is even read.

With the right key, in either the X-API-Key header or an Authorization Bearer header, we get the prediction in exactly the contract's field names. The key is read from the API_KEY environment variable at startup, compared in constant time, never logged, and never sent to the browser. If no key is configured, the service refuses requests instead of running open.

## 10:15 — Bad input gets a clean 4xx JSON error — never a 5xx

Robustness is part of the scoring, so invalid input always gets a clean JSON error. Malformed JSON gets 400. An unknown channel or empty text gets 422, with details for every failing field.

A wrong content type gets 415. In a batch, a duplicate ticket ID fails the whole request with 422, and the details carry the index of the bad item.

Even unknown routes return JSON, never an HTML page or a stack trace.

## 10:44 — Submit → poll → fetch results

For large evaluation runs, the judges submit up to five thousand tickets as an asynchronous job. We validate every ticket up front, then return 202 with a job ID, a Location header and Retry-After. Sending the same Idempotency-Key again returns the same job instead of creating a new one.

Asking for results before the job has finished gives 409.

Polling the status shows the job succeeded with three thousand of three thousand processed. Results come back in request order and can be paged with offset and limit.

Unknown job IDs give 404. Jobs are stored in SQLite and kept for twenty four hours, well above the six hour minimum. We allow one running and three queued jobs, and if the container restarts mid-job, the job ends as failed with the reason interrupted, instead of disappearing.

## 11:32 — Single docker run, no internet at runtime

Next, the container. We build the image, then start it with networking completely disabled, and the API key passed as an environment variable. It is healthy in about two seconds, well inside the hundred and twenty second limit.

Inside that offline container, health reports the loaded model, and a Sinhala ticket about a bag left in a car is correctly routed to Lost and Found.

And to prove there really is no network, a request to the internet from inside the container fails. The model never needs it.

## 12:02 — The documented start command

This is the documented single start command, docker run with the port mapping and the API key. Health returns 200 straight away.

## 12:11 — Automated checks against the official contract

Finally, how we tested all of this. Thirty nine automated tests cover the API, the job engine and the contract. They validate responses against both the OpenAPI file and the organisers' draft 2020-12 JSON Schemas.

The evaluation script runs all eight hundred validation tickets and checks every prediction against the official schemas: eight hundred out of eight hundred pass.

And our Postman collection behaves like the judges' harness: thirty five requests covering correct, wrong and missing keys, bad input, batches and a full async job, with over two thousand seven hundred assertions, and zero failures. The same collection runs against the hosted URL.

## 12:51 — What we learned

To wrap up, our main findings. Character n-grams let one small, fast model handle Sinhala, Tamil, English and their Latin-script forms, with no translation step. And internal splits of synthetic data badly overstate accuracy, so model selection has to use held-out data.

We are also honest about the limits. Primary category accuracy of sixty three percent is the main weakness, with missing-order versus refund being the hardest boundary, and Sinhala script being the hardest language group.

That is why Fresh Desk keeps people in the loop. Review is recommended conservatively, on 485 of the eight hundred validation tickets, and a support agent always makes the final routing decision for those.

## 13:34 — Fresh Desk

Everything you have seen is in our repository: the training and evaluation scripts, the saved experiments, the tests, the Postman collection, the Dockerfile and the report. The hosted evaluation endpoint runs this same image. Thank you for watching.
