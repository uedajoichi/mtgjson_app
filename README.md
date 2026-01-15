# MTG Internal API

Magic: The Gathering のカード情報を提供する内部 API。MTGJSON データを SQLite で効率的に処理し、マイクロサービス構成で運用。

## プロジェクト構成

```
.
├── packages/                          # 共有パッケージ
│   ├── mtg_internal_client/           # 他サービス向けクライアント SDK
│   │   └── mtg_internal_client/
│   │       ├── client.py              # SQLite クエリラッパー
│   │       ├── models.py              # データモデル
│   │       ├── auth.py                # 認証 (stub)
│   │       └── ...
│   ├── mtg_internal_core/             # 共通ビジネスロジック (DB、Repo、Schema)
│   └── mtg_internal_etl/              # ETL ユーティリティ
│       ├── sqlite_downloader.py       # SQLite ダウンロード
│       └── sqlite_init.py             # DB 初期化・インデックス
├── services/
│   ├── mtg_internal_api/              # FastAPI サーバー
│   │   ├── app/main.py                # エンドポイント定義
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── mtg_internal_etl_runner/       # ETL バッチ（ECS Task 想定）
│       ├── etl_runner.py              # SQLite DL + 初期化実行
│       ├── Dockerfile
│       └── requirements.txt
├── docker-compose.yml                 # ローカル開発環境
└── data/                              # SQLite DB（.gitignore）
    └── AllPrintings.sqlite            # MTG カード情報
```

## クイックスタート（Docker）

### 前提条件

- Docker & Docker Compose

### 起動

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

**初回起動時**:

- ETL ランナーが MTGJSON から `AllPrintings.sqlite` を自動ダウンロード（数分かかります）
- ダウンロード完了後、API は `http://localhost:8000` で利用可能

### API エンドポイント

**健全性確認**:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**基本検索 — カード名で検索（推奨）**:

```bash
curl "http://localhost:8000/cards?q=Black&limit=10"
# {"query":"Black","results":[...],"count":3}
```

**複合検索 — 複数条件で詳細検索**:

```bash
# 黒色のクリーチャーを検索
curl "http://localhost:8000/cards/advanced?colors=B&type=Creature&limit=20"

# 赤か緑色で、レアリティがRareのカード（Blackを含む）
curl "http://localhost:8000/cards/advanced?name=Black&colors=R,G&rarity=Rare"

# 特定セット（LEA）内のすべてのカードを検索
curl "http://localhost:8000/cards/advanced?set=LEA&limit=100"

# マナコスト0のアーティファクト
curl "http://localhost:8000/cards/advanced?mana_cost=0&type=Artifact&limit=50"

# 複数条件の組み合わせ（名前 + 色 + タイプ + レアリティ）
curl "http://localhost:8000/cards/advanced?name=Lotus&colors=B,G&type=Artifact&rarity=Mythic"
```

**複合検索のフィルタ一覧**:

| パラメータ  | 説明                                       | 例                                           |
| ----------- | ------------------------------------------ | -------------------------------------------- |
| `name`      | カード名（部分一致、大文字小文字区別なし） | `Black`, `Dragon`                            |
| `colors`    | カラー（カンマ区切り）                     | `B` (黒), `W,U` (白青), `R,G` (赤緑)         |
| `type`      | カードタイプ（部分一致）                   | `Creature`, `Sorcery`, `Land`, `Enchantment` |
| `mana_cost` | マナコスト（部分一致）                     | `0`, `{1}{B}`, `{X}`                         |
| `set`       | セットコード（完全一致）                   | `LEA`, `2ED`, `ARB`, `M21`                   |
| `rarity`    | レアリティ（部分一致）                     | `Common`, `Uncommon`, `Rare`, `Mythic Rare`  |
| `limit`     | 結果数上限（1-100、デフォルト: 10）        | `10`, `50`, `100`                            |

**単一カード検索（互換性保持）**:

```bash
curl "http://localhost:8000/cards/Black%20Lotus"
# {"found":true,"card":{...}}
```

**セット一覧**:

```bash
curl http://localhost:8000/sets
# {"sets":[...],"count":...}
```

## パッケージ説明

### `mtg_internal_client`

他のアプリケーション向けの SDK。SQLite クエリの薄いラッパー。

```python
from mtg_internal_client import client

# カード検索
cards = client.find_cards("Black", limit=10)
card = client.get_card_by_name("Black Lotus")

# セット取得
sets = client.get_sets()
```

### `mtg_internal_core`

データモデル、DB セッション、リポジトリ層（将来拡張用）。

### `mtg_internal_etl`

SQLite ダウンロード・初期化ロジック。ETL タスクで使用。

## 環境変数

- `MTG_DB_PATH`: SQLite DB パス（デフォルト: `data/AllPrintings.sqlite`）
- `PYTHONUNBUFFERED`: ログ出力を即座に表示（Docker で設定済み）

## パフォーマンス

- **SQLite 活用**: JSON メモリ全ロード廃止 → 低メモリ使用
- **インデックス**: カード名で自動作成（検索高速化）
- **キャッシング**: 接続キャッシング、接続プール対応可能

## 将来の拡張

- **SDK 生成**: OpenAPI → TypeScript / Python SDK（`tools/generate-sdks.sh`）
- **CI/CD**: GitHub Actions で OpenAPI 生成・SDK 配布
- **ECS デプロイ**: ETL ランナーを定期 Task、API を ECS Service で運用
- **DB**: SQLite → PostgreSQL への切り替え対応

## トラブルシューティング

### 「Read-only file system」エラー

docker-compose.yml で `data` ボリュームが読み取り専用になっていないか確認。

### 「AllPrintings.sqlite not found」

ETL ランナーのログを確認。ダウンロード中の可能性あり:

```bash
docker compose logs -f etl-runner
```

### 検索が空で返る

SQLite が完全にダウンロード・初期化されているか確認:

```bash
docker compose exec api sqlite3 /app/data/AllPrintings.sqlite "SELECT COUNT(*) FROM cards LIMIT 1"
```

## ライセンス

MTGJSON データは公式ライセンスに従う。本プロジェクトは MIT ライセンス。
