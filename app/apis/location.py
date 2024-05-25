from typing import Optional

from core import database
from fastapi import APIRouter, Query
from schemas import location

router = APIRouter()


@router.get(
    "",
    summary="場所",
    description="場所の取得",
)
async def get_locations(
    limit: int = Query(500, description="検索結果の取得上限"),
    location_start_at: Optional[str] = Query(None, description="検索k開始日時(yyyy-MM-dd hh24:mi:ss)"),
    location_end_at: Optional[str] = Query(None, description="検索終了日時(yyyy-MM-dd hh24:mi:ss"),
):
    q_location_start_at = "" if location_start_at is None else "AND location_at >= '" + location_start_at + "'"
    q_location_end_at = "" if location_end_at is None else "AND location_at <= '" + location_end_at + "'"

    sql = f"""
  SELECT jsonb_build_object(
      'type',     'FeatureCollection',
      'features', jsonb_agg(features.feature)
  )
  FROM (
    SELECT jsonb_build_object(
      'type',       'Feature',
      'id',         id,
      'geometry',   ST_AsGeoJSON(geom)::jsonb,
      'properties', to_jsonb(inputs) - 'geom'
    ) AS feature
    FROM (
      SELECT
        id,
        location_at,
        latitude,
        longitude,
        accuracy,
        altitude,
        speed,
        speed_accuracy,
        heading,
        ST_GeogFromText('SRID=4326;POINT(' || longitude || ' ' || latitude || ')')::geometry geom
      FROM locations
      WHERE 1 = 1 {q_location_start_at} {q_location_end_at}
      ORDER BY location_at desc
      LIMIT {limit}
      ) inputs) features;
  """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()[0][0]

    return results


@router.post(
    "",
    summary="場所",
    description="場所の登録",
)
async def post_location(data: location.Location):
    print("post location")
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            # レコードを挿入
            sql = """
              insert into locations(
                location_at, latitude, longitude, accuracy, altitude, speed, speed_accuracy, heading)
              values (%s, %s, %s , %s, %s, %s, %s, %s)
              """
            print(sql)
            cursor.execute(
                sql,
                (
                    data.location_at,
                    data.latitude,
                    data.longitude,
                    data.accuracy,
                    data.altitude,
                    data.speed,
                    data.speed_accuracy,
                    data.heading,
                ),
            )

    return {"status": 200}
