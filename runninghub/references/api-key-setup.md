# API Key Setup

## Check Status

Run `--check` first:
```bash
python3 {baseDir}/scripts/runninghub.py --check
```

React by `status`:
- `"ready"` → "账号就绪！积分 {credits}，钱包 {balance} {currency}，想做点什么？生图、视频、配音都可以找我～"（`credits` 为 `unknown` 就不提积分；不要写死 ¥，币种看 `currency`）
- `"no_key"` → Guide: 1) 注册 runninghub.ai 2) 创建 Key 3) 充值 4) 发 Key 给我
- `"no_balance"` → "钱包、积分、旧 RH 币都是 0 了～ 充个值就能继续：https://www.runninghub.ai/vip-rights/4"
- `"invalid_key"` → "Key 不太对，去这里看看：https://www.runninghub.ai/enterprise-api/sharedApi"

### Funds fields (2026-11 Credits switch)

RunningHub moved platform tasks from RH coins to **Credits** (1 USD = 680 credits; the enterprise API uses the wallet balance). `--check` reports each fund separately:

- `credits` — Credits, read from `remainPoint` (live field, not yet in the official doc). `unknown` when the account does not report it (old accounts).
- `coins` — legacy RH coins (`remainCoins`). **`0` after the switch is normal and does not mean the account is out of funds.**
- `balance` + `currency` — wallet (`remainMoney`).
- `funding_status` — `available` (some fund > 0), `empty` (every fund reported and all 0 → `status: no_balance`), `unknown` (nothing positive and a field is missing; **never treat this as 0** — submit, and only a real "insufficient balance" reply from the task counts).
- `funded_by` — which funds are > 0.

Never say "额度不足 / 点数不够" from `coins: "0"` alone. Only `status: no_balance` or an `INSUFFICIENT_BALANCE` error from an actual submission means the account is out of funds.

## Save Key

When user sends a key, verify with `--check --api-key THE_KEY`. If valid, save it:

```bash
python3 -c "
import json, pathlib
p = pathlib.Path.home() / '.openclaw' / 'openclaw.json'
p.parent.mkdir(exist_ok=True)
cfg = json.loads(p.read_text()) if p.exists() else {}
cfg.setdefault('skills', {}).setdefault('entries', {}).setdefault('runninghub', {})['apiKey'] = 'THE_KEY'
p.write_text(json.dumps(cfg, indent=2))
"
```

Replace `THE_KEY` with the actual key. OpenClaw auto-injects it as `RUNNINGHUB_API_KEY` env var via `primaryEnv`.
