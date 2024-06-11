# location-me-backend

### Windows で node のプロセス終了させる方法

```
//エラーでalreadyになっているポート番号を最後に入れる
netstat -aon | findstr 0.0:3000

//下記は帰ってくる値の例　最後の数値をコピー
//TCP         0.0.0.0:3000           0.0.0.0:0              LISTENING       15856

```

```
//先ほど表示された数値を入れて実行
taskkill /pid 15856 /F
```
