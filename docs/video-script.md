# Video walkthrough script

Narration for the Phase 2 walkthrough video, one section per scene. The start times match the generated MP4. To record the video in your own voice, read each section while its scene is on screen.

| Start | Scene | On screen |
| --- | --- | --- |
| 00:00 | Fresh Desk | Slide |
| 00:27 | One ticket in. Three predictions and a team out. | Slide |
| 01:09 | Our own trained classifiers — not an LLM wrapper | Slide |
| 01:43 | Two entry points, one model, one contract | Slide |
| 02:50 | Demo: intake | Live dashboard |
| 04:15 | Demo: ops | Live dashboard |
| 04:56 | Demo: judge | Live dashboard |
| 05:50 | Demo: batch | Live dashboard |
| 06:41 | The same desk, in your pocket | Live dashboard |
| 07:23 | Organiser data only, with provenance | Slide |
| 08:00 | Three pipelines, tuned separately | Slide |
| 09:00 | What we tried, what we kept, what we rejected | Slide |
| 10:01 | Development validation (800 tickets) | Slide |
| 10:47 | Key from the API_KEY environment variable, checked first | Terminal capture |
| 11:24 | Bad input gets a clean 4xx JSON error — never a 5xx | Terminal capture |
| 11:50 | Submit → poll → fetch results | Terminal capture |
| 12:34 | Single docker run, no internet at runtime | Terminal capture |
| 13:01 | The documented start command | Terminal capture |
| 13:10 | Automated checks against the official contract | Terminal capture |
| 13:46 | What we learned | Slide |
| 14:25 | Fresh Desk | Slide |

Total length: 14:40.

## 00:00 — Fresh Desk

Hello, and welcome to our TensorForge 2.0 Phase 2 walkthrough. This is Fresh Desk: a customer support ticket classification and routing system for RideEat, the fictional ride-hailing and food delivery platform in the brief.

In the next fifteen minutes we will show the working solution, explain the architecture, walk through how our three machine learning models were trained, validated and improved, and show exactly how we tested the authenticated evaluation API against the official contract.

## 00:27 — One ticket in. Three predictions and a team out.

Each ticket arrives with a channel, which is email, chat or call transcript, an optional subject, and free text. The text can be English, Sinhala, Tamil, Sinhala or Tamil typed in Latin script, emojis, or a mix of all of these. First, we predict the primary category, one of eleven values.

Second, a secondary category when the ticket clearly contains two issues, otherwise null. And third, whether the ticket is urgent and needs immediate human attention.

The team is not predicted. It is derived from the category using the fixed table on the right, exactly as the contract defines it. The contract also adds consistency rules: the secondary category must differ from the primary, and spam is never urgent and never has a secondary category.

## 01:09 — Our own trained classifiers — not an LLM wrapper

The guidelines are clear that simply wrapping a large language model is discouraged. So every prediction in Fresh Desk comes from classifiers we trained ourselves: TF-IDF features over words and characters, feeding linear models, trained only on the four thousand labelled tickets supplied by the organisers.

We train three separate models, one for each prediction target. The fitted pipelines are saved as a single artifact and baked into the Docker image, so inference needs no internet, no model download and no external AI service. And every response is checked against the official OpenAPI contract and JSON Schemas.

## 01:43 — Two entry points, one model, one contract

Here is the architecture. There are two ways in. On the left, the judges' evaluation harness calls the API directly with the team API key. Below it, Fresh Desk has a regular workspace and a separate Judge demo console. The regular workspace uses a same-origin server bridge, so the configured server key never reaches the browser. In the Judge console, the evaluator enters their own key; it is verified by the API and held in page memory only until sign-out.

Every protected request goes through the same checks, in the order the contract requires: authentication first, then content type, then payload size, then JSON parsing, and finally field validation. An unauthorised request never reaches the parser or the model.

Valid tickets go to the ticket model: the three trained pipelines, plus the fixed category to team map and the consistency rules. The single and small batch endpoints run this synchronously.

Large evaluation runs use asynchronous jobs. The request is validated up front, stored in SQLite, and a background worker classifies the tickets, so health checks and live predictions stay responsive.

All of this ships as one Docker image that starts with a single docker run command and runs with no network access at all.

## 02:50 — Demo: intake

Let's see it working. This is the Fresh Desk home page, live on our hosted site at tensorforge-phase2.vercel.app, served by the same FastAPI app as the API. The status pill in the top right confirms the model is loaded and the service is ready.

We open the desk and create a live chat ticket in Singlish: Sinhala typed with English letters. The customer says their order is an hour late, the driver won't answer, and they want a refund.

The prediction comes straight back. Primary category: delivery delay, routed to Delivery Operations. Secondary category: payment refund, because the customer also asked for their money back. The urgency model marks it standard priority. Primary confidence is only thirty one percent, so Fresh Desk recommends human review before the ticket is routed.

Next, a safety case. A passenger says the driver is not stopping the car, and they are scared. The model routes it to Trust and Safety, with ninety six percent confidence, and raises the urgent flag, so the ticket waits for a support agent to approve it.

Now a message in Tamil script, about an item missing from an order and a request for the money back. It goes to Food Operations, with payment refund as the secondary issue. Confidence here is low, so the ticket is flagged for human review. There is no translation step: character n-gram features let one model read Sinhala, Tamil and English scripts directly.

## 04:15 — Demo: ops

Every classified ticket lands in Live operations, a running view of routes, urgency and review status for the session.

Urgent or low-confidence tickets go to the Support queue. Support staff sign in with a separate server-side password. The customer role cannot accept or reroute tickets.

A support agent reviews the model's signals and accepts the ticket, or picks a different team and must give a reason for the override. The model's original prediction is never changed: the human decision is stored next to it.

## 04:56 — Demo: judge

Next in the navigation is the Judge demo, built for evaluators. It gathers the evidence in one place: the live site, the hosted API, the contract tests, the repository, the offline Docker run, training and evaluation, the report, and this walkthrough.

Below the checklist is every route in the evaluation contract, from the public health check to the authenticated prediction and job endpoints, with a link to the raw Open A P I specification.

Judges sign in with their own evaluation key. The page checks it with the auth verify endpoint, and keeps it in page memory only, never in browser storage.

The console then calls the real API. Here is a single prediction, with the full contract-shaped JSON response.

And a synchronous batch, with one prediction per ticket ID, in order. From the same console, judges can also submit an asynchronous job, poll it, fetch its results, or cancel it.

## 05:50 — Demo: batch

The Batch workbench is the evaluation path in the dashboard. Up to one hundred tickets run synchronously, through the predict batch endpoint. Here is the sample batch.

The predictions come back in the same order as the request, each one echoing its ticket ID.

Now a full synchronous batch: we paste one hundred tickets, the largest batch the predict batch endpoint accepts. Anything larger, up to five thousand tickets, becomes an asynchronous batch job, which we show through the API later in this video.

All one hundred predictions are back, in order, and can be downloaded as JSON in the same format the judges receive from the API.

## 06:41 — The same desk, in your pocket

Fresh Desk is also fully responsive. Here is the same hosted site on a phone. The header, navigation and landing page reflow into a single column, with nothing hidden away.

Support staff and customers can raise a ticket from their phone. This customer says the driver took a long route, charged them double, and wants a refund.

The full prediction fits the small screen: Ride Operations as the route, ride trip issue as the primary category, payment refund as the secondary issue, and standard priority. Confidence is above fifty percent, so the ticket is routed automatically.

## 07:23 — Organiser data only, with provenance

Now, how the models were built. We used only the organisers' data: four thousand training tickets and eight hundred validation tickets. The archive was downloaded from the official Drive folder, and the SHA-256 checksum of every file is recorded in the repository.

The models see only what the API will see at evaluation time: channel, subject and text. We deliberately excluded ticket IDs and the language labels in the dataset, because the judges' requests never contain them, and a model that relied on them would fail on the holdout.

The validation set covers six language styles, from English and Singlish to Sinhala and Tamil script, with smaller Tanglish and mixed-script groups.

## 08:00 — Three pipelines, tuned separately

Each target has its own pipeline. The category model is a class-balanced logistic regression over word unigrams and bigrams plus word-boundary character n-grams of length two to six. Character n-grams are what make the model work across scripts and spelling variants, such as the many ways people type Singlish.

The secondary category model is a linear support vector machine with sigmoid calibration, so we get usable probabilities. A secondary category is only returned when its probability is above zero point two and it differs from the primary.

The urgency model is another balanced logistic regression on character n-grams, with a decision threshold of zero point three, chosen to favour catching urgent tickets. For secondary and urgency we apply light cleanup: normalising whitespace and removing quoted earlier correspondence and synthetic reference numbers.

After the models, fixed rules enforce the contract: the team comes from the category table, spam is never urgent, and the secondary category cannot repeat the primary. When confidence is below fifty percent or the message is three words or fewer, we recommend human review.

## 09:00 — What we tried, what we kept, what we rejected

Here is how the models were validated and improved, including what did not work. We started from a baseline at sixty two point nine percent category accuracy.

Our first round of tuning used an internal split of the training data, where every candidate scored ninety-eight to ninety-nine percent. That was a warning sign: the synthetic training tickets are very similar to each other. Sure enough, the candidate we picked there dropped to sixty point nine percent on the development validation set. So we stopped trusting the internal split for selection.

We also tried stripping greeting and sign-off boilerplate from the text. It sounded sensible, but accuracy fell to around fifty six percent, so we rejected it. Those polite phrases turn out to carry signal.

We then compared regularisation strengths, class weighting and feature settings on the development set, kept the best primary configuration at sixty three percent accuracy and sixty five macro-F1, and swept the urgency threshold, which lifted urgency macro-F1 from ninety two point six to ninety three point one. Every experiment, including the rejected ones, is saved in the repository.

## 10:01 — Development validation (800 tickets)

These are the final scores on the eight hundred development validation tickets. Category accuracy is sixty three percent, with sixty five macro-F1. Secondary category accuracy is ninety five and a half percent, and urgency is ninety seven and a half percent with ninety three macro-F1. All eight hundred predictions validate against the official JSON Schemas.

Per category, spam is perfect, and ride, account and delivery issues are strong. The weakest is order missing or wrong, which is most often confused with payment refund, since those customers usually ask for their money back too.

By language, Singlish is the strongest at over ninety percent, while Sinhala script is the hardest at around forty six percent. We want to be clear: these are development scores, and the validation set informed our tuning. The judges' unseen holdout is the real test.

## 10:47 — Key from the API_KEY environment variable, checked first

Now the evaluation API, which the judges call directly. Health is public and needs no key.

Every prediction and job endpoint requires the team API key. A missing key or a wrong key returns 401, with a JSON error body and a WWW-Authenticate header, before the request body is even read.

With the right key, in either the X-API-Key header or an Authorization Bearer header, we get the prediction in exactly the contract's field names. The key is read from the API_KEY environment variable at startup, compared in constant time, never logged, and never sent to the browser. If no key is configured, the service refuses requests instead of running open.

## 11:24 — Bad input gets a clean 4xx JSON error — never a 5xx

Robustness is part of the scoring, so invalid input always gets a clean JSON error. Malformed JSON gets 400. An unknown channel or empty text gets 422, with details for every failing field.

A wrong content type gets 415. In a batch, a duplicate ticket ID fails the whole request with 422, and the details carry the index of the bad item.

Even unknown routes return JSON, never an HTML page or a stack trace.

## 11:50 — Submit → poll → fetch results

For large evaluation runs, the judges submit up to five thousand tickets as an asynchronous job. We validate every ticket up front, then return 202 with a job ID, a Location header and Retry-After. Sending the same Idempotency-Key again returns the same job instead of creating a new one.

Asking for results before the job has finished gives 409.

Polling the status shows the job succeeded with three thousand of three thousand processed. Results come back in request order and can be paged with offset and limit.

Unknown job IDs give 404. Jobs are stored in SQLite and kept for twenty four hours, well above the six hour minimum. We allow one running and three queued jobs, and if the container restarts mid-job, the job ends as failed with the reason interrupted, instead of disappearing.

## 12:34 — Single docker run, no internet at runtime

Next, the container. We build the image, then start it with networking completely disabled, and the API key passed as an environment variable. It is healthy in about two seconds, well inside the hundred and twenty second limit.

Inside that offline container, health reports the loaded model, and a Sinhala ticket about a bag left in a car is correctly routed to Lost and Found.

And to prove there really is no network, a request to the internet from inside the container fails. The model never needs it.

## 13:01 — The documented start command

This is the documented single start command, docker run with the port mapping and the API key. Health returns 200 straight away.

## 13:10 — Automated checks against the official contract

Finally, how we tested all of this. Thirty nine automated tests cover the API, the job engine and the contract. They validate responses against both the OpenAPI file and the organisers' draft 2020-12 JSON Schemas.

The evaluation script runs all eight hundred validation tickets and checks every prediction against the official schemas: eight hundred out of eight hundred pass.

And our Postman collection behaves like the judges' harness: thirty five requests covering correct, wrong and missing keys, bad input, batches and a full async job, with over two thousand seven hundred assertions, and zero failures. The same collection runs against the hosted URL.

## 13:46 — What we learned

To wrap up, our main findings. Character n-grams let one small, fast model handle Sinhala, Tamil, English and their Latin-script forms, with no translation step. And internal splits of synthetic data badly overstate accuracy, so model selection has to use held-out data.

We are also honest about the limits. Primary category accuracy of sixty three percent is the main weakness, with missing-order versus refund being the hardest boundary, and Sinhala script being the hardest language group.

That is why Fresh Desk keeps people in the loop. Review is recommended conservatively, on 485 of the eight hundred validation tickets, and a support agent always makes the final routing decision for those.

## 14:25 — Fresh Desk

Everything you have seen is in our repository: the training and evaluation scripts, the saved experiments, the tests, the Postman collection, the Dockerfile and the report. The hosted evaluation endpoint runs this same image. Thank you for watching.
