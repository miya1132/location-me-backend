import os


class BaseConfig:
    DEBUG = False
    VAPID_PUBLIC_KEY = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE55z_vWUdMpuzpd-zgxGUlOUl1pdCIfUP6So63YKBNs6ubx5YGTXfV37Yev6agslP6Mf0Qbxl8eVBo91s_tVvbA=="  # noqa: E501
    VAPID_PRIVATE_KEY = "TUlHSEFnRUFNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQkcwd2F3SUJBUVFnTlZOVGJocDhrV3J4a1VDbQ0KWGFQQitvdHZnbDZYNkxJbllxYm1Uemdtcnc2aFJBTkNBQVRublArOVpSMHltN09sMzdPREVaU1U1U1hXbDBJaA0KOVEvcEtqcmRnb0UyenE1dkhsZ1pOZDlYZnRoNi9wcUN5VS9veC9SQnZHWHg1VUdqM1d6KzFXOXM="  # noqa: E501
    VAPID_EMAIL = "mailto:miya1132@gmail.com"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    DATABASE_URI = "postgresql://postgres:Humanway=1974@location_me_db:5432/location_me_db"


class ProductionConfig(BaseConfig):
    DATABASE_URI = "postgresql://postgres:Humanway=1974@127.0.0.1:5432/location_me_db"


# 環境変数 'PYTHON_APP_MODE' から環境を判断する
# 'PYTHON_APP_MODE' が設定されていない場合は、本番環境をデフォルトとする
if os.environ.get("PYTHON_APP_MODE") == "dev":
    Config = DevelopmentConfig
else:
    Config = ProductionConfig
