from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from functools import wraps
import MySQLdb.cursors
import random
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necesario para usar 'flash'

# Configuración de MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'M4uNG:1285'
app.config['MYSQL_DB'] = 'crud_flask_1'

mysql = MySQL(app)

# Decorador para verificar si el usuario está logueado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            flash('Por favor, inicia sesión primero.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta principal: Mostrar tareas y tareas de amigos
@app.route('/')
@login_required
def index():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Obtener el código de amigo del usuario actual
    cursor.execute("SELECT friend_code FROM users WHERE id = %s", (session['id'],))
    user = cursor.fetchone()
    user_friend_code = user['friend_code']
    
    # Tareas del usuario
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (session['id'],))
    tasks = cursor.fetchall()
    
    # Tareas de los amigos con información del usuario
    cursor.execute("""
        SELECT tasks.*, users.username AS owner_username FROM tasks
        JOIN friends ON friends.friend_id = tasks.user_id
        JOIN users ON users.id = tasks.user_id
        WHERE friends.user_id = %s
    """, (session['id'],))
    friend_tasks = cursor.fetchall()

    return render_template('index.html', tasks=tasks, friend_tasks=friend_tasks, user_friend_code=user_friend_code)



# Ruta para agregar amigos mediante código
@app.route('/add_friend', methods=['POST'])
@login_required
def add_friend():
    friend_code = request.form['friend_code']
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Asegúrate de usar DictCursor
    cursor.execute("SELECT id FROM users WHERE friend_code = %s", (friend_code,))
    friend = cursor.fetchone()
    
    if friend:
        friend_id = friend['id']  # Accede a la clave del diccionario, no a la tupla

        # Verificamos si ya son amigos
        cursor.execute("SELECT * FROM friends WHERE user_id = %s AND friend_id = %s", (session['id'], friend_id))
        existing_friendship = cursor.fetchone()
        
        if not existing_friendship:
            cursor.execute("INSERT INTO friends (user_id, friend_id) VALUES (%s, %s)", (session['id'], friend_id))
            cursor.execute("INSERT INTO friends (user_id, friend_id) VALUES (%s, %s)", (friend_id, session['id']))  # Amistad bidireccional
            mysql.connection.commit()
            flash('¡Ahora son amigos!')
        else:
            flash('Ya eres amigo de este usuario.')
    else:
        flash('El código de amigo es inválido.')
    
    return redirect(url_for('index'))


# Función para generar un código de amigo único
def generate_friend_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

# Ruta para registro de usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        friend_code = generate_friend_code()

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        account = cursor.fetchone()

        if account:
            flash('El correo ya está registrado.')
        else:
            cursor.execute("INSERT INTO users (username, email, password, friend_code) VALUES (%s, %s, %s, %s)", (username, email, password, friend_code))
            mysql.connection.commit()
            flash('Te has registrado exitosamente. ¡Inicia sesión!')
            return redirect(url_for('login'))
    return render_template('register.html')

# Ruta para inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        account = cursor.fetchone()
        
        if account and check_password_hash(account['password'], password):
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            flash('Has iniciado sesión exitosamente.')
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.')
    return render_template('login.html')

# Ruta para añadir tareas
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO tasks (title, description, user_id) VALUES (%s, %s, %s)", (title, description, session['id']))
        mysql.connection.commit()
        flash('Tarea añadida exitosamente')
        return redirect(url_for('index'))
    return render_template('add_task.html')

# Ruta para editar tareas
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        cursor.execute("UPDATE tasks SET title=%s, description=%s WHERE id=%s", (title, description, id))
        mysql.connection.commit()
        flash('Tarea actualizada exitosamente')
        return redirect(url_for('index'))
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
    task = cursor.fetchone()
    return render_template('edit_task.html', task=task)

# Ruta para eliminar tareas
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_task(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    mysql.connection.commit()
    flash('Tarea eliminada exitosamente')
    return redirect(url_for('index'))

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    flash('Has cerrado sesión.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
