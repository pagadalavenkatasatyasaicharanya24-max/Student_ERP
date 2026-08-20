from flask import Flask, render_template, request, redirect, session
import mysql.connector
import config

app = Flask(__name__)

app.secret_key = "student_erp_secret_key"


# ---------------- DATABASE CONNECTION ----------------

def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


# ---------------- HOME / LOGIN PAGE ----------------

@app.route('/')
def home():
    return render_template('login.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    student_id = request.form.get('student_id')
    password = request.form.get('password')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE student_id = %s AND password = %s
        """,
        (student_id, password)
    )

    student = cursor.fetchone()

    cursor.close()
    connection.close()

    if student:
        session['student_id'] = student['student_id']
        return redirect('/dashboard')

    return "Invalid Student ID or Password"


# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():

    if 'student_id' not in session:
        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE student_id = %s
        """,
        (session['student_id'],)
    )

    student = cursor.fetchone()

    cursor.close()
    connection.close()

    if student:
        return render_template(
            'dashboard.html',
            student=student
        )

    return redirect('/')


# ---------------- SUBJECTS ----------------

@app.route('/subjects')
def subjects():

    if 'student_id' not in session:
        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM subjects
        WHERE student_id = %s
        """,
        (session['student_id'],)
    )

    subjects = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'subjects.html',
        subjects=subjects
    )


# ---------------- ASSIGNED FACULTY ----------------

@app.route('/assigned-faculty')
def assigned_faculty():

    if 'student_id' not in session:
        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            subject_code,
            subject_name,
            faculty
        FROM subjects
        WHERE student_id = %s
        """,
        (session['student_id'],)
    )

    faculty_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'assigned_faculty.html',
        faculty_data=faculty_data
    )


# ---------------- ATTENDANCE ----------------

@app.route('/attendance')
def attendance():

    if 'student_id' not in session:
        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            subjects.subject_name,
            subjects.subject_code,
            attendance.attendance_percentage
        FROM attendance
        INNER JOIN subjects
            ON attendance.subject_code = subjects.subject_code
        WHERE attendance.student_id = %s
        """,
        (session['student_id'],)
    )

    attendance_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'attendance.html',
        attendance_data=attendance_data
    )


# ---------------- MARKS & RESULTS ----------------

@app.route('/marks')
def marks():

    if 'student_id' not in session:
        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            subjects.subject_name,
            subjects.subject_code,
            marks.marks
        FROM marks
        INNER JOIN subjects
            ON marks.subject_code = subjects.subject_code
        WHERE marks.student_id = %s
        """,
        (session['student_id'],)
    )

    marks_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'marks.html',
        marks_data=marks_data
    )


# ---------------- TIMETABLE ----------------

@app.route('/timetable')
def timetable():

    if 'student_id' not in session:
        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            timetable.day,
            subjects.subject_name,
            subjects.subject_code,
            timetable.start_time,
            timetable.end_time
        FROM timetable
        INNER JOIN subjects
            ON timetable.subject_code = subjects.subject_code
        WHERE timetable.student_id = %s
        ORDER BY timetable.id
        """,
        (session['student_id'],)
    )

    timetable_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'timetable.html',
        timetable_data=timetable_data
    )


# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# ---------------- RUN APPLICATION ----------------

if __name__ == '__main__':
    app.run(debug=True)