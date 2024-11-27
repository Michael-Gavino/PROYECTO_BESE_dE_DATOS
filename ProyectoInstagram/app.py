from flask import Flask, render_template, request, redirect, url_for, session, flash
from mysql_connection import connect_mysql
from neo4j_connection import connect_neo4j
from sync_operations import sync_mysql_to_neo4j
app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'  # Necesario para usar sesiones


# Función para registrar usuario en MySQL
def register_user_mysql(first_name, last_name, email, phone):
    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return False

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO InformacionPersona (nombre, apellido, correo, telefono)
                VALUES (%s, %s, %s, %s)
            """, (first_name, last_name, email, phone))
        mysql_conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar usuario en MySQL: {e}")
        flash('Error al registrar usuario en MySQL.')
        return False
    finally:
        mysql_conn.close()


# Función para registrar usuario en Neo4j
def register_user_neo4j(first_name, last_name, email, phone):
    neo4j_driver = connect_neo4j()
    if not neo4j_driver:
        flash('Error al conectar con Neo4j.')
        return False

    try:
        with neo4j_driver.session() as session:
            session.run("""
                MERGE (u:Usuario {correo: $correo})
                SET u.nombre = $nombre, u.apellido = $apellido, u.telefono = $telefono
            """, nombre=first_name, apellido=last_name, correo=email, telefono=phone)
        return True
    except Exception as e:
        print(f"Error al registrar usuario en Neo4j: {e}")
        flash('Error al registrar usuario en Neo4j.')
        return False
    finally:
        neo4j_driver.close()

@app.route('/sync_mysql_to_neo4j', methods=['GET'])
def sync_mysql_to_neo4j():
    sync_mysql_to_neo4j()  # Llama la función de sincronización
    flash("Sincronización completada entre MySQL y Neo4j.")
    return redirect(url_for('profile'))  # Redirige a la página del perfil


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Obtener datos del formulario
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']

        # Verificar si el usuario ya existe en MySQL
        mysql_conn = connect_mysql()
        if not mysql_conn:
            flash('Error al conectar con MySQL.')
            return redirect(url_for('register'))

        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM InformacionPersona WHERE correo = %s", (email,))
            existing_user = cursor.fetchone()

        if existing_user:
            flash('El correo ya está registrado en MySQL. Por favor, utiliza otro.')
            return redirect(url_for('register'))

        # Registrar en MySQL y Neo4j
        if register_user_mysql(first_name, last_name, email, phone) and register_user_neo4j(first_name, last_name, email, phone):
            flash('Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect(url_for('index'))

        flash('Error al registrar el usuario.')
        return redirect(url_for('register'))

    return render_template('registro.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    phone = request.form['phone']

    # Verificar usuario en MySQL
    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('index'))

    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT * FROM InformacionPersona WHERE correo = %s AND telefono = %s", (email, phone))
        user = cursor.fetchone()

    if user:
        session['email'] = email
        flash('Inicio de sesión exitoso.')
        return redirect(url_for('feed'))

    flash('Correo o teléfono incorrecto.')
    return redirect(url_for('index'))


@app.route('/feed')
def feed():
    if 'email' not in session:
        flash('Por favor, inicia sesión para acceder al feed.')
        return redirect(url_for('index'))

    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('index'))

    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT * FROM InformacionPersona WHERE correo = %s", (session['email'],))
        user = cursor.fetchone()

    return render_template('feed.html', user=user)

@app.route('/search', methods=['POST'])
def search():
    if 'email' not in session:
        flash('Por favor, inicia sesión para buscar.')
        return redirect(url_for('index'))

    search_term = request.form.get('search_term', '').strip()  # Usa .get para evitar KeyError
    print(f"Término de búsqueda recibido: {search_term}")  # Log para confirmar el término

    mysql_conn = connect_mysql()
    results = []

    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('feed'))

    try:
        with mysql_conn.cursor() as cursor:
            query = """
                SELECT idInformacionPersona, nombre, apellido 
                FROM InformacionPersona 
                WHERE nombre LIKE %s OR apellido LIKE %s
            """
            cursor.execute(query, (f"%{search_term}%", f"%{search_term}%"))
            results = cursor.fetchall()
            print(f"Resultados obtenidos: {results}")  # Log para depuración
    except Exception as e:
        print(f"Error al buscar: {e}")
        flash('Error al realizar la búsqueda.')
    finally:
        mysql_conn.close()

    return render_template('search_results.html', results=results)

@app.route('/view_profile/<int:user_id>')
def view_profile(user_id):
    if 'email' not in session:
        flash('Por favor, inicia sesión para ver perfiles.')
        return redirect(url_for('index'))

    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('feed'))

    try:
        with mysql_conn.cursor() as cursor:
            # Obtener datos del perfil
            cursor.execute("SELECT * FROM InformacionPersona WHERE idInformacionPersona = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                flash('Usuario no encontrado.')
                return redirect(url_for('feed'))

            # Determinar si ya lo sigue
            cursor.execute("""
                SELECT * FROM Seguidores 
                WHERE id_seguidor = (SELECT idInformacionPersona FROM InformacionPersona WHERE correo = %s)
                AND id_seguido = %s
            """, (session['email'], user_id))
            is_following = cursor.fetchone() is not None

        return render_template('profile.html', user=user, is_own_profile=(user['correo'] == session['email']), is_following=is_following)
    except Exception as e:
        print(f"Error al cargar el perfil: {e}")
        flash('Error al cargar el perfil.')
        return redirect(url_for('feed'))
    finally:
        mysql_conn.close()



@app.route('/follow/<int:user_id>', methods=['POST'])
def follow_user(user_id):
    if 'email' not in session:
        flash('Por favor, inicia sesión para seguir a alguien.')
        return redirect(url_for('index'))

    mysql_conn = connect_mysql()
    neo4j_driver = connect_neo4j()  # Conexión a Neo4j
    if not mysql_conn or not neo4j_driver:
        flash('Error al conectar con MySQL o Neo4j.')
        return redirect(url_for('feed'))

    try:
        with mysql_conn.cursor() as cursor:
            # Obtener los datos del seguidor (la persona que está siguiendo)
            cursor.execute("SELECT idInformacionPersona, nombre FROM InformacionPersona WHERE correo = %s", (session['email'],))
            seguidor = cursor.fetchone()

            if not seguidor:
                flash('No se encontró tu información en la base de datos.')
                return redirect(url_for('feed'))

            # Obtener los datos del usuario al que se sigue
            cursor.execute("SELECT idInformacionPersona, nombre FROM InformacionPersona WHERE idInformacionPersona = %s", (user_id,))
            seguido = cursor.fetchone()

            if not seguido:
                flash('El usuario que intentas seguir no existe.')
                return redirect(url_for('feed'))

            # Verificar si ya existe una relación de "seguir"
            cursor.execute("""
                SELECT * FROM Seguidores 
                WHERE id_seguidor = %s AND id_seguido = %s
            """, (seguidor['idInformacionPersona'], user_id))
            relationship = cursor.fetchone()

            if relationship:
                # Si ya lo sigue, eliminar la relación (Dejar de seguir)
                cursor.execute("""
                    DELETE FROM Seguidores 
                    WHERE id_seguidor = %s AND id_seguido = %s
                """, (seguidor['idInformacionPersona'], user_id))
                mysql_conn.commit()

                # Eliminar la relación en Neo4j (Dejar de conocer)
                with neo4j_driver.session() as session_neo4j:
                    session_neo4j.run("""
                        MATCH (u:Usuario {id_mysql: $seguidor_id}), (v:Usuario {id_mysql: $seguidor_id2})
                        MATCH (u)-[r:CONOCE_A]->(v)
                        DELETE r
                    """, seguidor_id=seguidor['idInformacionPersona'], seguidor_id2=user_id)

                flash('Has dejado de seguir a esta persona.')
            else:
                # Si no lo sigue, añadir la relación (Seguir)
                cursor.execute("""
                    INSERT INTO Seguidores (id_seguidor, nombre_seguidor, id_seguido, nombre_seguido)
                    SELECT %s, %s, idInformacionPersona, nombre 
                    FROM InformacionPersona WHERE idInformacionPersona = %s
                """, (seguidor['idInformacionPersona'], seguidor['nombre'], user_id))
                mysql_conn.commit()

                # Añadir la relación en Neo4j (Conocer)
                with neo4j_driver.session() as session_neo4j:
                    session_neo4j.run("""
                        MATCH (u:Usuario {id_mysql: $seguidor_id}), (v:Usuario {id_mysql: $seguidor_id2})
                        MERGE (u)-[:CONOCE_A]->(v)
                    """, seguidor_id=seguidor['idInformacionPersona'], seguidor_id2=user_id)

                # Verificar si ambos se siguen mutuamente
                cursor.execute("""
                    SELECT * FROM Seguidores 
                    WHERE id_seguidor = %s AND id_seguido = %s
                """, (user_id, seguidor['idInformacionPersona']))
                reciprocal_relationship = cursor.fetchone()

                if reciprocal_relationship:
                    # Si ambos se siguen mutuamente, crear la relación ES_AMIGO_DE en Neo4j
                    with neo4j_driver.session() as session_neo4j:
                        session_neo4j.run("""
                            MATCH (u:Usuario {id_mysql: $seguidor_id}), (v:Usuario {id_mysql: $seguidor_id2})
                            MERGE (u)-[:ES_AMIGO_DE]->(v)
                            MERGE (v)-[:ES_AMIGO_DE]->(u)
                        """, seguidor_id=seguidor['idInformacionPersona'], seguidor_id2=user_id)

                    flash('Ahora ambos son amigos.')
                else:
                    flash('Ahora sigues a esta persona.')

            mysql_conn.commit()
            return redirect(url_for('view_profile', user_id=user_id))

    except Exception as e:
        print(f"Error al gestionar seguimiento: {e}")
        flash('Error al gestionar el seguimiento.')
        return redirect(url_for('feed'))
    finally:
        mysql_conn.close()
        neo4j_driver.close()



@app.route('/toggle_follow/<int:user_id>', methods=['POST'])
def toggle_follow(user_id):
    if 'email' not in session:
        flash('Por favor, inicia sesión para gestionar seguidores.')
        return redirect(url_for('index'))

    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('feed'))

    try:
        with mysql_conn.cursor() as cursor:
            # Obtener el seguidor (la persona que realiza el seguimiento)
            cursor.execute("SELECT idInformacionPersona, nombre FROM InformacionPersona WHERE correo = %s", (session['email'],))
            seguidor = cursor.fetchone()

            if not seguidor:
                flash('No se encontró tu información en la base de datos.')
                return redirect(url_for('feed'))

            # Verificar si ya sigue al usuario
            cursor.execute("""
                SELECT * FROM Seguidores 
                WHERE id_seguidor = %s AND id_seguido = %s
            """, (seguidor['idInformacionPersona'], user_id))
            relationship = cursor.fetchone()

            if relationship:
                # Si ya lo sigue, eliminar la relación
                cursor.execute("""
                    DELETE FROM Seguidores 
                    WHERE id_seguidor = %s AND id_seguido = %s
                """, (seguidor['idInformacionPersona'], user_id))
                mysql_conn.commit()
                flash('Has dejado de seguir a esta persona.')
            else:
                # Si no lo sigue, añadir la relación
                cursor.execute("""
                    INSERT INTO Seguidores (id_seguidor, nombre_seguidor, id_seguido, nombre_seguido)
                    SELECT %s, %s, idInformacionPersona, nombre 
                    FROM InformacionPersona WHERE idInformacionPersona = %s
                """, (seguidor['idInformacionPersona'], seguidor['nombre'], user_id))
                mysql_conn.commit()
                flash('Ahora sigues a esta persona.')

        return redirect(url_for('view_profile', user_id=user_id))

    except Exception as e:
        print(f"Error al gestionar seguimiento: {e}")
        flash('Error al gestionar el seguimiento.')
        return redirect(url_for('feed'))
    finally:
        mysql_conn.close()



@app.route('/profile')
def profile():
    if 'email' not in session:
        flash('Por favor, inicia sesión para acceder al perfil.')
        return redirect(url_for('index'))

    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('index'))

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM InformacionPersona WHERE correo = %s", (session['email'],))
            user = cursor.fetchone()

        if not user:
            flash("No se encontró información del usuario.")
            return redirect(url_for('index'))

        return render_template('profile.html', user=user, is_own_profile=True)
    except Exception as e:
        print(f"Error al cargar el perfil: {e}")
        flash('Error al cargar el perfil.')
        return redirect(url_for('index'))
    finally:
        mysql_conn.close()


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'email' not in session:
        flash('Por favor, inicia sesión para editar tu perfil.')
        return redirect(url_for('index'))

    email = session['email']
    if request.method == 'POST':
        # Obtener datos del formulario enviados por el usuario
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        city = request.form.get('city')
        bio = request.form.get('bio')
        birthdate = request.form.get('birthdate')

        mysql_conn = connect_mysql()
        if not mysql_conn:
            flash('Error al conectar con MySQL.')
            return redirect(url_for('edit_profile'))

        try:
            with mysql_conn.cursor() as cursor:
                # Actualizar los campos editados en la base de datos
                cursor.execute("""
                    UPDATE InformacionPersona
                    SET nombre = %s, apellido = %s, ciudad = %s, bio = %s, fecha_nacimiento = %s
                    WHERE correo = %s
                """, (first_name, last_name, city, bio, birthdate, email))
            mysql_conn.commit()
            flash('Tu perfil ha sido actualizado exitosamente.')
        except Exception as e:
            print(f"Error al actualizar perfil en MySQL: {e}")
            flash('Error al actualizar el perfil.')
        finally:
            mysql_conn.close()

        return redirect(url_for('profile'))

    # Recuperar la información actual del usuario para mostrarla en el formulario
    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('index'))

    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT * FROM InformacionPersona WHERE correo = %s", (email,))
        user = cursor.fetchone()

    return render_template('edit_profile.html', user=user)



@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'email' not in session:  # Verifica que la sesión esté activa
        flash('Por favor, inicia sesión para editar tu perfil.')
        return redirect(url_for('index'))  # Si no hay sesión activa, redirige a inicio de sesión

    # Captura los datos del formulario
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    correo = request.form['correo']
    telefono = request.form['telefono']
    preferencias = request.form.get('preferencias')
    sexo = request.form.get('sexo')
    carrera = request.form.get('carrera')  # Captura carrera
    red_social = request.form.get('red_social')  # Captura red_social

    mysql_conn = connect_mysql()
    if not mysql_conn:
        flash('Error al conectar con MySQL.')
        return redirect(url_for('profile'))

    try:
        with mysql_conn.cursor() as cursor:
            update_query = """
                UPDATE InformacionPersona
                SET nombre = %s, apellido = %s, correo = %s, telefono = %s, preferencias = %s, sexo = %s, carrera = %s, red_social = %s
                WHERE correo = %s
            """
            cursor.execute(update_query, (nombre, apellido, correo, telefono, preferencias, sexo, carrera, red_social, session['email']))
            mysql_conn.commit()

        flash('Perfil actualizado con éxito en MySQL.')

        # Ahora actualizamos en Neo4j
        neo4j_driver = connect_neo4j()
        if not neo4j_driver:
            flash('Error al conectar con Neo4j.')
            return redirect(url_for('profile'))

        try:
            with neo4j_driver.session() as session_neo4j:
                # Verificar si el correo ya existe en Neo4j
                result = session_neo4j.run("""
                    MATCH (u:Usuario {correo: $correo})
                    RETURN u
                """, correo=correo)

                existing_user = result.single()

                if existing_user:
                    # Si existe, actualizamos sus datos
                    session_neo4j.run("""
                        MATCH (u:Usuario {correo: $correo})
                        SET u.nombre = $nombre, u.apellido = $apellido, u.telefono = $telefono, u.preferencias = $preferencias,
                            u.sexo = $sexo, u.carrera = $carrera, u.red_social = $red_social
                    """, correo=correo, nombre=nombre, apellido=apellido, telefono=telefono, preferencias=preferencias,
                    sexo=sexo, carrera=carrera, red_social=red_social)
                    print(f"Usuario con correo {correo} actualizado en Neo4j.")
                else:
                    # Si no existe, creamos el nodo
                    session_neo4j.run("""
                        CREATE (u:Usuario {correo: $correo, nombre: $nombre, apellido: $apellido, telefono: $telefono, 
                                            preferencias: $preferencias, sexo: $sexo, carrera: $carrera, red_social: $red_social})
                    """, correo=correo, nombre=nombre, apellido=apellido, telefono=telefono, preferencias=preferencias,
                    sexo=sexo, carrera=carrera, red_social=red_social)
                    print(f"Usuario con correo {correo} insertado en Neo4j.")

            flash('Perfil actualizado con éxito en Neo4j.')
        except Exception as e:
            print(f"Error al actualizar el perfil en Neo4j: {e}")
            flash('Error al actualizar el perfil en Neo4j.')

        return redirect(url_for('profile'))  # Redirige a la vista del perfil actualizado

    except Exception as e:
        print(f"Error al actualizar el perfil en MySQL: {e}")
        flash('Error al actualizar el perfil en MySQL.')
        return redirect(url_for('profile'))

    finally:
        mysql_conn.close()



@app.route('/logout')
def logout():
    session.pop('email', None)
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
