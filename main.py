import sys, threading, time
from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import sha256_crypt #in case i ever feel like protecting user passwords
from turbo_flask import Turbo

app = Flask(__name__)
app.secret_key = "0439beans32kd+_+fej3fn4f"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(minutes=5)


db = SQLAlchemy(app)

turbo = Turbo(app)


class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True) #not using a string name for these bc it just uses the var name as a default
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    score = db.Column(db.Integer)

    def __init__(self, name, email, password, score):
        self.name = name
        self.email = email
        self.password = password
        self.score = score

def current_milli_time():
    return round(time.time() * 1000)


# turboFlask stuff, don't mess with this 
def update_load():
    with app.app_context():
        while True:
            time.sleep(1)
            turbo.push(turbo.update(render_template('minileaderboard.html'), 'data'))

with app.app_context():
    print("threadin'")
    threading.Thread(target=update_load).start()

@app.context_processor
def inject_load():
    thiplace = users.query.order_by(users.score.desc()).offset(2).first()
    secplace = users.query.order_by(users.score.desc()).offset(1).first()
    firstplace = users.query.order_by(users.score.desc()).offset(0).first()
    return {'firstplace': firstplace, 'secplace': secplace, 'thiplace': thiplace}


@app.route("/leaderboard", methods=['GET', 'POST'])
def leaderboard():
    listedusers = users.query.order_by(users.score.desc()).limit(50).all()
    return render_template("leaderboard.html", listedusers=listedusers)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":  
        user = request.form.get("nm")
        email = request.form.get("email")

        print("founduser name")
        maybe_user = users.query.filter_by(name=user).first()
        if maybe_user:
            flash("Username taken. Please choose another!")
            return redirect(url_for("home"))

        print("founduser email")
        found_email = users.query.filter_by(email=email).first()
        if found_email: 
            flash("Email registered to a different user. Please login to existing account or use a different email.")
            return redirect(url_for("home"))
        else:
            if '@' in email:
                if '.' in email:
                            print(" doing else in found_email ")
                            usr = users(user, request.form.get("password"), email, 0)
                            db.session.add(usr)
                            db.session.commit()
                            print(" successfully registered user ")
                            flash("Sucessfully registered!")
                            maybe_user = users.query.filter_by(name=usr.name).first()
                            print("found da user after account made")
                            session["user"] = maybe_user.name
                            print("sendin em away")
                            return redirect(url_for("login"))
                            #do actual email verification?
                else:
                    flash('Please enter a real email address.')
                    return redirect(url_for("home"))
            else:
                flash('Please enter a real email address.')
                return redirect(url_for("home"))

    return render_template("register.html")

@app.route("/clicker")
def clicker():
    if "user" in session:
        #scoreboard render moved to minileaderboard.html, this part is now obsolete but i'm scared to delete it
        thiplace = users.query.order_by(users.score.desc()).offset(2).first()
        secplace = users.query.order_by(users.score.desc()).offset(1).first()
        firstplace = users.query.order_by(users.score.desc()).offset(0).first()

        user = session["user"]
        currentuser = users.query.filter_by(name=user).first()
        score = currentuser.score
        name = currentuser.name
        return render_template("clicker.html", 
                               name=name, 
                               score=score, 
                               firstplace=firstplace,
                               secplace=secplace, 
                               thiplace=thiplace)
    else:  
        flash("You are not logged in!")
        return redirect(url_for("login"))

combo = int(1)
comboclick = int(0)
timesincelastclick = int(100000)

@app.route('/buttonclick', methods=['POST']) 
def buttonclick():
    if "user" in session:
        global timesincelastclick
        global comboclick
        global combo
        nowtime = int(current_milli_time())
        comboclick = int(nowtime - timesincelastclick)
        if comboclick < 500:
            combo += 0.01 #THIS DOES NOTHING RN, USE TURBOFLASK TO PUSH IT INTO THE HTML FILE
            print("combo'd")
        else:
            combo = int(1)
        timesincelastclick = int(current_milli_time())
        #DO NOT SCREW WITH THIS, THIS FUNCTION TOOK ME LIKE 4 HOURS TO GET WORKING WITH THE STUPID FLASK MODULE
        user = session["user"]
        found_user = users.query.filter_by(name=user).first()
        combomultiplier = round((1 * (combo**2)))
        found_user.score += round((1 * combomultiplier))
        db.session.commit()
        if turbo.can_stream():
            print("turbostreamig")# this stuff doesnt fricking work
            return turbo.stream(
            turbo.update(render_template('clicker.html', combomultiplier=combomultiplier), target='comboer')
            )
        else:
            print("not turbostreamig")
            return render_template('clicker.html', combomultiplier=combomultiplier)
        return 'success'

    else:  
        flash("You are not logged in!")
        return redirect(url_for("login"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/view")
def view():
    return render_template("view.html", values = users.query.all())

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True
        user = request.form["nm"]
        password = request.form["password"]
        
        if str.isspace(user) == True:
            flash("Name must include non-space characters!")
            return redirect(url_for("home"))
            
        session["user"] = user


        # how to delete objects:
        # found_user = users.query.filter_by(name=user).delete()
        # db.session.commit()

        found_user = users.query.filter_by(name=user).first()
        if found_user:
            if found_user.password != password:
                flash("Incorrect password!")
                session.pop("user", None)
                return redirect(url_for("home"))



        if found_user: #def include password checking in this too lol
            session["user"] = found_user.name
        else:
            session.pop("user", None)
            flash("Login details incorrect!")
            return redirect(url_for("register"))
            #usr = users(user, "", "", 0) #blanks are temporary to hold spot for user password, email, and score
            #db.session.add(usr)
            #db.session.commit()


        flash("Login Sucessful!")
        return redirect(url_for("user"))
        # above line redirects to page with url as /username, with username displayed on html
    
    else:
        if "user" in session:
            flash("Already logged in!")
            return redirect(url_for("user"))

    return render_template("login.html")

@app.route("/user", methods=["POST", "GET"])
def user():
    if "user" in session:
        user = session["user"]
        founduser = users.query.filter_by(name=user).first()
        return render_template("user.html", name=founduser.name, email=founduser.email, score=founduser.score)
    else:
        flash("You are not logged in!")
        return redirect(url_for("login"))
        
@app.route("/logout")
def logout():
    flash("You have been logged out!", "info")
    session.pop("user", None)
    session.pop("email", None)
    session.pop("score", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)