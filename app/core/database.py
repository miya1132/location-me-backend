import psycopg2

from core.config import Config


def get_connection():
    return psycopg2.connect(Config.DATABASE_URI)


def get_device(device_id):
    sql = "SELECT * FROM devices WHERE device_id = %s"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (device_id,))
            device_tuple = cursor.fetchone()
            if device_tuple:
                column_names = [desc[0] for desc in cursor.description]
                device = dict(zip(column_names, device_tuple))
            else:
                device = None

    return device
