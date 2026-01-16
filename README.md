# MTG Internal API

Magic: The Gathering のカード情報を提供する内部 API。MTGJSON データを SQLite で効率的に処理し、マイクロサービス構成で運用。

## プロジェクト構成

```
.
├── packages/                          # 共有パッケージ
│   ├── mtg_internal_client/           # 他サービス向けクライアント SDK
│   │   └── mtg_internal_client/
│   │       ├── client.py              # SQLite クエリラッパー（多言語検索対応）
│   │       ├── models.py              # データモデル
│   │       ├── auth.py                # 認証 (stub)
│   │       └── ...
│   ├── mtg_internal_core/             # 共通ビジネスロジック (DB、Repo、Schema)
│   └── mtg_internal_etl/              # ETL ユーティリティ
│       ├── sqlite_downloader.py       # SQLite ダウンロード（差分検知対応）
│       ├── sqlite_init.py             # DB 初期化・インデックス
│       ├── sqlite_reader.py           # データ抽出（NEW!）
│       ├── upsert.py                  # バッチ投入（NEW!）
│       ├── etl.py                     # ETL パイプライン（NEW!）
│       └── migrate.py                 # マイグレーション管理（NEW!）
├── services/
│   ├── mtg_internal_api/              # FastAPI サーバー
│   │   ├── app/main.py                # エンドポイント定義（多言語検索対応）
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── mtg_internal_etl_runner/       # ETL バッチ（ECS Task 想定）
│       ├── etl_runner.py              # SQLite DL + 初期化 + マイグレーション + ETL実行
│       ├── Dockerfile
│       └── requirements.txt
├── docker-compose.yml                 # ローカル開発環境
├── README.md                          # このファイル
└── data/                              # SQLite DB（.gitignore）
    ├── AllPrintings.sqlite            # MTG カード情報
    └── sync_state.json                # ダウンロード状態管理
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
- データベースマイグレーション実行（`foreign_data` テーブル作成）
- ETL 処理で外国語翻訳データを抽出・投入
- ダウンロード完了後、API は `http://localhost:8000` で利用可能

### API エンドポイント

**健全性確認**:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**統計情報取得**:

```bash
curl http://localhost:8000/stats
# {"total_cards":28000,"total_sets":500}
```

**基本検索 — カード名で検索（推奨）**:

```bash
curl "http://localhost:8000/cards?q=Black&limit=10"
# {"query":"Black","results":[...],"count":3}
```

**多言語検索 — 外国語でカード検索（NEW!）**:

```bash
# 日本語で検索
curl "http://localhost:8000/cards/search?q=ブラック&lang=ja&limit=5"
# {"query":"ブラック","language":"ja","results":[...],"count":3}

# フランス語で検索
curl "http://localhost:8000/cards/search?q=noir&lang=fr&limit=5"

# その他の言語（German, Spanish, Italian, Portuguese, Russian, Chinese Simplified など）
curl "http://localhost:8000/cards/search?q=黑&lang=zhs&limit=5"
```

**カード翻訳情報取得 — 指定カードの全言語版（NEW!）**:

```bash
curl "http://localhost:8000/cards/{uuid}/translations"
# {
#   "found": true,
#   "card": {
#     "uuid": "...",
#     "name": "Black Lotus",
#     "english_name": "Black Lotus",
#     "foreign_data": [
#       {"language": "Japanese", "name": "黒い蓮", "text": "..."},
#       {"language": "French", "name": "Lotus noir", "text": "..."},
#       ...
#     ]
#   }
# }
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

**多言語検索フィルタ一覧**:

| パラメータ | 説明                                             | 例                                                                                                                         |
| ---------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `q`        | 検索キーワード（部分一致、大文字小文字区別なし） | `ブラック`, `noir`, `黑`                                                                                                   |
| `lang`     | 言語コード                                       | `ja` (日本語), `fr` (フランス語), `de` (ドイツ語), `zhs` (簡体字中国語), `zht` (繁体字中国語), `it`, `pt`, `ru`, `es` など |
| `limit`    | 結果数上限（1-100、デフォルト: 10）              | `10`, `50`, `100`                                                                                                          |

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

# 多言語検索 (NEW!)
japanese_cards = client.find_cards_by_language("ブラック", "Japanese", limit=10)
card_with_translations = client.get_card_with_translations(card_uuid)

# セット取得
sets = client.get_sets()

# 統計情報取得 (NEW!)
total_cards = client.count_cards()
```

### `mtg_internal_core`

データモデル、DB セッション、リポジトリ層（将来拡張用）。

### `mtg_internal_etl`

SQLite ダウンロード・初期化・マイグレーション・ETL ロジック。ETL タスクで使用。

**主要モジュール**:

- `sqlite_downloader.py`: MTGJSON からデータベースをダウンロード（差分検知対応）
- `sqlite_init.py`: 初期インデックス作成
- `migrate.py`: マイグレーション管理（`foreign_data` テーブル追加など）
- `sqlite_reader.py`: SQLite からのデータ抽出
- `etl.py`: 外国語翻訳データの抽出・投入パイプライン
- `upsert.py`: バッチデータベース投入

## 環境変数

- `MTG_DB_PATH`: SQLite DB パス（デフォルト: `data/AllPrintings.sqlite`）
- `PYTHONUNBUFFERED`: ログ出力を即座に表示（Docker で設定済み）

## パフォーマンス

- **SQLite 活用**: JSON メモリ全ロード廃止 → 低メモリ使用
- **インデックス**: カード名・言語・UUID で自動作成（検索高速化）
- **マイグレーション**: バージョン管理されたスキーマ更新（重複実行防止）
- **キャッシング**: 接続キャッシング、接続プール対応可能
- **多言語対応**: 独立した `foreign_data` テーブルで検索性能を維持

## データベーススキーマ

### `foreign_data` テーブル

外国語版カード情報を保存（v1.1.0+）:

```sql
CREATE TABLE foreign_data (
    id INTEGER PRIMARY KEY,
    card_uuid TEXT NOT NULL,        -- 元のカードのUUID
    language TEXT NOT NULL,          -- 言語名 (Japanese, French, German など)
    name TEXT,                        -- 外国語でのカード名
    face_name TEXT,                   -- 表面のカード名（両面カード用）
    text TEXT,                        -- 外国語版ルールテキスト
    flavor_text TEXT,                 -- 外国語版フレーバーテキスト
    type TEXT,                        -- 外国語版カードタイプ
    UNIQUE(card_uuid, language),      -- カード＆言語の組み合わせは一意
    FOREIGN KEY(card_uuid) REFERENCES cards(uuid)
);

-- インデックス
CREATE INDEX idx_foreign_data_card_uuid ON foreign_data(card_uuid);
CREATE INDEX idx_foreign_data_language ON foreign_data(language);
CREATE INDEX idx_foreign_data_name ON foreign_data(name COLLATE NOCASE);
```

### マイグレーション管理

`sqlite_migrations` テーブルで適用済みマイグレーションを追跡:

```sql
CREATE TABLE sqlite_migrations (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 将来の拡張

- **SDK 生成**: OpenAPI → TypeScript / Python SDK（`tools/generate-sdks.sh`）
- **CI/CD**: GitHub Actions で OpenAPI 生成・SDK 配布
- **ECS デプロイ**: ETL ランナーを定期 Task、API を ECS Service で運用
- **DB**: SQLite → PostgreSQL への切り替え対応
- **翻訳検索の最適化**: フルテキスト検索（FTS）対応
- **キャッシング**: Redis による検索結果キャッシング
- **カード画像**: Scryfall API との連携

## 変更履歴

### v1.1.0 (2026-01-16)

**新機能**:

- ✨ 多言語検索サポート：日本語・フランス語など多言語でカード検索可能
- ✨ ETL パイプライン：外国語翻訳データを自動抽出・投入
- ✨ マイグレーション管理：`migrate.py` でスキーマ更新を版管理
- ✨ 統計情報 API：`/stats` エンドポイントでカード数・セット数を取得
- ✨ 翻訳情報 API：`/cards/{uuid}/translations` で全言語版を取得

**改善**:

- 📈 `foreign_data` テーブルに複数インデックスを追加（検索高速化）
- 📈 ETL ランナーに段階的実行ログ出力（4 ステップ表示）
- 📈 クライアント SDK に言語別検索関数を追加

### v1.0.0 (初版)

基本的なカード検索機能、複合フィルター検索

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

### 多言語検索で結果が返らない

`foreign_data` テーブルが作成・投入されているか確認:

```bash
# テーブルの存在確認
docker compose exec api sqlite3 /app/data/AllPrintings.sqlite ".tables"

# データ投入確認
docker compose exec api sqlite3 /app/data/AllPrintings.sqlite "SELECT COUNT(*) FROM foreign_data"

# マイグレーション状態確認
docker compose exec api sqlite3 /app/data/AllPrintings.sqlite "SELECT * FROM sqlite_migrations"
```

ETL ランナーが正常に完了しているか再度ログを確認:

```bash
docker compose logs etl-runner | grep -E "foreign_data|Upserted|migration"
```

## ライセンス

MTGJSON データは公式ライセンスに従う。本プロジェクトは MIT ライセンス。
