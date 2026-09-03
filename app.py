from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import config

app = Flask(__name__)
app.secret_key = "student_erp_secret_key"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")

        if not student_id or not password:
            return render_template(
                "login.html",
                error="Please enter Student ID and Password."
            )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM students
            WHERE student_id = %s
              AND password = %s
            """,
            (student_id, password)
        )

        student = cursor.fetchone()

        cursor.close()
        conn.close()

        if student:
            session["student_id"] = student["student_id"]
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid Student ID or Password."
        )

    return render_template("login.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "student_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE student_id = %s
        """,
        (session["student_id"],)
    )

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if student is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        student=student
    )


# =========================================================
# STUDENT PROFILE
# =========================================================

@app.route("/profile")
def profile():

    if "student_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE student_id = %s
        """,
        (session["student_id"],)
    )

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if student is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "student_profile.html",
        student=student
    )


# =========================================================
# MODULE INFORMATION
# =========================================================

MODULES = {

    "fees": {
        "title": "Fees & Payments",
        "description": "View semester-wise fee and payment information.",
        "icon": "💳"
    },

    "subjects": {
        "title": "My Subjects",
        "description": "View the subjects assigned for each semester.",
        "icon": "📚"
    },

    "faculty": {
        "title": "Assigned Faculty",
        "description": "View faculty assigned to each subject.",
        "icon": "👨‍🏫"
    },

    "attendance": {
        "title": "Attendance",
        "description": "View subject-wise attendance for each semester.",
        "icon": "📊"
    },

    "marks": {
        "title": "Marks & Results",
        "description": "View semester-wise marks and results.",
        "icon": "🏆"
    },

    "assignments": {
        "title": "Assignments",
        "description": "View assignments and submission status.",
        "icon": "📝"
    },

    "examinations": {
        "title": "Examinations",
        "description": "View Mid and End-Term examination schedules.",
        "icon": "📅"
    },

    "timetable": {
        "title": "Timetable",
        "description": "View the timetable for each semester.",
        "icon": "🗓️"
    }
}


# =========================================================
# SELECT SEMESTER FOR A MODULE
# =========================================================

@app.route("/module/<module_name>")
def module_selector(module_name):

    if "student_id" not in session:
        return redirect(url_for("login"))

    if module_name not in MODULES:
        return redirect(url_for("dashboard"))

    module = MODULES[module_name]

    return render_template(
        "semester_select.html",
        module_name=module_name,
        module=module
    )


# =========================================================
# DISPLAY SELECTED SEMESTER DATA
# =========================================================

@app.route("/module/<module_name>/<int:semester>")
def module_view(module_name, semester):

    if "student_id" not in session:
        return redirect(url_for("login"))

    if module_name not in MODULES:
        return redirect(url_for("dashboard"))

    if semester not in [1, 2, 3, 4, 5]:
        return redirect(
            url_for(
                "module_selector",
                module_name=module_name
            )
        )

    student_id = session["student_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    data = []

    # -----------------------------------------------------
    # SUBJECTS
    # -----------------------------------------------------

    if module_name == "subjects":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   faculty
            FROM subjects
            WHERE student_id = %s
              AND semester = %s
            ORDER BY id
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    # -----------------------------------------------------
    # FACULTY
    # -----------------------------------------------------

    elif module_name == "faculty":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   faculty
            FROM subjects
            WHERE student_id = %s
              AND semester = %s
            ORDER BY id
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    # -----------------------------------------------------
    # ATTENDANCE
    # -----------------------------------------------------

    elif module_name == "attendance":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   attended,
                   total_classes
            FROM attendance
            WHERE student_id = %s
              AND semester = %s
            ORDER BY id
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()

        for row in data:

            if row["total_classes"] > 0:
                row["percentage"] = round(
                    (row["attended"] / row["total_classes"]) * 100,
                    2
                )
            else:
                row["percentage"] = 0


    # -----------------------------------------------------
    # MARKS
    # -----------------------------------------------------

    elif module_name == "marks":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   marks
            FROM marks
            WHERE student_id = %s
              AND semester = %s
            ORDER BY id
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    # -----------------------------------------------------
    # FEES
    # -----------------------------------------------------

    elif module_name == "fees":

        cursor.execute(
            """
            SELECT semester,
                   total_fee,
                   paid_fee,
                   pending_fee,
                   status
            FROM fees
            WHERE student_id = %s
              AND semester = %s
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    # -----------------------------------------------------
    # ASSIGNMENTS
    # -----------------------------------------------------

    elif module_name == "assignments":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   assignment_title,
                   due_date,
                   status
            FROM assignments
            WHERE student_id = %s
              AND semester = %s
            ORDER BY due_date, id
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    # -----------------------------------------------------
    # EXAMINATIONS
    # -----------------------------------------------------

    elif module_name == "examinations":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   exam_type,
                   exam_date,
                   exam_time,
                   room
            FROM examinations
            WHERE student_id = %s
              AND semester = %s
            ORDER BY exam_date, id
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    # -----------------------------------------------------
    # TIMETABLE
    # -----------------------------------------------------

    elif module_name == "timetable":

        cursor.execute(
            """
            SELECT subject_code,
                   subject_name,
                   day,
                   start_time,
                   end_time,
                   room
            FROM timetable
            WHERE student_id = %s
              AND semester = %s
            ORDER BY
                FIELD(day,
                    'Monday',
                    'Tuesday',
                    'Wednesday',
                    'Thursday',
                    'Friday',
                    'Saturday'
                ),
                start_time
            """,
            (student_id, semester)
        )

        data = cursor.fetchall()


    cursor.close()
    conn.close()

    return render_template(
        "module.html",
        module_name=module_name,
        module=MODULES[module_name],
        semester=semester,
        data=data
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
    app.run(debug=True)