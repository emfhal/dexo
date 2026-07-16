# Contributing to Dexo

First off, thank you for considering contributing to Dexo! It's people like you that make open-source software such a great community to learn, inspire, and create.

To ensure a smooth workflow and clean history, we strictly enforce an issue-driven workflow. Please read through these guidelines before submitting a Pull Request.

## 1. Open an Issue First

**Do not write any code before opening an issue.** 

To maintain a clean and trackable project history, every Pull Request must be tied to an open issue. 
1. Go to the [Issues page](https://github.com/emfhal/dexo/issues) and open a new issue describing the bug you want to fix or the feature you want to build.
2. Wait for a maintainer to approve or assign the issue to you.
3. Take note of the **Issue Number** (e.g., `#1`). You will use this number (e.g., `DEXO-1`) as your prefix for all branches and commits.

## 2. Local Setup

Once you have your issue number, fork the repository and clone it locally:

```bash
git clone git@github.com:<your-username>/dexo.git
cd dexo
git remote add upstream git@github.com:emfhal/dexo.git
```

Set up the environment using `uv`:
```bash
uv sync --all-groups
cp .env.example .env
```

## 3. Branching and Committing

Create a feature branch prefixed with your issue number. For example, if you are working on Issue #1:
```bash
git checkout -b DEXO-1-add-amazing-feature
```

As you make changes, ensure your commit messages also follow the strict prefix convention:
```bash
git commit -m "DEXO-1 - Add amazing feature"
```

## 4. Testing and Linting

Before opening a Pull Request, you must ensure your code passes all formatting, linting, and testing checks. Our `Makefile` provides commands for this:

```bash
make format
make lint
make typecheck
make test
```

## 5. Opening a Pull Request

1. Fetch the latest changes from upstream and rebase to ensure a clean, linear history:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. Push your branch to your fork:
   ```bash
   git push -u origin DEXO-1-add-amazing-feature
   ```
3. Open a Pull Request on the main repository. In the PR description, explicitly reference the issue it resolves so GitHub links them automatically (e.g., `Resolves #1`).

Maintainers will review your PR. Once approved, it will be squash-merged into the `main` branch. 

Happy coding!
