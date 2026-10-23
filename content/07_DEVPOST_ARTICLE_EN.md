## Inspiration

Great AI experiences begin with a useful question. For a student club planning its next event, that question can be wonderfully simple: “What is our total budget?”

We wanted to pair that everyday ease with the elegance of mathematics. OrbitSum brings the calculation, the encryption boundary, and the answer into one clear experience. A viewer can follow the journey from local budget values to an AI-generated plan, then celebrate the result revealed in the browser.

## What it does

OrbitSum is an encrypted budget workspace powered by Alibaba Cloud Qwen. Four synthetic club budgets—SGD 1,240.00, 1,860.00, 920.00, and 1,580.00—become a browser-verified total of **SGD 5,600.00** through a live AI planning run.

You choose a public budget question. Your browser encrypts each amount, and Qwen receives the encrypted amounts with a public key, public labels, and the allowed operations. The model translates the question into a structured calculation plan. The native evaluator applies the approved operation to ciphertext, and your browser uses its own decryption key to reveal the answer.

The experience makes each role visible: your browser holds the values and key, cloud AI plans the calculation, and the evaluator works with encrypted amounts. An evidence panel brings the request and the plan into view alongside the result.

## How we built it

We connected browser-based key generation and **2048-bit Paillier encryption** to Qwen's hosted API. A native **C/OpenSSL BIGNUM** evaluator uses Paillier's additive homomorphism to combine encrypted amounts into an encrypted total. The calculation returns to the browser for the final reveal.

The planner works within a defined operation schema for totals, averages, and campus budget comparisons. A validation step checks the model's response, record identifiers, weights, and divisor before evaluation, connecting flexible AI planning to a precise mathematical workflow. Decimal currency values are represented as exact integer cents.

The interface presents this journey in a clear sequence: prepare, encrypt, plan, calculate, and reveal. Its **Encrypted request**, **Validated plan**, and **Run receipt** views connect the user experience to the actual calculation record. A downloadable receipt identifies the provider, model, operation, result, and local verification.

## Engineering achievement

The defining design decision was to give every component a clear responsibility. The AI produces a structured plan. The evaluator applies approved ciphertext operations. The browser retains the decryption key and presents the result. That division makes the workflow easy to demonstrate and its behavior straightforward to inspect.

## Accomplishments we are proud of

- Completed a live **qwen-plus** planning run that combined four encrypted club budgets into a locally verified **SGD 5,600.00** total.
- Built a guided workspace that makes browser-held keys, ciphertext operations, and the result easy to follow.
- Connected public budget questions to structured, validated AI calculation plans.
- Implemented the encrypted arithmetic in **C/OpenSSL BIGNUM**, bringing the mathematical property into a working low-level evaluator.
- Passed **8 cryptography and currency checks** and **14 independent backend and request-boundary tests**.
- Captured the real interface, encrypted request package, returned plan, and downloadable run receipt for direct review.

## What we learned

A mathematical property becomes much easier to appreciate when people can use it. Showing the boundary, the plan, and the final result in one place gives the cryptography a clear purpose. We also learned how strongly a precise plan format connects a language model to a dependable calculation flow.

## What's next

We are excited to extend OrbitSum with richer budget templates, additional supported calculations, and more ways to explore the evidence behind each result. The next chapter builds on the same idea: useful AI planning, encrypted computation, and a clear result in your hands.
