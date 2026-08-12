
| Dimension | GEPA | VISTA | SkillOpt |
|---|---|---|---|
| Main search style | Evolutionary candidate pool | Evolutionary pool + semantic trace | Single artifact, bounded edits |
| Candidate selection | Pareto frontier | Pareto frontier | Held-out validation gate |
| Diagnosis and rewrite | Collapsed in one reflection call | Explicitly separated | Usually combined in edit proposal, but edits are structured |
| Root-cause labels | Not recorded | Recorded on every successful edge | Captured through edit rationales, rejected buffer, slow/meta memory |
| Number of prompts per round | Usually one mutation candidate | K hypothesis-specific candidates | One candidate skill after merging/ranking edits |
| Exploration | Pareto diversity and optional merge | Pareto diversity + random restart + epsilon-greedy hypotheses | Batch variation + rejected-buffer feedback + epoch memory |
| Update granularity | Prompt/module mutation | Hypothesis-targeted prompt rewrite | ADD/DELETE/REPLACE bounded patch edits |
| Main failure addressed | Sample-efficient prompt search | Black-box / label-free reflective search | Unstable, uncontrolled text rewriting |
| Best for | Exploring diverse prompt variants | Auditable and robust prompt optimization | Stable training of one reusable skill/policy artifact |

