# Security Policy

## اصول
1. کلیدها فقط از Secrets پلتفرم مربوطه بارگذاری می‌شوند (Kaggle Secrets / Colab userdata / GitHub Actions secrets / .env محلی).
2. هیچ کلیدی در کد، لاگ، output نوت‌بوک یا commit چاپ نمی‌شود — همیشه `mask_key()`.
3. `.env` و `kaggle.json` در `.gitignore` هستند و هرگز commit نمی‌شوند.
4. pre-commit (gitleaks + no-api-keys) قبل از هر commit اجرا می‌شود.
5. هر API call در `artifacts/logs/api_access.log` با کلید masked ثبت می‌شود.
6. در نبود کلید: توقف فوری + گزارش + سه گزینه (skip / add key / stop). auto-skip ممنوع.

## چرخه حیات کلیدها
- Rotate هر 90 روز (ACLED, FIRMS)
- در صورت لو رفتن: revoke فوری در سرویس اصلی
- Rate limit management با backoff نمایی

## چک‌لیست Public کردن Notebook
- [ ] Clear all cell outputs
- [ ] هیچ cell کلید چاپ نمی‌کند
- [ ] metadata بدون secret
- [ ] artifact های حساس share نشده
- [ ] pre-commit پاس شده
