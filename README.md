# 日経平均カレンダー v0.4 — 自動更新準備版

**現状**：アプリ側の配信データ読込と、GitHub Actionsによる自動取得・四本値検証・履歴保持は実装済み。**実データ取得は未稼働**です。日経公式を含む外部サイトの自動取得方法は、利用許諾の対象範囲が確認されるまで設定しないでください。

## 使い始める手順

1. GitHubで新しい公開リポジトリを作成し、このZIPの中身（隠しフォルダ `.github` を含む）をルートに置きます。
2. Settings → Pages → Build and deployment → Deploy from a branch → main / (root) を指定します。
3. 数分後に `https://<GitHubユーザー名>.github.io/<リポジトリ名>/` にアクセスします。URLは本人のGitHub設定で確定します。
4. 許可された**自動CSV取得方法**が確定した場合に限り、リポジトリ Settings → Secrets and variables → Actions に設定します。
   - Repository secret `AUTHORIZED_NIKKEI_CSV_URL`：自動アクセスを明示的に許可された HTTPS CSV URL（`date,open,high,low,close`列）
   - Repository variable `AUTHORIZED_NIKKEI_SOURCE_NAME`：出典名
5. Actions → Authorized Nikkei CSV refresh → Run workflow で動作テストします。取得・検証に成功すると `data/nikkei.json` が更新され、アプリから読み込めます。
6. 平日17:30 JSTに自動取得します（予定時刻から遅延・実行漏れがあり得ます）。配信元の確定時刻が遅い場合は workflow の cron を調整してください。

## 現在の制限と注意

- **許可が確認されていないサイトへの自動アクセスは行いません**。現在はCSV手動読込と架空デモが利用できます。
- ブラウザーで既にCSVを読み込んでいる場合、そのローカルCSVが優先されます。配信データに戻すには「デモに戻す」を押してください（表示が初期化されます）。
- 静的ホスティングで扱う `data/nikkei.json` は**公開情報**になります。契約が「個人閲覧のみ」の場合、公開リポジトリにデータを配置してはいけません。その場合はこの構成を使用せず、非公開の配信・認証方式を再検討してください。
- 無料の定期実行に100％の配信保証はありません。通信障害時は端末に保存された最新データを表示します。
- 自動取得URLを秘密値にしても、取得した価格データは公開リポジトリに保存されます。データ公開自体の許諾が必要です。
- 初期状態の `data/nikkei.json` には実データは含まれません。
