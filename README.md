# Iran Crisis Early Warning System (EWS)

نرم‌افزار هشدار اولیه بحران برای ایران: جمع‌آوری ۷ منبع داده، پردازش NLP، گراف دانش، مدل‌سازی (LLM + GNN + Prophet)، بصری‌سازی و گزارش خودکار.

## معماری

```
GitHub (main = single source of truth)
   ⇅
Kaggle Notebook (main compute, T4x2 + Internet)
   ⇅
Colab (backup heavy compute)
```

## ساختار

- `src/` — ماژول‌های اصلی (ingestion, nlp, graph, models, viz, report, utils)
- `notebooks/` — نوت‌بوک‌های Kaggle / Colab / محلی
- `config/` — تنظیمات و الگوی Secrets
- `tests/` — تست‌های خودکار
- `.github/workflows/` — اتوماسیون روزانه و چک امنیتی

## Secrets

مقادیر واقعی فقط در Secrets هر پلتفرم (Kaggle UI / GitHub repo secrets).
فایل `config/secrets_template.yaml` فقط الگو است و مقدار واقعی ندارد.

## امنیتی

- کلیدها هرگز در کد، لاگ یا output چاپ نمی‌شوند (mask).
- pre-commit با gitleaks قبل از هر commit.
- هر API call در `artifacts/logs/api_access.log` ثبت می‌شود.

جزئیات در `SECURITY.md` و `CHANGELOG.md`.
