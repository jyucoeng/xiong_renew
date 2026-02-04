# 🐧 Account Auto-Renewal Script

This project implements an automatic account renewal feature based on GitHub Actions, supporting:

- ✅ Scheduled renewal (runs automatically every 3 days)
- ✅ Telegram notification push (notifies on both success and failure)
- ✅ Global SOCKS5 proxy support

---

## 📅 Automatic Execution Instructions

- By default, GitHub Actions runs automatically every 3 days.
- Manual triggering is also supported (click "Run workflow" on the GitHub page).
- Takes effect after creating Secrets in your forked repository.

---

## 🔐 Environment Variable Configuration (GitHub Secrets)

Go to your repository → Settings → Secrets and variables → Actions → New repository secret, and add the following variables.

| Variable Name | Required | Description |
| --- | --- | --- |
| ARCTIC_USERNAME | ✅ Required | Login username |
| ARCTIC_PASSWORD | ✅ Required | Login password |
| TELEGRAM_BOT_TOKEN | ✅ Recommended | Bot Token for sending Telegram notifications |
| TG_CHAT_ID | ✅ Recommended | Your Telegram account or channel chat_id |
| SOCKS5_PROXY | ✅ Recommended | Use SOCKS5 proxy to access websites (see format below) |

---

## 🌐 SOCKS5_PROXY Example

socks5://username:password@ip:port

---

## 📬 Telegram Setup Guide

1. Search and message @BotFather to create a Bot, and obtain the TELEGRAM_BOT_TOKEN.
2. Send a message to your own Telegram, then visit the following link (replace <YOUR_TOKEN> with your Bot Token):
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
Open it to view and obtain your chat_id.
3. Add TELEGRAM_BOT_TOKEN and TG_CHAT_ID to your GitHub repository Secrets.

---

## 🚀 Usage Instructions

1. Fork this repository to your own GitHub account.
2. Enter your repository and go to Settings → Secrets and variables → Actions to add the Secrets obtained in the previous step.
3. GitHub Actions will automatically run every three days (10 AM Beijing time), and manual triggering is also supported.

---

## GitHub Actions GITHUB_TOKEN (Auto-generated)
### Do I need to create GITHUB_TOKEN manually?

### No. You do not create GITHUB_TOKEN yourself.
### GitHub automatically provides a short-lived token for every workflow run at:

 ${{ secrets.GITHUB_TOKEN }}

You can use it directly in your workflow (as shown below):

env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}


### Note: You won’t see GITHUB_TOKEN in the repository “Secrets” list because it is automatically injected by GitHub at runtime.

### Required permissions for pushing commits

If your workflow needs to git push changes back to the repository, you must grant write access:

In your workflow YAML, keep:

permissions:
  contents: write


### In the repository settings, enable workflow write permissions:

### Repo → Settings → Actions → General → Workflow permissions
### Select:

#### Read and write permissions

If it is set to read-only, git push will fail.

Branch protection can block pushes

Even with correct token permissions, a push may still fail if the target branch is protected (e.g., main requires PRs).

Check:
Repo → Settings → Branches → Branch protection rules

Rules like the following can block direct pushes from Actions:

“Require a pull request before merging”

“Restrict who can push to matching branches”


----
GITHUB_TOKEN 不用你手动创建 —— 只要你的 workflow 在 GitHub Actions 里跑起来，GitHub 会自动为每次运行生成一个临时的 secrets.GITHUB_TOKEN，在 workflow 里直接用就行（你已经在用 ${{ secrets.GITHUB_TOKEN }} 了）。

你需要做的通常是 给它权限、以及确认 checkout 会把它用在 push 上。

1) 你不需要创建：它默认就存在

在 workflow 里这样写就能用：

env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}


这个 secrets.GITHUB_TOKEN 是 GitHub 自动注入的，不会出现在 “Secrets” 列表里让你手动建。

2) 你需要设置的地方：给它写权限

到仓库：

Settings → Actions → General → Workflow permissions

选择：

✅ Read and write permissions

（如果是 “Read repository contents permission” 只读，那 git push 会失败。）

你 workflow 里这段也要保留（你已经写对了）：

permissions:
  contents: write


## 💡 Acknowledgements

- Thanks to the author of the curl_cffi library, which is used in the project to simulate real browser requests.
