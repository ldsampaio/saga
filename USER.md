# USER.md — who the user is

## Identity
- **Name/role:** Professor at UTFPR (Universidade Tecnológica Federal do Paraná), sole maintainer of SGOA (Sistema de Gestão de Aconselhamento / academic-advising system).
- **Deploys to:** a university server behind nginx + Cloudflared; Docker Compose with Postgres, Kafka, and workers.
- **Language:** writes and reads Portuguese (pt-BR) — reply in Portuguese unless he switches.

## Working style
- **Works in stages:** wants a review checkpoint before the next stage advances ("revisar as mudanças antes de seguir").
- **Grants autonomy within a stage:** "continue aplicando as correções", "vamos seguir" — but reviews between stages.
- **Ordered instruction (1-2-3):** issues numbered instructions (1, 2, 3) and expects them executed in sequence **without asking anything and without pausing**. Only stops when all tasks are completed. Example: "execute o 1, 2 e 3 em sequencia sem me perguntar nada", "faça o 1 e depois siga para a fase 2", "commit e push".
- **Credential handling (constitutional):** credentials must NEVER be stored in a file, even a gitignored `credentials.env` — the app reads them from the Hermes vault at runtime and discards them immediately. This is a non-negotiable principle (RNF-02 / RRF-02).

## Communication preferences
- Gives numbered option lists and expects short picks ("1 - Autorizado").
- Expects action: when a login error is reported ("Diagnostique o problema e faça a correção"), diagnosis and correction are the priority, before continuing.
- Frustration about verbosity or format is a first-class skill signal — embed the lesson in the skill that governs that task.
