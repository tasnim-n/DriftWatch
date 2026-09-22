# DriftWatch Verified Literature Sources

## Scope and verification status

This bibliography records only sources accepted for Phase 6B. Metadata and claim fit were checked against publisher, conference, journal, standards-body, or author-hosted full-text records on 2026-09-22 and 2026-09-23. Citation numbers match `PAPER_DRAFT.md`.

- Accepted sources: **22**
- Peer-reviewed conference/journal sources: **21**
- Official technical reports: **1**
- Other reputable sources used as paper evidence: **0**
- Citation style: temporary numbered references, pending venue selection

## Accepted sources

### DW-LIT-01 / [1] — BARTH2010

- **Citation:** Adam Barth, Adrienne Porter Felt, Prateek Saxena, and Aaron Boodman. “Protecting Browsers from Extension Vulnerabilities.” *NDSS Symposium 2010*. 2010.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.ndss-symposium.org/ndss2010/protecting-browsers-extension-vulnerabilities/
- **Supports:** Extension privilege boundaries; least privilege, privilege separation, and isolation as browser-extension security mechanisms.
- **Verification:** NDSS record and paper metadata checked; title, authors, event, and date agree.
- **Limit:** Architecture and vulnerability mitigation, not malicious-update detection or a validation of DriftWatch.

### DW-LIT-02 / [2] — CARLINI2012

- **Citation:** Nicholas Carlini, Adrienne Porter Felt, and David Wagner. “An Evaluation of the Google Chrome Extension Security Architecture.” In *21st USENIX Security Symposium (USENIX Security 12)*, pp. 97–111. USENIX Association, 2012.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/carlini
- **Supports:** Empirical limits of Chrome isolation, privilege separation, and permission mechanisms; extension vulnerability threat models.
- **Verification:** USENIX page, abstract, and BibTeX checked.
- **Limit:** Reviews single extension versions and vulnerabilities; does not study longitudinal version-pair drift.

### DW-LIT-03 / [3] — BANDHAKAVI2010

- **Citation:** Sruthi Bandhakavi, Samuel T. King, P. Madhusudan, and Marianne Winslett. “VEX: Vetting Browser Extensions for Security Vulnerabilities.” In *19th USENIX Security Symposium (USENIX Security 10)*, pp. 339–354. USENIX Association, 2010.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.usenix.org/conference/usenixsecurity10/vex-vetting-browser-extensions-security-vulnerabilities
- **Supports:** Static, context- and flow-sensitive information-flow analysis for extension source-to-sink patterns; review-assistance motivation.
- **Verification:** USENIX record and full proceedings checked; title, authors, venue, year, and pages agree.
- **Limit:** Targets vulnerable legacy Firefox extensions and assumes non-obfuscated benign code; it does not classify malicious updates.

### DW-LIT-04 / [4] — KAPRAVELOS2014

- **Citation:** Alexandros Kapravelos, Chris Grier, Neha Chachra, Christopher Kruegel, Giovanni Vigna, and Vern Paxson. “Hulk: Eliciting Malicious Behavior in Browser Extensions.” In *23rd USENIX Security Symposium (USENIX Security 14)*, pp. 641–654. USENIX Association, 2014.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.usenix.org/conference/usenixsecurity14/technical-sessions/presentation/kapravelos
- **Supports:** Dynamic behavior elicitation, event fuzzing, network monitoring, and the need to trigger extension behavior.
- **Verification:** USENIX page, full text, and BibTeX checked.
- **Limit:** Runtime observations depend on elicitation coverage; it does not provide DriftWatch-style static heterogeneous deltas.

### DW-LIT-05 / [5] — FASS2021

- **Citation:** Aurore Fass, Dolière Francis Somé, Michael Backes, and Ben Stock. “DoubleX: Statically Detecting Vulnerable Data Flows in Browser Extensions at Scale.” In *Proceedings of the 2021 ACM SIGSAC Conference on Computer and Communications Security*, pp. 1789–1804. ACM, 2021.
- **Type:** Peer-reviewed security conference paper.
- **DOI:** https://doi.org/10.1145/3460120.3484745
- **Supports:** Extension-specific static dependence graphs, pointer/control/data-flow analysis, message interactions, and sensitive API source-to-sink analysis.
- **Verification:** DOI metadata, author full text, and institutional publication record checked.
- **Limit:** Detects potentially vulnerable flows in a snapshot; it does not show runtime reachability or malicious intent.

### DW-LIT-06 / [6] — WANG2018

- **Citation:** Yao Wang, Wandong Cai, Pin Lyu, and Wei Shao. “A Combined Static and Dynamic Analysis Approach to Detect Malicious Browser Extensions.” *Security and Communication Networks*, vol. 2018, Article 7087239, 2018.
- **Type:** Peer-reviewed journal article.
- **DOI:** https://doi.org/10.1155/2018/7087239
- **Supports:** Combined manifest/source and sandbox-runtime features for supervised malicious-extension classification.
- **Verification:** Publisher page and full text checked; authors, dates, article identifier, and DOI agree.
- **Limit:** Its binary classification target and reported corpus performance are not comparable to DriftWatch's review-priority objective or current dataset.

### DW-LIT-07 / [7] — FELT2011

- **Citation:** Adrienne Porter Felt, Kate Greenwood, and David Wagner. “The Effectiveness of Application Permissions.” In *2nd USENIX Conference on Web Application Development (WebApps 11)*, pp. 75–86. USENIX Association, 2011.
- **Type:** Peer-reviewed conference paper.
- **Stable record:** https://www.usenix.org/conference/webapps11/effectiveness-application-permissions
- **Supports:** Chrome extension permission declarations, review triage, warning frequency, granularity, wildcard access, and unnecessary permissions.
- **Verification:** USENIX page and full proceedings checked.
- **Limit:** Its Chrome permission model is historical; it supports principles and measured limitations, not current Manifest V3 semantics in every detail.

### DW-LIT-08 / [8] — JAGPAL2015

- **Citation:** Nav Jagpal, Eric Dingle, Jean-Philippe Gravel, Panayiotis Mavrommatis, Niels Provos, Moheeb Abu Rajab, and Kurt Thomas. “Trends and Lessons from Three Years Fighting Malicious Extensions.” In *24th USENIX Security Symposium (USENIX Security 15)*, pp. 579–593. USENIX Association, 2015.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/jagpal
- **Supports:** Large-scale malicious-extension detection using code, behavior, and developer-reputation evidence; adaptive threats and human-expert correction.
- **Verification:** USENIX page, abstract, full text, and BibTeX checked.
- **Limit:** Store-deployment findings and its maliciousness classifier do not establish DriftWatch performance or present-day prevalence.

### DW-LIT-09 / [9] — PANTELAIOS2020

- **Citation:** Nikolaos Pantelaios, Nick Nikiforakis, and Alexandros Kapravelos. “You've Changed: Detecting Malicious Browser Extensions through their Update Deltas.” In *Proceedings of the 2020 ACM SIGSAC Conference on Computer and Communications Security*, pp. 477–491. ACM, 2020.
- **Type:** Peer-reviewed security conference paper.
- **DOI:** https://doi.org/10.1145/3372297.3423343
- **Supports:** Longitudinal extension-version collection; update deltas as the central object; API-sequence representation of added code; discovery of malicious update clusters.
- **Verification:** DOI, paper first page/full text, DBLP metadata, and authors' repository checked.
- **Limit:** This is the nearest work, but its two-stage malicious-extension discovery goal and API-sequence clustering differ from DriftWatch's multi-family review prioritization and governance workflow.

### DW-LIT-10 / [10] — TORRESARIAS2019

- **Citation:** Santiago Torres-Arias, Hammad Afzali, Trishank Karthik Kuppusamy, Reza Curtmola, and Justin Cappos. “in-toto: Providing farm-to-table guarantees for bits and bytes.” In *28th USENIX Security Symposium (USENIX Security 19)*, pp. 1393–1410. USENIX Association, 2019.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias
- **Supports:** Software supply-chain steps as compromise points and cryptographic provenance across build/release workflows.
- **Verification:** USENIX page, full text, and BibTeX checked.
- **Limit:** General software-supply-chain evidence; it neither studies browser-extension semantics nor validates DriftWatch signals.

### DW-LIT-11 / [11] — KUPPUSAMY2017

- **Citation:** Trishank Karthik Kuppusamy, Vladimir Diaz, and Justin Cappos. “Mercury: Bandwidth-Effective Prevention of Rollback Attacks Against Community Repositories.” In *2017 USENIX Annual Technical Conference (USENIX ATC 17)*, pp. 673–688. USENIX Association, 2017.
- **Type:** Peer-reviewed systems conference paper.
- **Stable record:** https://www.usenix.org/conference/atc17/technical-sessions/presentation/kuppusamy
- **Supports:** Repository compromise, rollback attacks, and the security significance of authenticated version ordering.
- **Verification:** USENIX page, full text, and BibTeX checked.
- **Limit:** Concerns repository metadata and rollback prevention, not semantic analysis of extension updates.

### DW-LIT-12 / [12] — JACKSON1994

- **Citation:** Daniel Jackson and David A. Ladd. “Semantic Diff: A Tool for Summarizing the Effects of Modifications.” In *Proceedings of the International Conference on Software Maintenance*, pp. 243–252. IEEE, 1994.
- **Type:** Peer-reviewed software-engineering conference paper.
- **DOI:** https://doi.org/10.1109/ICSM.1994.336770
- **Supports:** Comparing program versions through observable semantic effects rather than textual differences.
- **Verification:** IEEE record, DBLP metadata, and author-hosted abstract checked.
- **Limit:** Procedure-level semantic differencing; it does not provide extension-specific or security-classification guarantees.

### DW-LIT-13 / [13] — PERSON2008

- **Citation:** Suzette Person, Matthew B. Dwyer, Sebastian G. Elbaum, and Corina S. Păsăreanu. “Differential Symbolic Execution.” In *Proceedings of the 16th ACM SIGSOFT International Symposium on Foundations of Software Engineering*, pp. 226–237. ACM, 2008.
- **Type:** Peer-reviewed software-engineering conference paper.
- **DOI:** https://doi.org/10.1145/1453101.1453131
- **Supports:** Change-aware symbolic execution and affected-path behavioral comparison between program versions.
- **Verification:** DOI and independent bibliographic records checked against the paper citation.
- **Limit:** Symbolic program semantics differ materially from DriftWatch's bounded static feature deltas.

### DW-LIT-14 / [14] — GAMA2014

- **Citation:** João Gama, Indrė Žliobaitė, Albert Bifet, Mykola Pechenizkiy, and Abdelhamid Bouchachia. “A Survey on Concept Drift Adaptation.” *ACM Computing Surveys*, vol. 46, no. 4, Article 44, pp. 1–37, 2014.
- **Type:** Peer-reviewed academic survey.
- **DOI:** https://doi.org/10.1145/2523813
- **Supports:** Statistical concept-drift terminology, changing input-target relationships, adaptive learning, and temporal evaluation context.
- **Verification:** ACM article record and metadata checked.
- **Limit:** Statistical concept drift is not equivalent to DriftWatch's static behavioral differences; the paper cites it only to make that distinction.

### DW-LIT-15 / [15] — PHILLIPS2021

- **Citation:** P. Jonathon Phillips, Carina Hahn, Peter Fontana, Amy Yates, Kristen K. Greene, David A. Broniatowski, and Mark A. Przybocki. *Four Principles of Explainable Artificial Intelligence*. NISTIR 8312. National Institute of Standards and Technology, 2021.
- **Type:** Official government technical report.
- **DOI:** https://doi.org/10.6028/NIST.IR.8312
- **Supports:** Explanation, meaningfulness to recipients, explanation accuracy, and knowledge limits as distinct explainability properties.
- **Verification:** Final NIST publication record and report checked; the superseded draft was not cited.
- **Limit:** General explainability principles; it is not a user study of DriftWatch or a security-alert standard.

### DW-LIT-16 / [16] — ALAHMADI2022

- **Citation:** Bushra A. Alahmadi, Louise Axon, and Ivan Martinovic. “99% False Positives: A Qualitative Study of SOC Analysts' Perspectives on Security Alarms.” In *31st USENIX Security Symposium (USENIX Security 22)*, pp. 2783–2800. USENIX Association, 2022.
- **Type:** Peer-reviewed security conference paper.
- **Stable record:** https://www.usenix.org/conference/usenixsecurity22/presentation/alahmadi
- **Supports:** Manual alarm validation, the role of benign contextual triggers, and analyst requirements for explainable and contextual alarms.
- **Verification:** USENIX page, full text, and BibTeX checked.
- **Limit:** Qualitative SOC findings do not prove that DriftWatch explanations improve efficiency or decision quality.

### DW-LIT-17 / [17] — CRANOR2008

- **Citation:** Lorrie Faith Cranor. “A Framework for Reasoning About the Human in the Loop.” In *Usability, Psychology, and Security 2008 (UPSEC 08)*. USENIX Association, 2008.
- **Type:** Peer-reviewed security/usability workshop paper.
- **Stable record:** https://www.usenix.org/conference/upsec-08/framework-reasoning-about-human-loop
- **Supports:** Treating human security tasks, communications, and failure modes as part of system design.
- **Verification:** USENIX record and full text checked.
- **Limit:** Conceptual framework; it does not prescribe DriftWatch's blind-review or adjudication protocol.

### DW-LIT-18 / [18] — COHEN1960

- **Citation:** Jacob Cohen. “A Coefficient of Agreement for Nominal Scales.” *Educational and Psychological Measurement*, vol. 20, no. 1, pp. 37–46, 1960.
- **Type:** Peer-reviewed methodological journal article.
- **DOI:** https://doi.org/10.1177/001316446002000104
- **Supports:** Definition and use of chance-corrected agreement for two raters assigning nominal categories.
- **Verification:** SAGE journal record checked for title, author, volume, issue, pages, and DOI.
- **Limit:** Does not justify universal qualitative labels for kappa values or turn agreement into accuracy.

### DW-LIT-19 / [19] — FEINSTEIN1990

- **Citation:** Alvan R. Feinstein and Domenic V. Cicchetti. “High Agreement but Low Kappa: I. The Problems of Two Paradoxes.” *Journal of Clinical Epidemiology*, vol. 43, no. 6, pp. 543–549, 1990.
- **Type:** Peer-reviewed methodological journal article.
- **DOI:** https://doi.org/10.1016/0895-4356(90)90158-L
- **Supports:** Sensitivity of kappa to imbalanced marginal totals and the need for cautious interpretation.
- **Verification:** PubMed metadata and DOI checked.
- **Limit:** Binary clinical-rating examples; it supports the marginal-distribution caveat, not a qualitative label for DriftWatch's kappa.

### DW-LIT-20 / [20] — HE2009

- **Citation:** Haibo He and Edwardo A. Garcia. “Learning from Imbalanced Data.” *IEEE Transactions on Knowledge and Data Engineering*, vol. 21, no. 9, pp. 1263–1284, 2009.
- **Type:** Peer-reviewed academic survey.
- **DOI:** https://doi.org/10.1109/TKDE.2008.239
- **Supports:** Learning and metric challenges caused by underrepresented classes and severe class skew.
- **Verification:** IEEE record checked for authors, journal, volume, issue, pages, year, and DOI.
- **Limit:** General imbalance survey; it does not quantify instability for DriftBench's particular split.

### DW-LIT-21 / [21] — VARMA2006

- **Citation:** Sudhir Varma and Richard Simon. “Bias in Error Estimation When Using Cross-Validation for Model Selection.” *BMC Bioinformatics*, vol. 7, Article 91, 2006.
- **Type:** Peer-reviewed methodological journal article.
- **DOI:** https://doi.org/10.1186/1471-2105-7-91
- **Supports:** Optimistic bias when tuning and estimating error in the same cross-validation process; need for nested or independent evaluation.
- **Verification:** Publisher full-text record checked.
- **Limit:** Simulation and bioinformatics context; supports evaluation design principles, not DriftWatch performance claims.

### DW-LIT-22 / [22] — KAPOOR2023

- **Citation:** Sayash Kapoor and Arvind Narayanan. “Leakage and the Reproducibility Crisis in Machine-Learning-Based Science.” *Patterns*, vol. 4, no. 9, Article 100804, 2023.
- **Type:** Peer-reviewed journal article and systematic cross-field analysis.
- **DOI:** https://doi.org/10.1016/j.patter.2023.100804
- **Supports:** Data leakage taxonomy, overoptimistic performance claims, and temporal/train-test separation concerns.
- **Verification:** Publisher article and author full text checked for metadata and claims.
- **Limit:** Cross-disciplinary methodological evidence; it does not establish that DriftWatch's completed leakage audit is exhaustive.

## Claim-use rule

These sources support background, prior-work comparisons, and methodological cautions only. DriftWatch corpus counts, scores, experiment outcomes, human agreement, adjudication results, and Gold Set properties remain supported by project artifacts listed in `PAPER_EVIDENCE_MAP.md`.
