# **Global-Scale GitHub Secret Scanning Architecture: A Comprehensive Technical and Operational Analysis**

## **1\. Introduction**

The integration of Large Language Models (LLMs) into the software development lifecycle has precipitated a fundamental shift in how applications authenticate and interact with third-party intelligence providers. Unlike traditional database credentials or internal service tokens, API keys for providers such as OpenAI and Anthropic represent a direct financial instrument. Possession of a valid key allows an adversary not merely access to data, but the consumption of computational resources that are billed directly to the victim. The phenomenon of "secret sprawl"—where sensitive credentials are inadvertently committed to version control systems—has escalated from a security best-practice concern to a critical financial liability.  
This report articulates a rigorous architectural blueprint for a system designed to "constantly fetch and watch all public repositories," scanning specifically for OpenAI and Anthropic credentials within every branch and commit of newly created and updated repositories. The proposed system requirements—comprehensive historical scanning ("all commits"), immediate detection in new repositories, rigorous pattern validation, and active liveness verification—constitute a massive-scale distributed engineering challenge. This document dissects the necessary ingestion mechanisms, detection algorithms, verification protocols, and state management strategies required to process the "GitHub Firehose" (the entirety of public event data) in near real-time.  
Furthermore, this analysis moves beyond the purely technical to address the significant legal and operational risks inherent in "liveness checking." While the detection of a string matching a regex pattern is a passive computational task, the act of sending that string to a provider's API to verify its validity constitutes an unauthorized interaction with a third-party system. This report will examine the Computer Fraud and Abuse Act (CFAA) implications of such verification, contrasting the engineering necessity of validation against the legal frameworks governing unauthorized access.

## **2\. Data Ingestion: The GitHub Event Stream Architecture**

The primary requirement to "constantly fetch and watch ALL public repo" necessitates a high-throughput ingestion layer capable of filtering noise from the immense volume of daily GitHub activity. A naive approach of polling individual repositories is mathematically impossible given the scale of 800 million repositories. Instead, the system must tap into the centralized event streams provided by GitHub, specifically optimizing for the PushEvent and CreateEvent types which signal the introduction of new code.

### **2.1 The GitHub Events API: Mechanics and Limitations**

The GET /events endpoint serves as the standard interface for monitoring public activity. However, relying on this API for a global-scale scanner introduces complex synchronization challenges. The API returns a list of public events that have occurred within the past five minutes, with a retention window limited to 300 events or 90 days, whichever is reached first. In practice, the high volume of global activity means the 300-event window cycles rapidly—often in seconds during peak hours—creating a "consumption race." If the ingestor fails to poll and page through these events faster than they are generated, data is permanently lost from the stream, resulting in missed commits and potential security blind spots.  
Latency is another critical factor. While often assumed to be real-time, the Events API has documented latencies ranging from 30 seconds to over six hours depending on system load and time of day. This variance implies that a "real-time" scanner is, in reality, a "near real-time" system subject to the vagaries of GitHub's internal queuing infrastructure. An effective ingestion architecture must therefore be decoupled from the scanning workers; the ingestor's sole responsibility is to capture event IDs and payloads to a durable queue (e.g., Kafka) to ensure that processing backpressure does not result in data loss at the ingestion edge.

### **2.2 Optimization Strategies for High-Frequency Polling**

To maintain a continuous watch on the event stream without triggering GitHub's abuse detection mechanisms, the polling infrastructure must strictly adhere to rate limits while maximizing throughput.

#### **2.2.1 Conditional Requests and ETag Management**

The most efficient method to poll the Events API is through Conditional Requests utilizing the ETag (Entity Tag) header. When the scanner makes a request to GET /events, the response includes an ETag header representing the state of the event list. Subsequent requests should include this value in the If-None-Match header. If no new events have occurred since the last poll, GitHub returns a 304 Not Modified status code. Crucially, 304 responses do not count against the primary rate limit quota. This mechanism allows the scanner to poll at a very high frequency (e.g., every second) to capture new events immediately as they appear, without exhausting the 5,000 requests-per-hour limit associated with authenticated tokens.

#### **2.2.2 Token Rotation and Quota Management**

For authenticated requests that do consume quota (i.e., when new events are returned), a single API token is insufficient for a system operating at global scale. The architecture must implement a pool of authenticated tokens. The ingestor tracks the x-ratelimit-remaining header for the active token. As this value approaches depletion, the system must seamlessly rotate to the next available token in the pool to ensure uninterrupted ingestion. This token rotation strategy is essential not only for the Events API but also for the subsequent retrieval of repository metadata and file contents.

### **2.3 Event Filtering for Secret Scanning**

Not all events are relevant to the objective of finding API keys. The ingestion layer must implement a high-performance filter to discard irrelevant data before it consumes downstream resources.

| Event Type | Relevance to Secret Scanning | Action |
| :---- | :---- | :---- |
| **PushEvent** | **Critical** | Contains the commits array with SHA hashes of new code. This is the primary trigger for scanning updates to existing repositories. The scanner must extract the head commit and the before commit to define the scan range. |
| **CreateEvent** | **Critical** | Indicates the creation of a new repository or branch. For new repositories, this signals the need for a "baseline scan" of the initial commit history. The user's requirement to watch "Especially new ones" highlights the importance of this event. |
| **PublicEvent** | **High** | Triggered when a private repository is made public. This is a high-risk event as it may expose a long history of previously private commits that were never scrubbed for secrets. A full historical scan is required. |
| **PullRequestEvent** | **Medium** | While relevant, the code in a PR is often also captured via PushEvent to the source branch. However, scanning PR diffs can provide earlier detection before a merge occurs. |
| **WatchEvent** | **None** | Indicates a user starred a repository. Contains no code changes. Should be dropped immediately. |
| **IssueCommentEvent** | **Low** | While secrets *can* be pasted in comments, the primary vector is the codebase. Scanning comments requires a different parsing logic (text vs. code). |

The ingestion service must parse the JSON payload of PushEvent and CreateEvent to extract the repo.url and the list of distinct commit SHAs. This metadata forms the "job definition" passed to the scanning workers.

## **3\. Repository Access and Commit Traversal**

Once an event triggers a scan, the system must access the actual file contents. The requirement to "pull down the repo... all branch... go through all the commit" presents a significant storage and bandwidth challenge. Cloning a multi-gigabyte repository to scan a few kilobytes of changes is inefficient and cost-prohibitive at scale.

### **3.1 Efficient Retrieval Strategies**

There are two primary methods for accessing repository content: full cloning and partial fetching.

#### **3.1.1 Ephemeral Shallow Cloning**

For "new" repositories identified via CreateEvent or PublicEvent, the most robust approach is an ephemeral shallow clone. Using git clone \--depth 1 retrieves only the latest commit, minimizing bandwidth while providing the full directory structure necessary for context-aware scanning. If the requirement is to scan the *entire* history of a new repository (to find secrets in past commits), a full clone or a "treeless" clone (--filter=tree:0) may be necessary, allowing the scanner to walk the commit log without downloading all file blobs initially.

#### **3.1.2 Differential Fetching for PushEvents**

For PushEvent updates, the system should avoid re-cloning the repository. Instead, the scanner can initialize an empty git repository and use git fetch to retrieve only the specific commit objects referenced in the event payload.

* **Command:** git fetch \--depth=1 origin \<commit\_sha\>  
* This places the specific commit into the local object store. The scanner can then use git diff or git show to isolate the changes introduced in that commit. This approach strictly aligns with the "go through all the commit" requirement while minimizing data transfer.

#### **3.1.3 Git Archive and Piping**

An advanced optimization involves using git archive to stream the repository content directly into the scanner without writing to the disk. However, this requires the repository host (GitHub) to support archive generation via API, and the scanner (e.g., Gitleaks) to support stdin input. Gitleaks supports the stdin mode (cat archive.tar | gitleaks detect \--source \-), which allows for scanning in-memory. This significantly reduces I/O latency, a major bottleneck in high-throughput systems.

### **3.2 Traversal of Branches and History**

The requirement to scan "All branch" implies discovering references beyond the default main or master.

* **Remote Reference Enumeration:** The scanner must list all remote references using git ls-remote. This returns a list of all branches and tags with their current commit SHAs.  
* **Iterative Scanning:** For a new repository, the scanner must iterate through every branch tip. However, simply scanning the *tip* is insufficient if the user wants to check "all the commit." The scanner must perform a graph traversal (e.g., git log \--all) to identify unique commits across all branches.  
* **Deduplication at Source:** Many branches share a common history. Scanning every commit of every branch will result in redundant processing. The system must maintain a local cache or set of processed commit hashes for the current job to ensure each unique commit SHA is scanned only once, regardless of how many branches reference it.

### **3.3 Handling Git Large File Storage (LFS)**

A critical edge case in repository scanning is Git LFS. Secrets are sometimes inadvertently stored in configuration files or datasets managed by LFS. Standard git commands only download the pointer files (small text files containing the object hash). To scan the actual content, the scanner must explicitly pull LFS objects. This operation is bandwidth-intensive and subject to separate rate limits. For a general-purpose scanner, it is often a strategic decision to skip LFS objects unless specific file extensions (e.g., .env files that were accidentally added to LFS) are detected, as the cost-benefit ratio of scanning gigabytes of binary data for text-based keys is poor.

## **4\. Detection Engineering: Pattern Matching and Analysis**

The core of the system is the detection engine. To satisfy the requirement to "scan for checked in envs for Open api key / anthropic api key," the engine must employ high-fidelity Regular Expressions (Regex) combined with entropy analysis to distinguish actual secrets from random strings.

### **4.1 Target Patterns: OpenAI**

OpenAI has evolved its key format over time. A robust scanner must detect both legacy and modern formats.

* **Legacy User Keys:** These keys typically start with sk- followed by a 40+ character alphanumeric string. They do not have a distinct project identifier.  
  * *Pattern:* sk-\[a-zA-Z0-9\]{40,}.  
* **Project Keys (Modern):** To improve security and scoping, OpenAI introduced project keys prefixed with sk-proj-. These keys often contain a secondary identifier or checksum and are significantly longer.  
  * *Pattern:* sk-proj-\[a-zA-Z0-9\_-\]{48,}.  
* **Service Account Keys:** These are used for automated systems and utilize the sk-svcacct- prefix.  
  * *Pattern:* sk-svcacct-\[a-zA-Z0-9\_-\]+.

The detection engine must normalize these patterns. A generalized regex such as \\b(sk-(?:proj-|svcacct-)?\[a-zA-Z0-9\_\\-\]{40,})\\b captures the variability while enforcing the structural requirements of the key.

### **4.2 Target Patterns: Anthropic**

Anthropic keys follow a distinct structure, often including version identifiers within the prefix.

* **Standard API Keys:** These keys typically begin with sk-ant-api03-. The api03 segment indicates the key format version.  
  * *Pattern:* sk-ant-api03-\[a-zA-Z0-9\_\\-\]{20,}.  
* **Admin/Internal Keys:** While less common in public leaks, keys starting with sk-ant-admin- represent highly privileged access and must be prioritized.  
  * *Pattern:* sk-ant-admin-\[a-zA-Z0-9\_\\-\]{20,}.

### **4.3 Reducing False Positives: Entropy and Context**

Regex matching alone produces a high volume of false positives (e.g., a variable named task-project-12345 might match a loose sk-proj regex). To mitigate this, the system must employ **Shannon Entropy** analysis.

* **Entropy Calculation:** API keys are generated using high-entropy random number generators. Their character distribution is uniform and unpredictable. In contrast, natural language or standard code variables have low entropy (predictable patterns).  
* **Thresholding:** The scanner should calculate the entropy of any captured string. If the entropy falls below a certain threshold (e.g., 4.5 bits per character), the match is likely a false positive and should be discarded before the expensive verification step.  
* **File Context:** The scanner should prioritize files likely to contain secrets, such as .env, config.py, secrets.json, and .yaml files. Conversely, matches found in package-lock.json, markdown files, or binary files should be treated with higher skepticism or ignored to optimize performance.

### **4.4 Tooling: Gitleaks vs. TruffleHog**

For the implementation of this detection logic, two tools stand out: Gitleaks and TruffleHog.

* **Gitleaks:** Written in Go, Gitleaks is optimized for speed and stream processing. It uses the Hyperscan regex engine (or Go's native engine) for extremely fast matching. It supports scanning git history via the \--log-opts flag, making it ideal for the "go through all the commit" requirement. It can also pipe content via stdin, enabling the git archive optimization discussed earlier.  
* **TruffleHog:** While also capable of regex scanning, TruffleHog's distinguishing feature is its built-in verification modules. However, for the *detection* phase of a high-throughput pipeline, Gitleaks offers superior performance per resource unit.

**Recommendation:** Use **Gitleaks** as the primary detection engine to identify candidate strings rapidly. Pass these candidates to a separate, specialized verification service that performs the liveness checks. This decoupling prevents the slow network I/O of verification from blocking the fast CPU-bound task of scanning.

## **5\. Verification: Liveness Checking and Validation**

The requirement to "check if the key is live" transitions the system from passive analysis to active network interaction. This is the most operationally complex and legally risky component of the architecture.

### **5.1 The Economics of Verification**

Verification is not free. Both OpenAI and Anthropic operate on a pre-paid credit model for API access.

* **OpenAI:** There is no permanent free tier. Trial credits expire, and accounts must be funded to make API requests. While checking a key's validity doesn't necessarily require generating text (which costs significantly more), finding an endpoint that returns a status without consuming credits is crucial.  
* **Anthropic:** Similarly, Anthropic requires an active credit balance. A key associated with an account that has zero credits will return a specific error code (400 Bad Request \- Credit Balance Too Low), distinct from an invalid key (401 Unauthorized).

### **5.2 Validation Endpoints and Response Analysis**

To validate a key with minimal side effects (e.g., avoiding cost or triggering usage alerts), the scanner should target "metadata" endpoints rather than generation endpoints.

#### **5.2.1 Validating OpenAI Keys**

The optimal endpoint for OpenAI validation is GET https://api.openai.com/v1/models. This endpoint lists the models available to the key. It is lightweight, typically allows high concurrency, and does not incur generation costs.  
**Response Codes & Interpretation:**

* **200 OK:** The key is **Live**, valid, and has permissions to list models.  
* **401 Unauthorized:** The key is **Dead** or invalid.  
* **429 Too Many Requests (Quota Exceeded):** The key is **Live** (authentication succeeded), but the account is out of credits or rate-limited. This is a critical distinction: the credential works, but the wallet is empty. For a security scanner, this is still a "Live" finding because the account could be refunded at any time.  
* **403 Forbidden:** The key is valid but lacks scope for this endpoint (rare for the models endpoint).

#### **5.2.2 Validating Anthropic Keys**

For Anthropic, the GET https://api.anthropic.com/v1/models endpoint serves a similar purpose. Alternatively, a request to POST /v1/messages with a dummy payload can be used if strict access to models is restricted, though this carries a higher risk of cost or logging.  
**Response Codes & Interpretation:**

* **200 OK:** The key is **Live**.  
* **401 Unauthorized:** The key is **Dead**.  
* **400 Bad Request (Credit Balance Too Low):** The key is **Live** (authenticated) but unfunded. This confirms the credential is valid.

### **5.3 Operational Security (OpSec) for Verification**

Active verification exposes the scanner's infrastructure to the API providers. Sending thousands of requests from a single IP address to check stolen keys will result in immediate IP bans by OpenAI and Anthropic, and potentially legal complaints to the hosting provider.

* **Proxy Rotation:** The verification worker must route requests through a rotating residential or datacenter proxy network. This distributes the traffic and masks the origin of the scan.  
* **User-Agent Spoofing:** Requests should not identify as python-requests or Go-http-client. They should mimic legitimate traffic (e.g., OpenAI-Python-Client/0.27.0) to avoid heuristic blocking.  
* **Rate Limiting:** The verifier must respect the 429 backoff signals. Aggressive retries on a 429 can lead to permanent bans of the proxy IP.

## **6\. Deduplication and State Management**

The requirement to "store result on checked commit id. So it will skip" is a massive scalability constraint. With GitHub processing billions of commits, a naive database look-up for every commit SHA will become the system's bottleneck.

### **6.1 The Scale of Deduplication**

If the system processes 500 events per second, and each push contains an average of 3 commits, the deduplication layer must handle 1,500 lookups and writes per second. A standard SQL SELECT query on a table with 5 billion rows will introduce unacceptable latency.

### **6.2 Probabilistic Data Structures: Redis Bloom and Cuckoo Filters**

To achieve sub-millisecond deduplication at this scale, the architecture requires probabilistic data structures.

* **Bloom Filters:** A space-efficient structure that tells you if an element is *definitely not* in the set or *possibly* in the set. It has zero false negatives (if it says "not seen," it hasn't been seen) but a small probability of false positives (saying "seen" when it hasn't). For this use case, a false positive means skipping a commit that hasn't been scanned—a potentially acceptable trade-off for speed.  
* **Cuckoo Filters:** An evolution of Bloom filters that supports **deletion** of items and generally offers better lookup performance and higher space efficiency for large datasets. Cuckoo filters are ideal for this application because they allow for managing the "checked" state with high fidelity.

**Implementation Strategy:** Use Redis with the RedisBloom module. The workflow for every commit SHA extracted from an event is:

1. **Check:** CF.EXISTS scanned\_commits \<commit\_sha\>  
2. **Logic:**  
   * If TRUE: The commit has likely been scanned. Skip.  
   * If FALSE: The commit is new. Proceed to scan.  
3. **Update:** After successful scanning, execute CF.ADD scanned\_commits \<commit\_sha\>.

A Cuckoo filter storing 1 billion items requires approximately 1-2 GB of RAM, whereas a PostgreSQL index for the same dataset would require hundreds of gigabytes of storage and significant I/O overhead.

### **6.3 Persistent Storage**

While Redis handles the ephemeral "skip" logic, the actual results must be stored in a durable database (e.g., PostgreSQL or MongoDB). The schema should capture:

* **Repository Metadata:** URL, Owner, Visibility.  
* **Commit Metadata:** SHA, Message, Author, Date.  
* **Secret Metadata:** Type (OpenAI/Anthropic), Pattern Match, File Path.  
* **Verification Status:** Liveness Result (Live/Dead/Quota), Response Code, Timestamp of check.

## **7\. Legal and Ethical Framework: The CFAA and Unauthorized Access**

This section addresses the critical legal risks associated with the user's requirement to "check if the key is live."

### **7.1 The Computer Fraud and Abuse Act (CFAA)**

In the United States, the CFAA (18 U.S.C. § 1030\) makes it illegal to access a computer without authorization or to exceed authorized access.

* **Unauthorized Access:** When the scanner uses a leaked API key to query OpenAI's servers, it is technically performing an action that the key owner did not authorize. Even if the intent is security research or validation, the act of using credentials belonging to another party to access a protected computer system (OpenAI's API) falls within the definition of unauthorized access.  
* **Exceeding Authorized Access:** While the researcher may have their own OpenAI account, using a third party's key "exceeds" the authorization granted to the researcher. Legal precedents regarding "scraping" (e.g., *hiQ v. LinkedIn*) generally protect access to *public* data. However, an API key is a private credential, akin to a password, and using it provides access to *private* functionality (the ability to bill the victim's account).

### **7.2 Terms of Service Violations**

Both GitHub and the API providers have strict Terms of Service (ToS).

* **GitHub:** While scraping public data is generally tolerated, excessive requests that burden the infrastructure ("constantly fetch... ALL public repo") can be classified as a denial-of-service attack or abusive behavior, leading to IP bans or account suspension.  
* **OpenAI/Anthropic:** Their policies explicitly prohibit the use of unowned credentials. Automated verification scripts violate the intended use of the API and can lead to the banning of the researcher's own accounts and IP addresses.

### **7.3 Responsible Disclosure and Safe Harbor**

Legitimate security researchers operate under "Safe Harbor" policies. However, these policies typically exist between the researcher and the *vendor* (e.g., OpenAI). They do not automatically grant the right to test credentials belonging to *third-party users* (the developers who leaked the keys).

* **The Risk:** If a scanner validates a key, and that validation triggers a security alert for the victim or consumes their limited credits, the victim may pursue legal action. There is no "Safe Harbor" agreement between the scanner operator and the random developer on GitHub.  
* **Recommendation:** To mitigate legal risk, the "liveness check" should be omitted for any general public scanning. The detection of the pattern itself is sufficient for a "suspected" finding. If liveness checking is mandatory, it should only be performed on repositories where the scanner operator has explicit permission (e.g., their own organization's repositories) or as part of a formal partnership with the API provider (e.g., GitHub's Secret Scanning Partner Program).

## **8\. Conclusion**

Constructing a system to scan all public GitHub repositories for API keys is a solved architectural problem but remains an immense operational undertaking. The proposed solution requires a distributed pipeline utilizing **GitHub Events API polling with ETag optimization** for ingestion, **ephemeral shallow cloning** for efficient data access, **Gitleaks** for high-throughput regex detection, and **Redis Cuckoo Filters** for billion-scale deduplication.  
While the technical pathway to "check if the key is live" via API probing is straightforward, it carries severe legal liabilities under the CFAA. The act of automating the use of leaked credentials transforms the system from a passive observer into an active participant in unauthorized access. Consequently, while the detection component of this plan is viable for security research, the automated verification component should be approached with extreme caution, ideally restricted to authorized environments or replaced with passive reporting mechanisms that do not interact with the compromised credentials.

#### **Works cited**

1\. GitHub just hit 800 MILLION repositories and the stats behind it are absolutely mind-blowing (AI is eating the world) \- Reddit, https://www.reddit.com/r/ThinkingDeeplyAI/comments/1l92ufg/github\_just\_hit\_800\_million\_repositories\_and\_the/ 2\. REST API endpoints for events \- GitHub Docs, https://docs.github.com/en/rest/activity/events 3\. GitHub Events API delay — how long for new commits to appear in /users/{user}/events/public? \- Reddit, https://www.reddit.com/r/github/comments/1o2ilir/github\_events\_api\_delay\_how\_long\_for\_new\_commits/ 4\. Using webhooks with GitHub Apps, https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps 5\. A Developer's Guide: Managing Rate Limits for the GitHub API \- Lunar.dev, https://www.lunar.dev/post/a-developers-guide-managing-rate-limits-for-the-github-api 6\. Rate limits for the REST API \- GitHub Docs, https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api 7\. Events | GitHub API \- LFE Documentation, http://docs2.lfe.io/v3/activity/events/ 8\. Managing large Git Repositories \- GitHub Well-Architected, https://wellarchitected.github.com/library/architecture/recommendations/scaling-git-repositories/large-git-repositories/ 9\. Find secrets with Gitleaks \- GitHub, https://github.com/gitleaks/gitleaks 10\. Searching GitHub for OpenAI API Keys | thoughts \- TheDen.sh, https://thoughts.theden.sh/posts/openai-api-keys/ 11\. What are the valid characters for the APIKey? \- API \- OpenAI Developer Community, https://community.openai.com/t/what-are-the-valid-characters-for-the-apikey/288643 12\. Regex's to validate API Key and Org ID format? \- OpenAI Developer Community, https://community.openai.com/t/regex-s-to-validate-api-key-and-org-id-format/44619 13\. Incorrect API is generated in the OpenAI account, https://community.openai.com/t/incorrect-api-is-generated-in-the-openai-account/879912 14\. API-Examples/.gitleaks.toml at main \- GitHub, https://github.com/AgoraIO/API-Examples/blob/main/.gitleaks.toml 15\. Get Api Key \- Claude API Reference, https://platform.claude.com/docs/en/api/admin/api\_keys/retrieve 16\. Internal server error with certain API keys when model identifier contains space characters \#691 \- GitHub, https://github.com/anthropics/anthropic-sdk-typescript/issues/691 17\. Usage and Cost API \- Claude Docs, https://platform.claude.com/docs/en/build-with-claude/usage-cost-api 18\. How to Prevent Secret Leaks in Your Repositories \- InfraCloud, https://www.infracloud.io/blogs/prevent-secret-leaks-in-repositories/ 19\. Top 9 Git Secret Scanning Tools for DevSecOps \- Spectral, https://spectralops.io/blog/top-9-git-secret-scanning-tools/ 20\. Complete Guide to OpenAI API Access: Free Trials, Alternatives & Cost-Effective Solutions 2025, https://www.cursor-ide.com/blog/how-to-get-openai-api-key-free-2025 21\. Can I use openAI API with the free account?, https://community.openai.com/t/can-i-use-openai-api-with-the-free-account/977476 22\. Insufficient credit error has the same error code as bad requests \#618 \- GitHub, https://github.com/anthropics/anthropic-sdk-typescript/issues/618 23\. \[Solved\] Your credit balance is too low to access the requested service. Please visit Plans & Billing to upgrade or purchase credits. \- Portkey, https://portkey.ai/error-library/insufficient-balance-error-10489 24\. OpenAI API Key Tester \- Trevor Fox, https://trevorfox.com/api-key-tester/openai 25\. openai-api-key-verifier \- PyPI, https://pypi.org/project/openai-api-key-verifier/ 26\. Error codes | OpenAI API, https://platform.openai.com/docs/guides/error-codes 27\. Cuckoo filter | Docs \- Redis, https://redis.io/docs/latest/develop/data-types/probabilistic/cuckoo-filter/ 28\. Bloom filter or cuckoo hashing? \- Stack Overflow, https://stackoverflow.com/questions/867099/bloom-filter-or-cuckoo-hashing 29\. Cuckoo and Bloom filters: probabilistic efficient caching. \- Sam Gozman, https://gozman.space/blog/cuckoo-and-bloom-filters-probabilistic-efficient-caching 30\. API Key Leaks: How to Detect, Prevent, and Secure Your Business \- TRaViS ASM, https://travisasm.com/blog/our-blog-1/api-key-leaks-how-to-detect-prevent-and-secure-your-business-57 31\. Challenging Evidence of Unauthorized Access in CFAA Cases Under Federal Law, https://leppardlaw.com/federal/computer-crimes/challenging-evidence-of-unauthorized-access-in-cfaa-cases-under-federal-law/ 32\. Using the Computer Fraud and Abuse Act to Secure Public Data Exclusivity \- Scholarly Commons: Northwestern Pritzker School of Law, https://scholarlycommons.law.northwestern.edu/cgi/viewcontent.cgi?article=1242\&context=njtip 33\. Responsible Disclosure Program \- Homebase, https://www.joinhomebase.com/responsible-disclosure-program 34\. Vulnerability Disclosure Program \- DoIT.maryland.gov., https://doit.maryland.gov/services/cybersecurity/vulnerability\_disclosure\_program/Pages/default.aspx 35\. Secret scanning updates — November 2025 \- GitHub Changelog, https://github.blog/changelog/2025-12-02-secret-scanning-updates-november-2025/ 36\. Secret scanning partner program \- GitHub Docs, https://docs.github.com/code-security/secret-scanning/secret-scanning-partnership-program/secret-scanning-partner-program