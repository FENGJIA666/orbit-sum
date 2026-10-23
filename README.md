# OrbitSum

**Shared insight. Private inputs.** OrbitSum turns student club budgets into a shared planning number with browser-owned Paillier encryption, a hosted AI planner and a C/OpenSSL encrypted arithmetic worker.

Four synthetic budgets — **SGD 1,240.00, 1,860.00, 920.00 and 1,580.00** — produce a **SGD 5,600.00 total**, **SGD 1,400.00 average**, or **SGD 600.00 North-minus-South comparison**. Edit the amounts and generate a new verified result.

## Run locally

Requirements: Python 3.10+, a modern browser, and Node.js 22+ for tests. The native evaluator uses a C compiler and OpenSSL development headers.

~~~sh
python3 scripts/build_native.py
python3 src/server.py
~~~

Open **http://127.0.0.1:8765**. The server binds exclusively to the loopback interface. Local planner mode runs the complete encryption, computation and browser decryption workflow with no API configuration.

The native build script supports Homebrew OpenSSL at its standard Apple Silicon location and system OpenSSL on other platforms. When the helper is present, the receipt identifies **C / OpenSSL BIGNUM**; the portable Python evaluator identifies itself separately.

## Connect a hosted AI planner

The adapter supports the official OpenAI and Alibaba Cloud DashScope compatible endpoints. Provide your approved configuration as environment variables:

~~~sh
export ORBITSUM_ENABLE_HOSTED=1
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4.1-mini
# Set OPENAI_API_KEY securely in your shell environment.
python3 src/server.py
~~~

For Qwen, use https://dashscope.aliyuncs.com/compatible-mode/v1 as OPENAI_BASE_URL and qwen-plus as OPENAI_MODEL.

An existing configuration can be loaded without copying its credentials into the project:

~~~sh
python3 scripts/start_hosted.py --env-file /path/to/approved.env --provider qwen
~~~

This reads only the selected provider's QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL (or corresponding OPENAI_ variables), loads them into process memory, and starts the local server. It uses full TLS certificate verification and never prints the configuration values.

Hosted mode uses the selected provider's metered API. Each press of **Generate encrypted insight** makes one hosted planning request. The UI and downloadable receipt identify the actual provider, model, usage, timing and live/local mode.

## The workflow

1. **Local workspace.** WebCrypto generates a 2048-bit RSA key pair locally; the browser uses its primes to derive the standard Paillier parameters. Decimal amounts become exact integer cents. A fresh random factor seals each contribution.
2. **Encrypted AI workflow.** The hosted model receives a public natural-language question, the operation vocabulary, public campus labels, public key and ciphertexts. It translates the question into a bounded JSON arithmetic plan.
3. **Validated computation.** The backend checks the plan against the user's selected intent, exact record IDs, approved coefficients and divisor. The native C worker multiplies ciphertexts modulo n²; comparison uses modular inversion for public −1 weights. The aggregate is re-randomized.
4. **Results.** The browser decrypts the returned aggregate and divides by the public count for an average. It compares the result with the local synthetic fixture and enables a downloadable run receipt.

The inspector offers **Encrypted request**, **Validated plan** and **Run receipt** tabs. The request tab is the same public envelope used in the provider's user message.

## Mathematics

For n = pq, g = n + 1, and a random r coprime to n:

~~~text
E(m; r) = g^m · r^n mod n²
E(a) · E(b) mod n² = E(a + b)
E(a)^k mod n² = E(k · a), for a public integer k
λ = lcm(p − 1, q − 1)
μ = λ⁻¹ mod n
D(c) = L(c^λ mod n²) · μ mod n, where L(x) = (x − 1) / n
~~~

The implementation uses **additive homomorphic encryption**. Budget amounts are supported from SGD 0.00 to SGD 10,000.00. The service accepts 2–32 encrypted records, and the UI presents four synthetic clubs. Approved coefficients are +1 and −1; with the supported input domain, the absolute aggregate is at most 32,000,000 cents, far below n/3. Signed decoding uses the centred modular representation. Average results retain the exact numerator and divisor in the receipt; the four-club UI displays up to four currency decimal places.

Reference: [Pascal Paillier, Public-Key Cryptosystems Based on Composite Degree Residuosity Classes, EUROCRYPT 1999](https://doi.org/10.1007/3-540-48910-X_16).

## Trust boundary

The local workspace brings four synthetic club budgets into one browser. Browser code holds the amounts and private parameters in memory. The Python service and hosted provider receive only the approved public envelope; they never receive p, q, λ, μ or individual plaintext amounts. Public metadata includes the selected question, record count, IDs, campus group and public key.

The local browser and code serving it are trusted. Paillier provides encrypted arithmetic; the exact plan validator and local result comparison provide the demonstration's operation checks. The public-key input validator checks shape, size and group membership. The service accepts only approved fields, operations, endpoints and record structures, uses bounded request sizes, and rejects foreign browser origins and Host headers. It stores no application database or request-body logs.

## Verify

~~~sh
python3 scripts/verify.py
~~~

This compiles the native helper, checks browser arithmetic and money conversion, runs the independent backend and HTTP boundary suite, and writes evidence/local-verification.json with check outputs and source SHA-256 fingerprints. Tests create fresh ephemeral synthetic keys in memory. They exercise exact totals, averages, signed differences, native cancellation, randomized ciphertexts, malformed values, extra fields, unapproved plans, provider envelope consistency and loopback request controls.

Live provider receipts and visual captures are separate evidence from local verification.

## Project map

- web/paillier.js — browser key generation, integer arithmetic, money conversion, encryption and decryption.
- web/app.js, web/index.html, web/style.css — the interactive collaboration workspace.
- src/engine.py — public-envelope construction, hosted planner, validation and keyless evaluation.
- src/aggregate.c — OpenSSL BIGNUM ciphertext multiplication and modular inversion.
- src/server.py — loopback HTTP service.
- scripts/start_hosted.py — selected local configuration loader.
- tests/ — browser and independently authored adversarial boundary checks.
