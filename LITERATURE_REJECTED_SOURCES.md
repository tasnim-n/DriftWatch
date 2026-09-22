# DriftWatch Rejected Literature Sources

## Purpose

This register records sources screened during Phase 6B but not used as evidence in `PAPER_DRAFT.md`. Rejection does not necessarily imply that a source is poor scholarship; it means the source was unnecessary, weaker than an accepted source for the intended claim, superseded, or mismatched to the claim.

- Sources rejected: **10**
- Search/screening dates: **2026-09-22 to 2026-09-23**

## Rejected sources

| ID | Source considered | Decision reason |
|---|---|---|
| REJ-01 | Abhay Rana and Rushil Nagda, “A Security Analysis of Browser Extensions,” arXiv:1403.3235, 2014. https://arxiv.org/abs/1403.3235 | Preprint status and broad survey framing; stronger peer-reviewed primary sources support the threat-model and permission claims. |
| REJ-02 | Stefan Heule, Devon Rifkin, Alejandro Russo, and Deian Stefan, “The Most Dangerous Code in the Browser,” *HotOS XV*, 2015. https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-heule.pdf | Relevant position paper, but its broad privacy argument duplicates stronger empirical and architecture sources and is not needed for a paper claim. |
| REJ-03 | Sheryl Hsu, Manda Tran, and Aurore Fass, “What is in the Chrome Web Store?” *ACM AsiaCCS 2024*, pp. 785–798. https://doi.org/10.1145/3634737.3637636 | Strong recent ecosystem measurement, but snapshot composition does not directly support the version-pair or update-security claims being made; excluded to avoid unrelated volume. |
| REJ-04 | Hossain Shahriar, Komminist Weldemariam, Mohammad Zulkernine, and Thibaud Lutellier, “Effective Detection of Vulnerable and Malicious Browser Extensions,” *Computers & Security*, vol. 47, pp. 66–84, 2014. https://doi.org/10.1016/j.cose.2014.06.005 | Relevant detection work, but static/dynamic detection coverage is already supported by more directly verified primary sources; no unique claim required it. |
| REJ-05 | P. Phillips et al., *Four Principles of Explainable Artificial Intelligence (Draft)*, NISTIR 8312-draft, 2020. https://doi.org/10.6028/NIST.IR.8312-draft | Superseded by the final 2021 NISTIR 8312, which is cited instead. |
| REJ-06 | Ron Artstein and Massimo Poesio, “Inter-Coder Agreement for Computational Linguistics,” *Computational Linguistics*, vol. 34, no. 4, pp. 555–596, 2008. https://doi.org/10.1162/coli.07-034-R2 | Useful survey, but Cohen's original coefficient and Feinstein–Cicchetti's marginal-distribution analysis directly support the paper's narrow kappa statements. |
| REJ-07 | FIRST, *Common Vulnerability Scoring System v4.0: Specification Document*, version 1.2. https://www.first.org/cvss/v4.0/specification-document | Official and authoritative for vulnerability severity, but CVSS is not the basis of DriftWatch's frozen heuristic review-priority score; citing it risked false equivalence. |
| REJ-08 | `wspr-ncsu/extensiondeltas`, “Extension Deltas” source repository. https://github.com/wspr-ncsu/extensiondeltas | Useful corroborating implementation record, but the peer-reviewed CCS 2020 paper is the authoritative citation for the research claim. |
| REJ-09 | Chromium Blog, “Trustworthy Chrome Extensions, by Default,” 2018. https://blog.chromium.org/2018/10/trustworthy-chrome-extensions-by-default.html | First-party policy context, but peer-reviewed sources provide stronger evidence for architecture and update-delta claims; no platform-policy claim in the paper required it. |
| REJ-10 | Wikipedia, “Browser extension.” https://en.wikipedia.org/wiki/Browser_extension | Secondary, mutable encyclopedia entry; used only as a discovery lead and not as scholarly evidence. |

## Reuse rule

A rejected source may be reconsidered only for a new, precisely matched claim and after metadata and full-text verification. It must not be silently copied into the manuscript because it appears in this screening register.
