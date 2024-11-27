import pymysql
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def connect_mysql():
    """
    Establece la conexión con la base de datos MySQL utilizando variables de entorno.
    """
    try:
        # Cargar las credenciales desde las variables de entorno
        connection = pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            port=int(os.getenv("MYSQL_PORT", 3306)),  # Puerto por defecto: 3306
            cursorclass=pymysql.cursors.DictCursor  # Configura el cursor para devolver diccionarios
        )
        print("Conexión exitosa a la base de datos MySQL.")
        return connection
    except pymysql.MySQLError as e:
        print(f"Error al conectar a MySQL: {e}")
        return None


def create_tables():
    """
    Crea las tablas necesarias en la base de datos MySQL si no existen.
    """
    connection = connect_mysql()
    if not connection:
        print("No se pudo establecer la conexión con la base de datos. Verifica las credenciales.")
        return

    try:
        with connection.cursor() as cursor:
            # Crear tabla de usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    telefono VARCHAR(15),
                    correo VARCHAR(100)
                )
            """)
            print("Tabla 'usuarios' creada exitosamente (o ya existe).")
        connection.commit()
    except pymysql.MySQLError as e:
        print(f"Error al crear la tabla: {e}")
    finally:
        connection.close()

# Ejemplo de uso
if __name__ == "__main__":
    create_tables()