# %%
import json

import httpx

# https://developer.am.mufg.jp/fund_information_all_latest
# https://developer.am.mufg.jp//fund_information_latest/fund_cd/253266
apiUrl = "https://developer.am.mufg.jp/fund_information_all_latest"
with httpx.Client() as client:
    response = client.get(apiUrl)
    fund = response.json()

    fund_names = []
    datasets = fund["datasets"]
    for dataset in datasets:
        print(dataset["fund_name"])
        fund_names.append(dataset["fund_name"])

    file_path = "fund_names.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(fund_names, f, ensure_ascii=False, indent=4)
