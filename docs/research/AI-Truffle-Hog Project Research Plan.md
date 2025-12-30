# **Architectural Blueprint for AI-Enhanced Secret Detection: A Hybrid Approach**

## **Executive Summary**

The modern software supply chain is increasingly defined by the proliferation of secrets—API keys, cryptographic tokens, database credentials, and private certificates—that act as the keys to the digital kingdom. As development velocity accelerates and infrastructure becomes defined as code, the accidental committal of these secrets into version control systems (VCS) has become an endemic vulnerability. Traditional remediation strategies have relied heavily on two deterministic mechanisms: Regular Expressions (Regex) for pattern matching and Shannon Entropy analysis for detecting high-randomness strings. While these methods offer high recall, ensuring that most obvious secrets are detected, they suffer from a debilitating precision problem. Security teams are frequently overwhelmed by false positives—random hashes, compiled binary artifacts, and test data—that statistically resemble secrets but lack security significance. This "alert fatigue" often leads to the disabling of safety checks, leaving organizations exposed.

This report presents a comprehensive architectural specification for "AI TruffleHog," a proposed next-generation secret scanning tool designed to bridge the gap between deterministic speed and semantic understanding. By hybridizing the robust history-mining capabilities of established tools like TruffleHog and Gitleaks with the contextual reasoning of Small Language Models (SLMs) and efficient NLP techniques, this project aims to drastically reduce false positives without sacrificing recall.

The proposed architecture leverages a **Python-based CLI** built on **Typer** for ergonomic developer interaction, supporting both targeted single-repository scans and bulk organizational audits. It utilizes **PyDriller** for memory-efficient traversal of complex Git histories, enabling the detection of secrets that may have been deleted in subsequent commits. The core innovation lies in the integration of **SetFit**, a few-shot learning framework that fine-tunes Sentence Transformers to distinguish between actual credentials and benign high-entropy strings based on surrounding code context (e.g., variable assignment, file paths, and comments). To ensure the tool remains lightweight and deployable on standard developer hardware, the AI components are optimized using **ONNX Runtime** and **INT8 quantization**, removing the dependency on heavy machine learning frameworks like PyTorch in the final distribution.

Furthermore, the system is designed for enterprise interoperability, mandating **SARIF (Static Analysis Results Interchange Format)** for log generation, ensuring seamless integration with GitHub Advanced Security, DefectDojo, and other vulnerability management platforms. The report also details extension pathways, including **pre-commit hooks** for "shift-left" prevention and **CI/CD integration** for continuous monitoring. By synthesizing findings from academic research on transformer-based vulnerability detection and practical documentation from industry-standard tools, this document serves as a foundational blueprint for developing a high-precision, AI-augmented secret scanner.

## ---

**1\. The Operational Context: Limitations of Legacy Scanning**

To understand the necessity of an AI-driven approach, one must first analyze the deficiencies of the current state-of-the-art. The domain of secret scanning is currently dominated by tools that prioritize speed and determinism over semantic understanding. While effective for simple patterns, this approach fails in complex, modern codebases.

### **1.1 The Deterministic Trap: Regex and Entropy**

Tools such as **TruffleHog** and **Gitleaks** have set the standard for secret detection. Their primary detection engine relies on regular expressions. For example, an AWS Access Key ID has a distinct, documented format (AKIA followed by 16 alphanumeric characters). A regex engine can identify this with 100% precision. However, the vast majority of modern secrets—SaaS API tokens, private keys, and internal service credentials—do not follow a standardized prefix or format.

To catch these "generic" secrets, tools employ **Shannon Entropy**. This mathematical concept measures the unpredictability of data. A cryptographic key appears highly random (high entropy), whereas English text is predictable (low entropy).

* **The False Positive Dilemma:** The fundamental flaw in entropy-based detection is that "randomness" is not unique to secrets. A Git commit hash, a UUID, a compiled bytecode string, or even a hardcoded CSS color gradient can exhibit high entropy levels indistinguishable from a high-value API token. Research indicates that tools relying solely on regex and entropy can suffer from false positive rates exceeding 80%.1 This forces security engineers to manually triage thousands of findings, a process that is both expensive and error-prone.  
* **The Context Blind Spot:** A deterministic scanner sees the string 12345abcdef as a potential secret regardless of whether it is assigned to stripe\_api\_key (a critical vulnerability) or background\_image\_id (benign). It lacks the capacity to read the *context*—the variable names, the file extension, the surrounding comments—that a human reviewer would use to determine validity.2

### **1.2 The Emergence of Semantic Analysis**

The industry has begun to recognize the need for "code-aware" scanning. The **OWASP DeepSecrets** project represents an early attempt to move beyond simple text parsing.3 DeepSecrets introduces "semantic analysis" by lexing the code to identify variable assignments and assess the risk based on the variable name (e.g., flagging assignments to variables containing "password" or "secret"). This significantly reduces noise compared to raw entropy scanning.

However, DeepSecrets and similar heuristic-based tools (like **detect-secrets**) still rely on manually crafted rules and heuristic scoring. They do not leverage the probabilistic reasoning capabilities of modern machine learning, which can learn subtle, non-linear patterns in code structure that define a "secret" versus a "non-secret".3 The "AI TruffleHog" project aims to supersede these heuristic approaches by embedding a trained neural network that can generalize from examples, effectively learning the "shape" of a credential leak in a way that rigid rules cannot.

### **1.3 The Hybrid "Sandwich" Architecture**

This report advocates for a **Hybrid Architecture**, often referred to in literature as a "Sandwich" approach.5

1. **Layer 1 (The Bread \- High Recall):** A highly optimized regex and entropy engine scans the codebase at maximum speed. Its goal is to cast a wide net, capturing every *potential* secret. It deliberately accepts a high false positive rate to ensure zero false negatives.  
2. **Layer 2 (The Meat \- High Precision):** The candidate strings identified in Layer 1 are passed to the AI engine. This engine acts as a sophisticated filter. It analyzes the snippet—variable name, line of code, and surrounding lines—to determine the probability that the candidate is a true secret.  
3. **Layer 3 (The Bread \- Reporting):** The verified findings are structured into standardized logs (SARIF) for consumption by downstream systems.

This architecture balances the computational cost of AI (which is too slow to run on every line of code) with the speed of regex, applying the expensive verification step only where it is statistically necessary.

## ---

**2\. Core Architecture: Python Base and CLI Design**

The choice of Python for the Proof of Concept (POC) and subsequent CLI tool is strategic. While languages like Go (used by Gitleaks and TruffleHog) offer raw performance advantages for string processing, Python possesses the unrivaled ecosystem for Machine Learning integration (PyTorch, Hugging Face, ONNX) and rapid prototyping. To mitigate Python's performance overhead, the architecture must leverage specific high-performance libraries and concurrency models.

### **2.1 CLI Framework Selection: The Case for Typer**

The user interface is the critical boundary between the tool's capability and the operator's workflow. The requirement is for a CLI that can accept a "single repo url or list as input." While the Python standard library offers argparse, and Click is a popular alternative, this report recommends **Typer** for the implementation.6

#### **2.1.1 Comparative Analysis: Typer vs. Click vs. Argparse**

* **Argparse:** Included in the standard library, ensuring zero dependencies. However, it requires verbose, imperative boilerplate code to define arguments and commands. It lacks modern features like automatic type conversion based on function signatures.6  
* **Click:** A robust, composable framework used by projects like Flask. It uses decorators to define commands. While powerful, it does not natively leverage Python 3.6+ type hints for validation, requiring manual definition of types.8  
* **Typer:** Built on top of Click, Typer utilizes standard Python type hints to enforce CLI behavior.  
  * **Type Safety:** If the CLI expects a list of URLs, defining the argument as targets: List\[str\] allows Typer to handle parsing and validation automatically.  
  * **Developer Efficiency:** It significantly reduces boilerplate code, allowing the development team to focus on the scanning logic rather than argument parsing. It also auto-generates rich help documentation.9  
  * **Validation:** Typer integrates seamlessly with the pydantic library (via typer.Argument or typer.Option), which is essential for validating complex configuration files or input lists.7

#### **2.1.2 Input Polymorphism Strategy**

The tool's entry point must handle polymorphic input—seamlessly distinguishing between a single repository URL and a file containing a list of URLs.

* **Design Pattern:** The main command should accept a target argument.  
  * If target matches a URL pattern (regex ^https?:// or ^git@), the tool initiates a SingleScanSession.  
  * If target resolves to a local file path (using pathlib.Path.exists()), the tool initiates a BulkScanSession, reading the file line-by-line.  
  * This logic should be encapsulated in an InputHandler class to ensure separation of concerns.

### **2.2 Git History Traversal: PyDriller over GitPython**

Mining the history of a repository is computationally expensive. Secrets are often introduced in a commit and then deleted in a subsequent "fix," meaning they exist only in the history, not the current HEAD.

* **GitPython Limitations:** While popular, GitPython is a low-level wrapper that often loads entire Git objects into memory. For repositories with thousands of commits (e.g., the Linux kernel or large enterprise monorepos), this can lead to MemoryError crashes and extreme slowness.10  
* **PyDriller Superiority:** **PyDriller** is a framework explicitly designed for Mining Software Repositories (MSR).10  
  * **Generator-Based:** PyDriller traverses commits using Python generators, meaning it only loads the metadata and diff of the *current* commit being analyzed into memory. This ensures the memory footprint remains constant (O(1)) regardless of repository size/depth.  
  * **Contextual Diffing:** PyDriller provides a high-level API to access the diff (the exact lines added or removed) and the source\_code (the state of the file at that commit). This "diff context" is the exact input required for the AI model to assess the validity of a secret.10  
  * **Filtering:** It includes native support for filtering commits by date range (since, to), branch, or file type, which simplifies the implementation of "incremental scanning" in CI/CD pipelines.11

### **2.3 Concurrency Model: Multiprocessing for CPU-Bound Tasks**

Scanning a list of repositories is an "embarrassingly parallel" workload. However, the choice of concurrency model is critical due to Python's Global Interpreter Lock (GIL).

* **AsyncIO (Inappropriate for Core Logic):** asyncio is designed for I/O-bound tasks (waiting for network responses). While the initial git clone operation is I/O-bound, the subsequent analysis—regex matching, entropy calculation, and neural network inference—is heavily **CPU-bound**.12 Using asyncio for the analysis phase would block the event loop, degrading performance to that of a single-threaded application.  
* **Multiprocessing (Recommended):** The multiprocessing module spawns separate operating system processes, each with its own Python interpreter and GIL. This allows the tool to utilize all available CPU cores for the heavy analysis work.14  
  * **Architecture:** The BulkScanSession should utilize a ProcessPoolExecutor. Each repository in the input list is submitted as a task. The operating system schedules these tasks across cores.  
  * **Inter-Process Communication:** Results from each process should be passed back to the main process via a thread-safe queue or returned as Future objects to be aggregated into the final log report.

## ---

**3\. The Detection Engine: Hybridizing Regex and AI**

The core value proposition of "AI TruffleHog" is to solve the precision gap inherent in legacy tools. This requires a sophisticated "detection engine" that treats regex matches not as findings, but as *candidates*.

### **3.1 Stage 1: Candidate Generation (High Recall)**

The first stage of the pipeline must be extremely fast to process millions of lines of code. AI models are too slow for this initial pass.

* **Regex Engine:** The tool should implement a library of high-confidence regex patterns. These can be sourced from the open-source rule sets of **Gitleaks** (gitleaks.toml) or **TruffleHog**. This ensures the tool covers known formats (AWS, Stripe, Slack tokens).15  
* **Entropy Scanner:** For secrets without fixed patterns, a Shannon entropy scanner is used. To avoid missing non-standard secrets, the entropy threshold should be set aggressively low (e.g., capturing any string with high randomness). This intentionally generates a high volume of false positives, relying on the AI layer to filter them out.  
* **Output:** The result of Stage 1 is a collection of Candidate objects, each containing the secret\_string, file\_path, line\_number, and a context\_window (e.g., 5 lines of code before and after the match).

### **3.2 Stage 2: Contextual Verification (High Precision)**

This is the integration point for the AI. The Candidate objects are passed to a classification model.

* **Contextual Analysis:** The model does not just look at the secret string; it "reads" the surrounding code. It learns to distinguish:  
  * **True Positive Signal:** api\_key \= "xyza..." (Variable name implies sensitivity).  
  * **False Positive Signal:** image\_hash \= "xyza..." (Variable name implies benign data).  
  * **False Positive Signal:** assert token \== "xyza..." (Test assertion implies dummy data).  
* **Model Input:** The input to the model is the context\_window. The model is trained to predict a binary label: 0 (False Positive) or 1 (True Secret).

### **3.3 Reference Work and Integration**

* **Gitleaks:** This tool is the gold standard for regex performance.15 AI TruffleHog should support importing Gitleaks configuration files (.toml) to allow users to use custom regex rules they have already defined.  
* **DeepSecrets:** This OWASP tool pioneered the use of "variable detection".3 AI TruffleHog's architecture generalizes this by using a neural network to learn variable associations implicitly, rather than relying on rigid lexing rules.  
* **Detect-Secrets:** This tool introduced the concept of "baselining" (ignoring known secrets).16 This concept should be adopted to manage technical debt in legacy repositories.

## ---

**4\. Machine Learning Strategy: Models, Training, and Optimization**

Deploying AI in a CLI tool introduces constraints: model size (must be downloadable) and inference latency (must not slow down the scan). We cannot rely on API calls to OpenAI (privacy risk, latency, cost); the model must run locally.

### **4.1 Model Architecture: SetFit and DistilBERT**

Standard Large Language Models (LLMs) like GPT-4 are overkill and computationally prohibitive. The task is **Binary Text Classification**, which can be solved effectively by Small Language Models (SLMs).

* **SetFit (Sentence Transformer Fine-tuning):** This is the recommended framework.17  
  * **Mechanism:** SetFit is designed for few-shot learning. It fine-tunes a **Sentence Transformer** (e.g., paraphrase-mpnet-base-v2 or all-MiniLM-L6-v2) using contrastive learning. It trains the model to minimize the distance between "secret" examples and maximize the distance from "non-secret" examples in vector space.  
  * **Efficiency:** A SetFit model based on MiniLM is approximately 80MB in size and extremely fast on CPUs.  
  * **Performance:** Research shows SetFit achieves high accuracy with very little training data (e.g., only a few hundred labeled examples of secrets vs. non-secrets).17  
* **DistilBERT:** An alternative is a standard fine-tuned DistilBERT model. While slightly larger than MiniLM, it offers robust performance for code understanding tasks.19

### **4.2 Optimization: ONNX Quantization**

To ensure the tool runs on standard developer laptops without requiring a GPU or a massive PyTorch installation:

* **ONNX Export:** The trained PyTorch model must be exported to the **ONNX (Open Neural Network Exchange)** format. ONNX provides a uniform, cross-platform file format for ML models.21  
* **Quantization:** The critical optimization step is **Quantization**. Using onnxruntime.quantization, the model's weights are converted from 32-bit floating-point numbers (FP32) to 8-bit integers (INT8).22  
  * **Impact:** This reduces the model size by \~4x (e.g., 80MB \-\> 20MB) and increases inference speed on CPUs by 2x-4x.  
  * **Deployment:** The CLI tool ships with the .onnx file and uses the lightweight onnxruntime library for inference. This eliminates the need for users to install the 700MB+ torch library, keeping the CLI install size small.

### **4.3 Training Data Generation**

The success of the AI depends on the quality of its training data.

* **Source:** Public repositories (GitHub) are a rich source of data.  
* **Labeling:**  
  * *True Positives:* Use high-confidence regexes (e.g., AWS, Stripe) on public repos to find real secrets (which are then scrubbed/rotated).  
  * *False Positives:* Use entropy scanners on "safe" projects (e.g., Linux kernel, documentation repos) to find high-entropy strings that are definitely not secrets (hashes, IDs).  
  * *Synthetic Data:* Use LLMs to generate synthetic examples of "tricky" code (e.g., dummy\_password \= "password123" in a test file) to teach the model to ignore them.1

### **4.4 Microsoft Presidio Integration**

**Microsoft Presidio** is an open-source library for PII detection/anonymization.24 It allows for pluggable "Recognizers."

* **Extension Pattern:** AI TruffleHog can be architected as a custom EntityRecognizer within the Presidio framework.25  
* **Benefit:** This leverages Presidio's existing logic for context analysis, score aggregation, and text spanning, preventing the need to reinvent the boilerplate of text processing. A custom recognizer class in Python can wrap the ONNX inference logic.25

## ---

**5\. False Positive Reduction: The "Context" Heuristic**

While the AI model provides probabilistic verification, deterministic heuristics are essential for handling edge cases and improving user trust.

### **5.1 Variable Name Analysis**

The strongest signal for a secret often lies in the variable name, not the value.

* **Technique:** Use simple lexing or Abstract Syntax Trees (ASTs) (via libraries like tree-sitter) to extract the identifier assigned to the candidate string.26  
* **Heuristic:** If the variable name contains specific "hotwords" (e.g., key, token, secret, password, auth, cred), the risk score is boosted. Conversely, if the variable name contains "coldwords" (e.g., hash, uuid, id, color, css, example), the risk score is penalized.27

### **5.2 File Path and Extension Filtering**

A high percentage of false positives occur in test files and documentation.

* **Test Data Exclusion:** The tool should automatically downgrade the severity or ignore findings in paths containing test, spec, mock, fixture, or example.1  
* **Extension Allowlisting:** Binary files (images, compiled objects) should be strictly ignored. The scanner should focus on text-based source code files (.py, .js, .go, .json, .yml, etc.).

### **5.3 Validation (The Ultimate Filter)**

For specific high-value secrets (like AWS keys, Slack tokens, or GitHub tokens), the tool can offer an optional "Verification" mode.

* **Mechanism:** The tool attempts a non-destructive API call using the detected credential (e.g., calling sts:GetCallerIdentity for AWS).28  
* **Result:**  
  * *Success:* The finding is marked "Verified Active" (Critical Severity).  
  * *Failure:* The finding is marked "Inactive/Fake" (Low Severity).  
* **Note:** This feature must be opt-in, as it generates network traffic that could be monitored by defenders.

## ---

**6\. Logging, Auditing, and Data Interchange**

The requirement for "sufficient logs file generation" is paramount for enterprise adoption. Security tools do not exist in a vacuum; their output must be consumable by other systems.

### **6.1 Structured Logging with JSON**

Logs must be machine-parsable. The tool should utilize the **structlog** library or Python's standard logging with a JSON formatter.29

* **Fields:** Every log entry should be a JSON object containing:  
  * timestamp (ISO 8601\)  
  * level (INFO, WARN, ERROR)  
  * component (Scanner, AI-Verifier, Reporter)  
  * repo\_url  
  * commit\_hash  
  * event (e.g., "scan\_started", "secret\_detected")

### **6.2 Standardization: SARIF Output**

The global standard for Static Analysis security tools is **SARIF (Static Analysis Results Interchange Format)**.4

* **Interoperability:** GitHub Advanced Security, GitLab, Azure DevOps, and VS Code all support SARIF natively. If the tool outputs SARIF, findings appear directly in the GitHub Security tab or as annotations in a Pull Request.  
* **Implementation:** The tool must generate a results.sarif file adhering to the OASIS schema.  
  * ruleId: The specific detector (e.g., "aws-access-key-onnx").  
  * message: Description of the finding.  
  * locations: File path, start line, end line.  
  * relatedLocations: Code snippets providing context.

### **6.3 Security of Logs (Redaction)**

A common vulnerability in secret scanners is that they log the secrets they find to disk in plain text, creating a new leak.

* **Redaction Requirement:** The logging pipeline must include a filter that automatically redacts the secret string (e.g., replacing it with REDACTED or a truncated hash like AKIA...\*\*\*\*) before writing to the log file or console.32 Full secret display should only be enabled via a strictly warned \--show-secrets debug flag.

## ---

**7\. Extensions and Ecosystem Integration**

To function effectively within a DevSecOps pipeline, "AI TruffleHog" must support various integration points.

### **7.1 Pre-Commit Hooks**

Preventing secrets from entering the codebase is far cheaper than remediating them later.

* **Configuration:** The repository must include a .pre-commit-hooks.yaml file to allow easy installation via the pre-commit framework.33  
* **Optimization:** Pre-commit hooks must be fast to avoid blocking developers. The hook should be configured to run in "staged" mode, scanning only the files currently being committed. To further optimize, the AI verification step could be skipped or run in a "light" mode for pre-commit checks, reserving the full deep scan for CI/CD.34

### **7.2 CI/CD Pipeline Integration**

The tool should be packaged as a Docker container (chayuto/ai-truffle-hog:latest) for easy usage in GitHub Actions, GitLab CI, or Jenkins.

* **Pipeline Logic:** The scanner should run on every Pull Request. If it detects a *verified* secret (high confidence score from the AI), it should fail the build, preventing the merge.  
* **Baseline Support:** To support legacy codebases, the tool must support a .secrets.baseline file (similar to detect-secrets). This JSON file lists known/accepted technical debt. The scanner ignores findings present in the baseline, alerting only on *new* secrets.16

### **7.3 IDE Extensions**

Using the SARIF output, a VS Code or IntelliJ extension can be developed to highlight secrets in the editor in real-time, functioning like a spell-checker for security.35

## ---

**8\. Implementation Roadmap**

To transition from concept to production-grade tool, the following roadmap is recommended:

### **Phase 1: The Foundation (Data & Regex)**

* **Goal:** Build the "Bread" of the sandwich.  
* **Tasks:**  
  * Implement the Typer CLI and PyDriller traversal logic.  
  * Integrate high-performance regex rules from Gitleaks/TruffleHog.  
  * **Research:** Create a dataset generation script to mine public repos for "True Positives" (validated secrets) and "False Positives" (entropy noise).

### **Phase 2: The Intelligence (Model Training)**

* **Goal:** Build the "Meat" of the sandwich.  
* **Tasks:**  
  * Train a SetFit model (using sentence-transformers) on the generated dataset. Focus on distinguishing "dummy" secrets from "real" secrets based on context.  
  * Export the model to ONNX and quantize to INT8.  
  * Integrate onnxruntime into the Python tool.

### **Phase 3: The Ecosystem (Integration)**

* **Goal:** Operationalize the tool.  
* **Tasks:**  
  * Implement SARIF reporting and JSON structured logging.  
  * Create .pre-commit-hooks.yaml and Dockerfile.  
  * Implement the "Validation" module for checking live API keys.  
  * Documentation: Write detailed guides on configuring false positive thresholds and ignoring files.

## **9\. Conclusion**

The "AI TruffleHog" project represents a necessary evolution in the field of secret scanning. By recognizing that **context is king**, this architecture moves beyond the binary limitations of regex and entropy. The combination of **Typer** for usability, **PyDriller** for historical depth, **SetFit/ONNX** for efficient local intelligence, and **SARIF** for integration provides a robust, enterprise-ready foundation.

Success will be defined not just by the code, but by the quality of the training data. A model that understands the difference between test\_key and prod\_key will transform secret scanning from a noisy compliance checkbox into a high-signal security control, saving thousands of developer hours and effectively closing one of the most persistent vulnerabilities in modern software engineering.

## **Summary of Recommendations**

| Component | Recommendation | Rationale |
| :---- | :---- | :---- |
| **CLI Framework** | **Typer** | Type safety, auto-documentation, pydantic integration. |
| **Git Engine** | **PyDriller** | Memory efficiency (generators), easy diff context access. |
| **Concurrency** | **Multiprocessing** | Bypasses Python GIL for CPU-bound analysis tasks. |
| **AI Model** | **SetFit (MiniLM)** | Few-shot learning efficiency, small size, high accuracy. |
| **Inference** | **ONNX Runtime (INT8)** | Deployment on standard CPUs without heavy deps. |
| **Logging** | **Structlog \+ SARIF** | Machine readability and standard tool integration. |
| **FP Reduction** | **Context \+ Heuristics** | Variable name analysis, test file exclusion. |
| **Integration** | **Pre-commit \+ Docker** | Shift-left prevention and CI/CD automation. |

#### **Works cited**

1. Argus: A Multi-Agent Sensitive Information Leakage Detection Framework Based on Hierarchical Reference Relationships \- arXiv, accessed December 30, 2025, [https://arxiv.org/html/2512.08326v1](https://arxiv.org/html/2512.08326v1)  
2. Secrets in Source Code: Reducing False Positives using Machine Learning \- ResearchGate, accessed December 30, 2025, [https://www.researchgate.net/publication/339819882\_Secrets\_in\_Source\_Code\_Reducing\_False\_Positives\_using\_Machine\_Learning](https://www.researchgate.net/publication/339819882_Secrets_in_Source_Code_Reducing_False_Positives_using_Machine_Learning)  
3. OWASP DeepSecrets, accessed December 30, 2025, [https://nest.owasp.org/projects/deepsecrets](https://nest.owasp.org/projects/deepsecrets)  
4. OWASP DeepSecrets | OWASP Foundation, accessed December 30, 2025, [https://owasp.org/www-project-deepsecrets/](https://owasp.org/www-project-deepsecrets/)  
5. Secret Breach Detection in Source Code with Large Language Models \- arXiv, accessed December 30, 2025, [https://arxiv.org/pdf/2504.18784](https://arxiv.org/pdf/2504.18784)  
6. Comparing Python Command Line Interface Tools: Argparse, Click, and Typer | CodeCut, accessed December 30, 2025, [https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/](https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/)  
7. Navigating the CLI Landscape in Python: A Comparative Study of argparse, click, and typer, accessed December 30, 2025, [https://medium.com/@mohd\_nass/navigating-the-cli-landscape-in-python-a-comparative-study-of-argparse-click-and-typer-480ebbb7172f](https://medium.com/@mohd_nass/navigating-the-cli-landscape-in-python-a-comparative-study-of-argparse-click-and-typer-480ebbb7172f)  
8. Click vs argparse \- Which CLI Package is Better? \- Python Snacks, accessed December 30, 2025, [https://www.pythonsnacks.com/p/click-vs-argparse-python](https://www.pythonsnacks.com/p/click-vs-argparse-python)  
9. Python CLI Options: argparse, Click, Typer for Beginners, accessed December 30, 2025, [https://www.python.digibeatrix.com/en/api-libraries/python-command-line-options-guide/](https://www.python.digibeatrix.com/en/api-libraries/python-command-line-options-guide/)  
10. PyDriller: Python Framework for Mining Software Repositories \- Alberto Bacchelli, accessed December 30, 2025, [https://sback.it/publications/fse2018td.pdf](https://sback.it/publications/fse2018td.pdf)  
11. Overview / Install — PyDriller 1.0 documentation, accessed December 30, 2025, [https://pydriller.readthedocs.io/en/latest/intro.html](https://pydriller.readthedocs.io/en/latest/intro.html)  
12. AsyncIO vs Threading vs Multiprocessing: A Beginner's Guide \- Codimite, accessed December 30, 2025, [https://codimite.ai/blog/asyncio-vs-threading-vs-multiprocessing-a-beginners-guide/](https://codimite.ai/blog/asyncio-vs-threading-vs-multiprocessing-a-beginners-guide/)  
13. Deep Dive into Multithreading, Multiprocessing, and Asyncio | Towards Data Science, accessed December 30, 2025, [https://towardsdatascience.com/deep-dive-into-multithreading-multiprocessing-and-asyncio-94fdbe0c91f0/](https://towardsdatascience.com/deep-dive-into-multithreading-multiprocessing-and-asyncio-94fdbe0c91f0/)  
14. Python Multithreading vs Multiprocessing vs Asyncio Explained in 10 Minutes \- YouTube, accessed December 30, 2025, [https://www.youtube.com/watch?v=QXwefd3z8IU](https://www.youtube.com/watch?v=QXwefd3z8IU)  
15. Find secrets with Gitleaks \- GitHub, accessed December 30, 2025, [https://github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)  
16. Best Secret Scanning Tools in 2025 \- Aikido, accessed December 30, 2025, [https://www.aikido.dev/blog/top-secret-scanning-tools](https://www.aikido.dev/blog/top-secret-scanning-tools)  
17. bew/setfit-subject-model-basic \- Hugging Face, accessed December 30, 2025, [https://huggingface.co/bew/setfit-subject-model-basic](https://huggingface.co/bew/setfit-subject-model-basic)  
18. Efficient Few-Shot Learning for NLP | PDF | Statistical Inference \- Scribd, accessed December 30, 2025, [https://www.scribd.com/document/735677396/setfit](https://www.scribd.com/document/735677396/setfit)  
19. Security Requirements Classification by Means of Explainable Transformer Models | Request PDF \- ResearchGate, accessed December 30, 2025, [https://www.researchgate.net/publication/395177090\_Security\_Requirements\_Classification\_by\_Means\_of\_Explainable\_Transformer\_Models](https://www.researchgate.net/publication/395177090_Security_Requirements_Classification_by_Means_of_Explainable_Transformer_Models)  
20. TinyBERT: Distilling BERT for Natural Language Understanding | Request PDF, accessed December 30, 2025, [https://www.researchgate.net/publication/347234859\_TinyBERT\_Distilling\_BERT\_for\_Natural\_Language\_Understanding](https://www.researchgate.net/publication/347234859_TinyBERT_Distilling_BERT_for_Natural_Language_Understanding)  
21. Model Formats \- State of Open Source AI Book, accessed December 30, 2025, [https://book.premai.io/state-of-open-source-ai/model-formats/](https://book.premai.io/state-of-open-source-ai/model-formats/)  
22. Quantize ONNX models | onnxruntime, accessed December 30, 2025, [https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)  
23. Quantization \- Hugging Face, accessed December 30, 2025, [https://huggingface.co/docs/optimum-onnx/onnxruntime/usage\_guides/quantization](https://huggingface.co/docs/optimum-onnx/onnxruntime/usage_guides/quantization)  
24. Microsoft Presidio: An Open Source Tool Specialized in Personal Information Protection, accessed December 30, 2025, [https://developer.mamezou-tech.com/en/blogs/2025/01/04/presidio-intro/](https://developer.mamezou-tech.com/en/blogs/2025/01/04/presidio-intro/)  
25. Tutorial \- Microsoft Presidio \- Microsoft Open Source, accessed December 30, 2025, [https://microsoft.github.io/presidio/analyzer/adding\_recognizers/](https://microsoft.github.io/presidio/analyzer/adding_recognizers/)  
26. Secrets Scanning, Secrets scanners \- All You Need To Know \- Entro Security, accessed December 30, 2025, [https://entro.security/resource/complete-guide-to-secrets-scanning/](https://entro.security/resource/complete-guide-to-secrets-scanning/)  
27. Evaluating Large Language Models in detecting Secrets in Android Apps \- arXiv, accessed December 30, 2025, [https://arxiv.org/html/2510.18601v1](https://arxiv.org/html/2510.18601v1)  
28. Secrets Scans \- JFrog, accessed December 30, 2025, [https://jfrog.com/help/r/jfrog-security-user-guide/products/advanced-security/features-and-capabilities/secrets-scans](https://jfrog.com/help/r/jfrog-security-user-guide/products/advanced-security/features-and-capabilities/secrets-scans)  
29. 10 Python Logging Best Practices for Cybersecurity \- Apriorit, accessed December 30, 2025, [https://www.apriorit.com/dev-blog/cybersecurity-logging-python](https://www.apriorit.com/dev-blog/cybersecurity-logging-python)  
30. Guide to structured logging in Python \- New Relic, accessed December 30, 2025, [https://newrelic.com/blog/log/python-structured-logging](https://newrelic.com/blog/log/python-structured-logging)  
31. DevSecOps on Azure Kubernetes Service (AKS) \- Microsoft Learn, accessed December 30, 2025, [https://learn.microsoft.com/en-us/azure/architecture/guide/devsecops/devsecops-on-aks](https://learn.microsoft.com/en-us/azure/architecture/guide/devsecops/devsecops-on-aks)  
32. Python Logging Best Practices: Complete Guide 2025 \- Carmatec, accessed December 30, 2025, [https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/)  
33. pre-commit, accessed December 30, 2025, [https://pre-commit.com/](https://pre-commit.com/)  
34. Pre-commit hooks \- TruffleHog Docs, accessed December 30, 2025, [https://docs.trufflesecurity.com/pre-commit-hooks](https://docs.trufflesecurity.com/pre-commit-hooks)  
35. Detect Secrets in the IDE with SonarLint | Sonar, accessed December 30, 2025, [https://www.sonarsource.com/resources/library/detect-secrets-in-the-ide-with-sonarlint/](https://www.sonarsource.com/resources/library/detect-secrets-in-the-ide-with-sonarlint/)