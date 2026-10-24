from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "cinerate-secret-key-change-this"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Vinutha@498",
        database="movie_rating_system"
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# MOVIES
# =========================================================

@app.route("/movies")
def movies():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    search = request.args.get("search", "").strip()
    language = request.args.get("language", "").strip()

    query = """
        SELECT
            m.movie_id,
            m.title,
            m.language,
            m.release_year,
            m.description,
            m.duration,

            ROUND(AVG(r.rating), 2) AS average_rating,

            COUNT(DISTINCT r.rating_id) AS rating_count,

            GROUP_CONCAT(
                DISTINCT g.genre_name
                ORDER BY g.genre_name
                SEPARATOR ', '
            ) AS genres

        FROM movies m

        LEFT JOIN ratings r
            ON m.movie_id = r.movie_id

        LEFT JOIN movie_genres mg
            ON m.movie_id = mg.movie_id

        LEFT JOIN genres g
            ON mg.genre_id = g.genre_id

        WHERE 1 = 1
    """

    parameters = []

    if search:
        query += """
            AND (
                m.title LIKE %s
                OR m.description LIKE %s
            )
        """

        search_value = "%" + search + "%"

        parameters.extend([
            search_value,
            search_value
        ])

    if language:
        query += """
            AND m.language = %s
        """

        parameters.append(language)

    query += """
        GROUP BY
            m.movie_id,
            m.title,
            m.language,
            m.release_year,
            m.description,
            m.duration

        ORDER BY m.title
    """

    cursor.execute(query, parameters)

    movies_list = cursor.fetchall()


    # Get available languages
    cursor.execute("""
        SELECT DISTINCT language
        FROM movies
        ORDER BY language
    """)

    languages = cursor.fetchall()


    cursor.close()
    connection.close()

    return render_template(
        "movies.html",
        movies=movies_list,
        languages=languages,
        search=search,
        selected_language=language
    )


# =========================================================
# MOVIE DETAILS
# =========================================================

@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            m.movie_id,
            m.title,
            m.language,
            m.release_year,
            m.description,
            m.duration,

            ROUND(AVG(r.rating), 2) AS average_rating,

            COUNT(DISTINCT r.rating_id) AS rating_count,

            GROUP_CONCAT(
                DISTINCT g.genre_name
                ORDER BY g.genre_name
                SEPARATOR ', '
            ) AS genres

        FROM movies m

        LEFT JOIN ratings r
            ON m.movie_id = r.movie_id

        LEFT JOIN movie_genres mg
            ON m.movie_id = mg.movie_id

        LEFT JOIN genres g
            ON mg.genre_id = g.genre_id

        WHERE m.movie_id = %s

        GROUP BY
            m.movie_id,
            m.title,
            m.language,
            m.release_year,
            m.description,
            m.duration
    """, (movie_id,))

    movie = cursor.fetchone()

    if movie is None:
        cursor.close()
        connection.close()
        return "Movie not found", 404


    # Reviews
    cursor.execute("""
        SELECT
            r.review_id,
            r.review_text,
            r.created_at,
            u.name

        FROM reviews r

        JOIN users u
            ON r.user_id = u.user_id

        WHERE r.movie_id = %s

        ORDER BY r.created_at DESC
    """, (movie_id,))

    reviews = cursor.fetchall()


    # Current user's rating
    user_rating = None

    if "user_id" in session:

        cursor.execute("""
            SELECT rating
            FROM ratings
            WHERE user_id = %s
              AND movie_id = %s
            ORDER BY rating_id DESC
            LIMIT 1
        """, (
            session["user_id"],
            movie_id
        ))

        rating_result = cursor.fetchone()

        if rating_result:
            user_rating = rating_result["rating"]


    cursor.close()
    connection.close()

    return render_template(
        "movie_details.html",
        movie=movie,
        reviews=reviews,
        user_rating=user_rating
    )


# =========================================================
# SUBMIT RATING
# =========================================================

@app.route("/movie/<int:movie_id>/rate", methods=["POST"])
def rate_movie(movie_id):

    if "user_id" not in session:
        flash("Please login to rate a movie.", "error")
        return redirect(url_for("login"))


    rating = request.form.get("rating", type=int)

    if rating is None or rating < 1 or rating > 5:
        flash("Rating must be between 1 and 5.", "error")
        return redirect(url_for("movie_details", movie_id=movie_id))


    connection = get_db_connection()
    cursor = connection.cursor()


    # Remove previous rating from this user for this movie
    cursor.execute("""
        DELETE FROM ratings
        WHERE user_id = %s
          AND movie_id = %s
    """, (
        session["user_id"],
        movie_id
    ))


    # Add new rating
    cursor.execute("""
        INSERT INTO ratings
        (user_id, movie_id, rating)
        VALUES (%s, %s, %s)
    """, (
        session["user_id"],
        movie_id,
        rating
    ))


    connection.commit()

    cursor.close()
    connection.close()


    flash("Your rating has been saved.", "success")

    return redirect(
        url_for("movie_details", movie_id=movie_id)
    )


# =========================================================
# SUBMIT REVIEW
# =========================================================

@app.route("/movie/<int:movie_id>/review", methods=["POST"])
def add_review(movie_id):

    if "user_id" not in session:
        flash("Please login to write a review.", "error")
        return redirect(url_for("login"))


    review_text = request.form.get(
        "review_text",
        ""
    ).strip()


    if not review_text:

        flash(
            "Review cannot be empty.",
            "error"
        )

        return redirect(
            url_for("movie_details", movie_id=movie_id)
        )


    connection = get_db_connection()
    cursor = connection.cursor()


    cursor.execute("""
        INSERT INTO reviews
        (user_id, movie_id, review_text)
        VALUES (%s, %s, %s)
    """, (
        session["user_id"],
        movie_id,
        review_text
    ))


    connection.commit()

    cursor.close()
    connection.close()


    flash(
        "Your review has been added.",
        "success"
    )

    return redirect(
        url_for("movie_details", movie_id=movie_id)
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        if not name or not email or not password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(url_for("register"))


        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(url_for("register"))


        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)


        cursor.execute("""
            SELECT user_id
            FROM users
            WHERE email = %s
        """, (email,))


        existing_user = cursor.fetchone()


        if existing_user:

            cursor.close()
            connection.close()

            flash(
                "This email is already registered.",
                "error"
            )

            return redirect(url_for("login"))


        hashed_password = generate_password_hash(password)


        cursor.execute("""
            INSERT INTO users
            (name, email, password)
            VALUES (%s, %s, %s)
        """, (
            name,
            email,
            hashed_password
        ))


        connection.commit()

        cursor.close()
        connection.close()


        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(url_for("login"))


    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)


        cursor.execute("""
            SELECT
                user_id,
                name,
                email,
                password
            FROM users
            WHERE email = %s
        """, (email,))


        user = cursor.fetchone()


        cursor.close()
        connection.close()


        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]


            flash(
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid email or password.",
            "error"
        )

        return redirect(url_for("login"))


    return render_template("login.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    cursor.execute("""
        SELECT COUNT(*) AS rating_count
        FROM ratings
        WHERE user_id = %s
    """, (session["user_id"],))

    rating_data = cursor.fetchone()


    cursor.execute("""
        SELECT COUNT(*) AS review_count
        FROM reviews
        WHERE user_id = %s
    """, (session["user_id"],))

    review_data = cursor.fetchone()


    cursor.execute("""
        SELECT
            m.title,
            r.rating
        FROM ratings r
        JOIN movies m
            ON r.movie_id = m.movie_id
        WHERE r.user_id = %s
        ORDER BY r.rating_id DESC
        LIMIT 5
    """, (session["user_id"],))

    recent_ratings = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "dashboard.html",
        rating_count=rating_data["rating_count"],
        review_count=review_data["review_count"],
        recent_ratings=recent_ratings
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("home"))


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)