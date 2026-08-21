# おみくじ・ミニゲーム Discord Bot

既存のおみくじに、じゃんけん、ダイス、人狼ゲームを加えた Discord Bot です。Slash Command と Embed、Button、Select Menu、DM を使用します。

## 機能

- `/omikuji` — おみくじを引きます。1時間のクールダウンがあります。
- `/omikuji_admin` — Bot所有者用。指定ユーザーの次回または毎回の運勢を固定します。
- `/janken` — ボタンでBotとじゃんけんします。
- `/dice 面数:6 個数:1` — 2～1000面のダイスを1～20個振ります。
- `/werewolf` — チャンネル単位で4～12人の人狼ゲームを開始します。

人狼ゲームのセッションは `(Guild ID, Channel ID)` 単位でメモリ上に管理されるため、別チャンネルでは同時に進行できます。役職と夜の能力、投票はDMで通知されます。Botを再起動すると進行中セッションは終了します。

## セットアップ

Python 3.10 以降を推奨します。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

環境変数を設定します。

| 変数 | 必須 | 内容 |
|---|---:|---|
| `DISCORD_TOKEN` | はい | Discord Botトークン |
| `DISCORD_GUILD_ID` | いいえ | 開発用サーバーID。設定時はそのサーバーへ即時同期 |
| `PORT` | いいえ | Keep Alive HTTPサーバーのポート（既定: `10000`） |
| `WEREWOLF_DISCUSSION_TIME` | いいえ | 議論時間（既定: `180`秒） |
| `WEREWOLF_NIGHT_TIME` | いいえ | 夜の選択時間（既定: `60`秒） |
| `WEREWOLF_VOTE_TIME` | いいえ | 投票時間（既定: `60`秒） |

起動します。

```bash
python bot.py
```

Render の Start Command も `python bot.py` のまま使用できます。Keep Alive 用の Flask サーバーは `PORT` で待ち受けます。JSONデータ（`cooldown.json` と `force_result.json`）を再起動後も維持する場合は、永続ディスクを接続してください。

## Discord Developer Portal

1. Bot を作成してトークンを `DISCORD_TOKEN` に設定します。
2. OAuth2 URL Generator で `bot` と `applications.commands` を選択します。
3. Bot Permissions に `View Channels`、`Send Messages`、`Embed Links`、`Read Message History` を許可します。
4. Bot の **Server Members Intent** を有効にします。参加者のサーバー退出を検知するために使用します。Message Content Intent は不要です。
5. 参加者がサーバーメンバーからのDMを許可していることを確認します。開始前に疎通確認を行います。

## テスト

```bash
python -m unittest discover -s tests -v
python -m compileall .
```

Discord上の統合確認では、テスト用 `DISCORD_GUILD_ID` を設定するとコマンド反映が速くなります。
