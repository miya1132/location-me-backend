import os


class BaseConfig:
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    DATABASE_URI = (
        "postgresql://postgres:Humanway=1974@location_me_db:5432/location_me_db"
    )


class ProductionConfig(BaseConfig):
    DATABASE_URI = "postgresql://postgres:Humanway=1974@127.0.0.1:5432/location_me_db"


# 環境変数 'PYTHON_APP_MODE' から環境を判断する
# 'PYTHON_APP_MODE' が設定されていない場合は、本番環境をデフォルトとする
if os.environ.get("PYTHON_APP_MODE") == "dev":
    Config = DevelopmentConfig
else:
    Config = ProductionConfig
