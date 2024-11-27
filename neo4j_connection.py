from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Cargar las variables de entorno
load_dotenv()

def connect_neo4j():
    """
    Establece la conexión con la base de datos Neo4j.
    """
    try:
        driver = GraphDatabase.driver(
            uri=os.getenv("NEO4J_URI"),  # URI del servidor Neo4j
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))  # Credenciales
        )
        print("Conexión exitosa a la base de datos Neo4j.")
        return driver
    except Exception as e:
        print(f"Error al conectar a Neo4j: {e}")
        return None

def create_neo4j_constraints():
    """
    Crea restricciones en la base de datos Neo4j para garantizar la unicidad de los nodos.
    """
    driver = connect_neo4j()
    if not driver:
        print("No se pudo establecer la conexión con la base de datos Neo4j.")
        return

    try:
        with driver.session() as session:
            # Crear restricción para el nodo Usuario
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (u:Usuario)
                REQUIRE u.id IS UNIQUE
            """)
            print("Restricción de unicidad para 'Usuario' creada exitosamente.")
    except Exception as e:
        print(f"Error al crear la restricción en Neo4j: {e}")
    finally:
        driver.close()