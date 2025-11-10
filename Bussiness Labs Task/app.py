from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = '1234'  
app.config['MYSQL_DB'] = 'bls'  

mysql = MySQL(app)

# Home route - redirect to login
@app.route('/')
def index():
    return redirect(url_for('login'))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        Name = request.form['Name']
        Email = request.form['Email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        # Check if email already exists
        cur.execute("SELECT * FROM Students WHERE Email = %s", (Email,))
        user_exists = cur.fetchone()

        if user_exists:
            flash("Email already taken. Try a different one.", "error")
            return redirect(url_for('register'))

        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Insert new user
        cur.execute("INSERT INTO Students (Name, Email, Password) VALUES (%s, %s, %s)", 
                    (Name, Email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash(f"User {Email} registered successfully! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        Email = request.form['Email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Students WHERE Email = %s", (Email,))
        user = cur.fetchone()

        if not user:
            flash("Email not found! Please try again or register.", "error")
            return redirect(url_for('login'))

        # Check password
        if not check_password_hash(user[3], password):  # user[3] is the password column
            flash("Incorrect password! Please try again.", "error")
            return redirect(url_for('login'))

        # Store user info in session
        session['user_id'] = user[0]
        session['user_name'] = user[1]
        session['user_email'] = user[2]
        
        # Check if admin (for simplicity, let's assume admin is the first user)
        if user[0] == 1:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    return render_template('login.html')

# Student dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Students WHERE id = %s", (session['user_id'],))
    student = cur.fetchone()
    cur.close()
    
    return render_template('student_dashboard.html', student=student)

# Admin dashboard
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get filter parameters
    class_filter = request.args.get('class_filter', '')
    name_filter = request.args.get('name_filter', '')
    
    cur = mysql.connection.cursor()
    
    # Build query with filters
    query = "SELECT * FROM Students WHERE 1=1"
    params = []
    
    if class_filter:
        query += " AND Class = %s"
        params.append(class_filter)
    
    if name_filter:
        query += " AND Name LIKE %s"
        params.append(f"%{name_filter}%")
    
    cur.execute(query, params)
    students = cur.fetchall()
    cur.close()
    
    # Get unique classes for filter dropdown
    cur = mysql.connection.cursor()
    cur.execute("SELECT DISTINCT Class FROM Students WHERE Class IS NOT NULL AND Class != ''")
    classes = [row[0] for row in cur.fetchall()]
    cur.close()
    
    return render_template('admin_dashboard.html', students=students, classes=classes, 
                          class_filter=class_filter, name_filter=name_filter)

# Add new student
@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    Name = request.form['Name']
    Email = request.form['Email']
    Password = request.form['Password']
    Class = request.form['Class']
    Subject = request.form['Subject']
    Marks = request.form['Marks']
    
    # Hash password
    hashed_password = generate_password_hash(Password, method='pbkdf2:sha256')
    
    cur = mysql.connection.cursor()
    
    # Check if email already exists
    cur.execute("SELECT * FROM Students WHERE Email = %s", (Email,))
    if cur.fetchone():
        flash("Email already exists!", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Insert new student
    cur.execute("INSERT INTO Students (Name, Email, Password, Class, Subject, Marks) VALUES (%s, %s, %s, %s, %s, %s)",
                (Name, Email, hashed_password, Class, Subject, Marks))
    mysql.connection.commit()
    cur.close()
    
    flash("Student added successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# Edit student
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        Name = request.form['Name']
        Email = request.form['Email']
        Class = request.form['Class']
        Subject = request.form['Subject']
        Marks = request.form['Marks']
        
        # Check if email already exists for another student
        cur.execute("SELECT * FROM Students WHERE Email = %s AND id != %s", (Email, student_id))
        if cur.fetchone():
            flash("Email already exists for another student!", "error")
            return redirect(url_for('edit_student', student_id=student_id))
        
        # Update student
        cur.execute("UPDATE Students SET Name = %s, Email = %s, Class = %s, Subject = %s, Marks = %s WHERE id = %s",
                    (Name, Email, Class, Subject, Marks, student_id))
        mysql.connection.commit()
        cur.close()
        
        flash("Student updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))
    
    # GET request - load student data
    cur.execute("SELECT * FROM Students WHERE id = %s", (student_id,))
    student = cur.fetchone()
    cur.close()
    
    if not student:
        flash("Student not found!", "error")
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_student.html', student=student)

# Delete student
@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Students WHERE id = %s", (student_id,))
    mysql.connection.commit()
    cur.close()
    
    flash("Student deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)