#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 1日前の実績実行
# python main.py --past_days=1 --forecast_days=0
# 当日の予報実行
# python main.py --past_days=0 --forecast_days=1

# cron
# 0 5 * * * docker exec  location_me_backend sh -c "cd /backend/app/jobs/weather && python main.py --past_days=1 --forecast_days=0" >> /var/location-me/tmp/weather.log  # noqa: E501
# 0 5 * * * docker exec  location_me_backend sh -c "cd /backend/app/jobs/weather && python main.py --past_days=0 --forecast_days=1" >> /var/location-me/tmp/weather.log  # noqa: E501

import argparse
import time

import httpx
import psycopg2
import yaml


def load_weather(past_days, forecast_days):
    with open("./config.yml", "r", encoding="utf-8") as yml:
        config = yaml.safe_load(yml)
        print(config["weather"]["locations"])

        locations = config["weather"]["locations"]
        for location in locations:
            print(location["name"], location["latitude"], location["longitude"])
            apiUrl = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"past_days={past_days}&forecast_days={forecast_days}&"
                f"latitude={location['latitude']}&longitude={location['longitude']}&"
                f"timezone=Asia%2FTokyo&"
                f"daily=weather_code,temperature_2m_max,temperature_2m_min&"
                f"hourly=weather_code,temperature_2m,precipitation_probability,relative_humidity_2m"
            )
            print(apiUrl)
            with httpx.Client() as client:
                response = client.get(apiUrl)
                print(response.json())
                weather = response.json()
                print(config["weather"]["database_url"])

                sql = (
                    "insert into weather_dailies"
                    "(name,code,src_latitude,src_longitude,daily_time,dst_latitude,dst_longitude,weather_code,temperature_2m_min,temperature_2m_max)"
                    "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id"
                )
                print(sql)
                with get_connection(config["weather"]["database_url"]) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            sql,
                            (
                                location["name"],
                                location["code"],
                                location["latitude"],
                                location["longitude"],
                                weather["daily"]["time"][0],
                                weather["latitude"],
                                weather["longitude"],
                                weather["daily"]["weather_code"][0],
                                weather["daily"]["temperature_2m_min"][0],
                                weather["daily"]["temperature_2m_max"][0],
                            ),
                        )

                        inserted_id = cursor.fetchone()[0]
                        for index, time in enumerate(weather["hourly"]["time"]):  # noqa: F402
                            sql = (
                                "insert into weather_hourlies"
                                "(weather_daily_id,code,hourly_time,weather_code,temperature_2m,precipitation_probability,relative_humidity_2m)"
                                "values(%s,%s,%s,%s,%s,%s,%s)"
                            )
                            cursor.execute(
                                sql,
                                (
                                    inserted_id,
                                    location["code"],
                                    time,
                                    weather["hourly"]["weather_code"][index],
                                    weather["hourly"]["temperature_2m"][index],
                                    weather["hourly"]["precipitation_probability"][index],
                                    weather["hourly"]["relative_humidity_2m"][index],
                                ),
                            )


def get_connection(database_uri):
    return psycopg2.connect(database_uri)


if __name__ == "__main__":
    start_time = time.time()

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("--past_days", type=int, help="Number of past days")
    parser.add_argument("--forecast_days", type=int, help="Number of forecast days")
    args = parser.parse_args()

    load_weather(args.past_days, args.forecast_days)

    print("Execution time: %s seconds" % (time.time() - start_time))
