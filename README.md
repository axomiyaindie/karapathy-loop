 <p align="center">
  <img src="assets/karapathy-loop.svg" alt="karapathy-loop logo" width="650">
</p>

<h1 align="center">karapathy-loop</h1>

<p align="center">
  <strong>A Recursive Self-Improvement Agent Framework</strong>
</p>

<p align="center">
  Propose · Evaluate · Improve
</p>

---

**An experimental self-improving AI agent framework.**

An independent experiment exploring how AI agents can propose improvements to their own software, test those improvements, and optionally adopt successful changes.

[GitHub Repository](https://github.com/axomiyaindie/karapathy-loop) · [Contributing Guidelines](CONTRIBUTING.md)

## Getting started

### Requirements

- Windows 10 or 11
- Python 3.12
- Git
- Docker Desktop
- An API key from OpenAI or Anthropic

### 1. Download the project

Open PowerShell:

```powershell
git clone https://github.com/axomiyaindie/karapathy-loop.git
cd karapathy-loop
```

### 2. Create a Python environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure your API key

```powershell
Copy-Item .env.example .env
notepad .env
```

Add your API key and the model identifier supported by your provider.

Never publish your `.env` file or expose your API credentials.

### 5. Start Docker Desktop

Install and open [Docker Desktop](https://www.docker.com/products/docker-desktop/).

Wait until Docker reports that its engine is running.

### 6. Run the initial tests

```powershell
New-Item -ItemType Directory -Force .agent_sandbox | Out-Null
Copy-Item src\agent\live_agent.py .agent_sandbox\temp_agent.py -Force

python tests\immutable_ruler.py
python tests\run_challenge.py
python -m pytest -v
```
These direct evaluator commands run on the host against the current production agent. They do not verify Docker isolation. Candidate isolation is tested through the supervisor's Docker-backed evaluation.

### 7. Start karapathy-loop

```powershell
python src\loop\main_loop.py
```

Starting the supervisor makes live AI provider requests and may incur API costs.

Automatic Git commits and pushes are disabled by default. Keep them disabled while experimenting.

## Important

This is an experimental project. AI-generated changes may contain errors. Tests and Docker restrictions reduce risks but do not guarantee complete security.

Always review proposed changes and keep backups of important files.

## Inspiration

Inspired by the experiments and ideas of [Andrej Karpathy](https://github.com/karpathy).

This is an independent project and is not affiliated with or endorsed by Andrej Karpathy.

## Contributing

Interested in improving the project?

Read [CONTRIBUTING.md](CONTRIBUTING.md) for development instructions, project architecture, testing guidance, and contribution guidelines.

---

**Project status:** Experimental · Under active development

*Explore. Experiment. Evaluate. Improve.*
