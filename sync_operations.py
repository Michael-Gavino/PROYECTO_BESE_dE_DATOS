from mysql_connection import connect_mysql
from neo4j_connection import connect_neo4j
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

def sync_mysql_to_neo4j():
    """Sincroniza datos desde MySQL hacia Neo4j."""
    mysql_conn = connect_mysql()
    neo4j_driver = connect_neo4j()

    if not mysql_conn or not neo4j_driver:
        logging.error("Error al conectar a MySQL o Neo4j.")
        return

    try:
        # Obtener usuarios de MySQL
        with mysql_conn.cursor() as cursor:
            cursor.execute("""
                SELECT idInformacionPersona, nombre, apellido, telefono, correo, red_social
                FROM InformacionPersona
            """)
            usuarios = cursor.fetchall()

        # Insertar/Actualizar en Neo4j
        with neo4j_driver.session() as session:
            for usuario in usuarios:
                session.run("""
                    MERGE (u:Usuario {id: $id})
                    SET u.nombre = $nombre, u.apellido = $apellido, 
                        u.telefono = $telefono, u.correo = $correo, 
                        u.red_social = $red_social
                """, id=usuario['idInformacionPersona'], nombre=usuario['nombre'],
                       apellido=usuario['apellido'], telefono=usuario['telefono'],
                       correo=usuario['correo'], red_social=usuario['red_social'])
                logging.info(f"Usuario {usuario['idInformacionPersona']} sincronizado en Neo4j.")

    except Exception as e:
        logging.error(f"Error durante la sincronización: {e}")
    finally:
        mysql_conn.close()
        neo4j_driver.close()


def sync_neo4j_to_mysql():
    """Sincroniza datos desde Neo4j hacia MySQL."""
    mysql_conn = connect_mysql()
    neo4j_driver = connect_neo4j()

    if not mysql_conn or not neo4j_driver:
        logging.error("Error al conectar a MySQL o Neo4j.")
        return

    try:
        # Obtener usuarios de Neo4j
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (u:Usuario)
                RETURN u.id AS id, u.nombre AS nombre, u.apellido AS apellido, 
                       u.telefono AS telefono, u.correo AS correo, u.red_social AS red_social
            """)
            usuarios = result.data()

        # Insertar/Actualizar en MySQL
        with mysql_conn.cursor() as cursor:
            for usuario in usuarios:
                cursor.execute("""
                    INSERT INTO InformacionPersona (idInformacionPersona, nombre, apellido, telefono, correo, red_social)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        nombre = VALUES(nombre), apellido = VALUES(apellido), 
                        telefono = VALUES(telefono), correo = VALUES(correo), 
                        red_social = VALUES(red_social)
                """, (usuario['id'], usuario['nombre'], usuario['apellido'],
                      usuario['telefono'], usuario['correo'], usuario['red_social']))
                logging.info(f"Usuario {usuario['id']} sincronizado en MySQL.")

        mysql_conn.commit()

    except Exception as e:
        logging.error(f"Error durante la sincronización: {e}")
    finally:
        mysql_conn.close()
        neo4j_driver.close()





