
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from functools import wraps


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)
app.secret_key = "student_erp_secret_key"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="student_erp"
    )


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student_id" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    if "student_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        student_id = request.form.get("student_id")
        password = request.form.get("password")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                student_id,
                name,
                email,
                course,
                branch_code,
                year_number,
                current_semester,
                batch_year
            FROM students
            WHERE student_id = %s
              AND password = %s
            """,
            (student_id, password)
        )

        student = cursor.fetchone()

        cursor.close()
        connection.close()

        if student:
            session["student_id"] = student["student_id"]
            session["student_name"] = student["name"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid Student ID or Password"
        )

    return render_template("login.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            email,
            course,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    # -----------------------------------------------------
    # CURRENT SEMESTER ATTENDANCE
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            AVG(attendance_percentage) AS attendance
        FROM academic_attendance
        WHERE student_id = %s
          AND semester_number = %s
        """,
        (
            student_id,
            student["current_semester"]
        )
    )

    attendance_result = cursor.fetchone()

    attendance = attendance_result["attendance"]

    if attendance is not None:
        attendance = round(float(attendance), 2)
    else:
        attendance = 0

    # -----------------------------------------------------
    # PENDING FEES
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(pending_amount), 0) AS pending_fees
        FROM student_fees
        WHERE student_id = %s
        """,
        (student_id,)
    )

    fee_result = cursor.fetchone()

    pending_fees = float(fee_result["pending_fees"])

    # -----------------------------------------------------
    # CONSOLIDATED RESULT
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            cgpa,
            percentage,
            total_backlogs
        FROM consolidated_results
        WHERE student_id = %s
        """,
        (student_id,)
    )

    consolidated_result = cursor.fetchone()

    if consolidated_result is None:
        consolidated_result = {
            "cgpa": 0,
            "percentage": 0,
            "total_backlogs": 0
        }

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        student=student,
        attendance=attendance,
        pending_fees=pending_fees,
        consolidated_result=consolidated_result
    )


# =========================================================
# SUBJECTS
# =========================================================

@app.route("/subjects")
@login_required
def subjects():

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            email,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    # -----------------------------------------------------
    # CURRENT SEMESTER SUBJECTS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            subject_code,
            subject_name,
            credits,
            semester_number
        FROM academic_subjects
        WHERE branch_code = %s
          AND semester_number = %s
        ORDER BY subject_code
        """,
        (
            student["branch_code"],
            student["current_semester"]
        )
    )

    subject_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "subjects.html",
        student=student,
        subjects=subject_data
    )


# =========================================================
# ASSIGNED FACULTY
# =========================================================

@app.route("/assigned-faculty")
@login_required
def assigned_faculty():

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            email,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    # -----------------------------------------------------
    # SELECTED SEMESTER
    # -----------------------------------------------------

    selected_semester = request.args.get(
        "semester",
        default=student["current_semester"],
        type=int
    )

    if selected_semester < 1:
        selected_semester = 1

    if selected_semester > 8:
        selected_semester = 8

    # -----------------------------------------------------
    # FACULTY DATA
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            a.subject_code,
            a.subject_name,
            a.credits,
            a.semester_number,
            COALESCE(
                f.faculty_name,
                'Not Assigned'
            ) AS faculty,
            COALESCE(
                f.faculty_email,
                'Not Available'
            ) AS faculty_email
        FROM academic_subjects a

        LEFT JOIN faculty_assignments f
            ON f.subject_code = a.subject_code
           AND f.semester_number = a.semester_number

        WHERE a.branch_code = %s
          AND a.semester_number = %s

        ORDER BY a.subject_code
        """,
        (
            student["branch_code"],
            selected_semester
        )
    )

    faculty_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "assigned_faculty.html",
        student=student,
        faculty_data=faculty_data,
        selected_semester=selected_semester,
        current_semester=student["current_semester"]
    )


# =========================================================
# ATTENDANCE
# =========================================================

@app.route("/attendance")
@login_required
def attendance():

    student_id = session["student_id"]

    semester = request.args.get(
        "semester",
        type=int
    )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            email,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    current_semester = student["current_semester"]

    # -----------------------------------------------------
    # SELECTED SEMESTER
    # -----------------------------------------------------

    if semester is None:
        semester = current_semester

    if semester < 1:
        semester = 1

    if semester > current_semester:
        semester = current_semester

    # -----------------------------------------------------
    # ATTENDANCE DATA
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            aa.subject_code,
            aas.subject_name,
            aas.credits,
            aa.semester_number,
            aa.attendance_percentage
        FROM academic_attendance aa

        JOIN academic_subjects aas
            ON aa.subject_code = aas.subject_code
           AND aa.semester_number = aas.semester_number
           AND aas.branch_code = %s

        WHERE aa.student_id = %s
          AND aa.semester_number = %s

        ORDER BY aa.subject_code
        """,
        (
            student["branch_code"],
            student_id,
            semester
        )
    )

    attendance_data = cursor.fetchall()

    # -----------------------------------------------------
    # OVERALL ATTENDANCE
    # -----------------------------------------------------

    overall_attendance = 0

    if attendance_data:

        total_attendance = sum(
            float(row["attendance_percentage"])
            for row in attendance_data
        )

        overall_attendance = round(
            total_attendance / len(attendance_data),
            2
        )

    cursor.close()
    connection.close()

    return render_template(
        "attendance.html",
        student=student,
        attendance_data=attendance_data,
        selected_semester=semester,
        current_semester=current_semester,
        overall_attendance=overall_attendance
    )


# =========================================================
# MARKS & RESULTS
# =========================================================

@app.route("/marks")
@login_required
def marks():

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            email,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    current_semester = student["current_semester"]

    # -----------------------------------------------------
    # SELECTED SEMESTER
    # -----------------------------------------------------

    selected_semester = request.args.get(
        "semester",
        default=current_semester,
        type=int
    )

    if selected_semester < 1:
        selected_semester = 1

    if selected_semester > current_semester:
        selected_semester = current_semester

    # -----------------------------------------------------
    # MARKS DATA
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            am.subject_code,
            aas.subject_name,
            aas.credits,
            am.semester_number,
            am.marks,
            am.grade,
            am.grade_point
        FROM academic_marks am

        JOIN academic_subjects aas
            ON am.subject_code = aas.subject_code
           AND am.semester_number = aas.semester_number
           AND aas.branch_code = %s

        WHERE am.student_id = %s
          AND am.semester_number = %s

        ORDER BY am.subject_code
        """,
        (
            student["branch_code"],
            student_id,
            selected_semester
        )
    )

    marks_data = cursor.fetchall()

    # -----------------------------------------------------
    # SEMESTER RESULTS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            semester_number,
            sgpa,
            percentage,
            backlog_count
        FROM semester_results
        WHERE student_id = %s
        ORDER BY semester_number
        """,
        (student_id,)
    )

    semester_results = cursor.fetchall()

    # -----------------------------------------------------
    # CONSOLIDATED RESULT
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            cgpa,
            percentage,
            total_backlogs
        FROM consolidated_results
        WHERE student_id = %s
        """,
        (student_id,)
    )

    consolidated_result = cursor.fetchone()

    if consolidated_result is None:

        consolidated_result = {
            "cgpa": 0,
            "percentage": 0,
            "total_backlogs": 0
        }

    cursor.close()
    connection.close()

    return render_template(
        "marks.html",
        student=student,
        marks_data=marks_data,
        semester_results=semester_results,
        consolidated_result=consolidated_result,
        selected_semester=selected_semester,
        current_semester=current_semester
    )


# =========================================================
# FEES
# =========================================================

@app.route("/fees")
@login_required
def fees():

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            email,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    # -----------------------------------------------------
    # FEE DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            semester_number,
            academic_year,
            total_fee,
            amount_paid,
            pending_amount,
            payment_status
        FROM student_fees
        WHERE student_id = %s
        ORDER BY semester_number
        """,
        (student_id,)
    )

    fee_data = cursor.fetchall()

    # -----------------------------------------------------
    # FEE TOTALS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(total_fee), 0) AS total_fee,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(pending_amount), 0) AS total_pending
        FROM student_fees
        WHERE student_id = %s
        """,
        (student_id,)
    )

    fee_totals = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "fees.html",
        student=student,
        fee_data=fee_data,
        fee_totals=fee_totals
    )


# =========================================================
# NOTICES
# =========================================================

@app.route("/notices")
@login_required
def notices():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            notice_id,
            title,
            description,
            category,
            priority,
            notice_date
        FROM notices
        WHERE published = TRUE
        ORDER BY notice_date DESC
        """
    )

    notices_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "notices.html",
        notices=notices_data
    )


# =========================================================
# TIMETABLE
# =========================================================

@app.route("/timetable")
@login_required
def timetable():

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # GET STUDENT DETAILS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            name,
            branch_code,
            year_number,
            current_semester,
            batch_year
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        return redirect(url_for("logout"))

    # -----------------------------------------------------
    # TIMETABLE
    #
    # Current timetable table uses:
    # subject_code
    # day
    # start_time
    # end_time
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            subject_code,
            day,
            start_time,
            end_time
        FROM timetable
        WHERE student_id = %s
        ORDER BY
            FIELD(
                day,
                'Monday',
                'Tuesday',
                'Wednesday',
                'Thursday',
                'Friday',
                'Saturday',
                'Sunday'
            ),
            start_time
        """,
        (student_id,)
    )

    timetable_data = cursor.fetchall()

    # -----------------------------------------------------
    # CONVERT TIME VALUES TO STRINGS
    # -----------------------------------------------------

    for row in timetable_data:

        if row["start_time"] is not None:
            row["start_time"] = str(row["start_time"])

        if row["end_time"] is not None:
            row["end_time"] = str(row["end_time"])

    cursor.close()
    connection.close()

    return render_template(
        "timetable.html",
        student=student,
        timetable_data=timetable_data
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )