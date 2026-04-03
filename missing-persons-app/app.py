from flask import Flask, render_template, request, redirect, session
from supabase import create_client
from werkzeug.utils import secure_filename
import requests, os, random
from twilio.rest import Client


app = Flask(__name__)
app.secret_key = "secret"

SUPABASE_URL = "https://vpfwvzhtlwjpgzndhtwd.supabase.co/"
SUPABASE_KEY = "sb_publishable_1pMVcZoDRGn8yNWFaPP6SQ_nmv0ZuTP"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




ACCOUNT_SID = "AC6591ec4ad05b454a4244ac96999e1c2c"
AUTH_TOKEN = "31e2bd2b717ae036b3401098278096ee"
TWILIO_NUMBER = "+13613158676"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms(phone, text):
    try:
        msg = client.messages.create(
            body=text,
            from_=TWILIO_NUMBER,
            to="+91" + phone
        )
        print("✅ SMS SENT:", msg.sid)
    except Exception as e:
        print("❌ ERROR:", e)
# 🏠 HOME
@app.route("/")
def home():
    return render_template("index.html")

# 📂 FILE COMPLAINT
@app.route("/complaint", methods=["GET", "POST"])
def complaint():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]

        photo = request.files["photo"]
        aadhar = request.files["aadhar"]

        photo_name = secure_filename(photo.filename)
        aadhar_name = secure_filename(aadhar.filename)

        photo.save(os.path.join(UPLOAD_FOLDER, photo_name))
        aadhar.save(os.path.join(UPLOAD_FOLDER, aadhar_name))

        supabase.table("missing_persons").insert({
            "name": name,
            "phone": phone,
            "photo": photo_name,
            "aadhar": aadhar_name,
            "status": "pending"
        }).execute()

        return redirect("/")

    return render_template("complaint.html")

# 📊 UPDATE INFO (ONLY APPROVED)
@app.route("/update")
def update():
    data = supabase.table("missing_persons")\
        .select("*")\
        .eq("status", "approved")\
        .execute()

    return render_template("update.html", persons=data.data)

# 🔐 ADMIN LOGIN
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        data = supabase.table("admin").select("*").eq("username", username).execute()

        if data.data and data.data[0]["password"] == password:
            session["admin"] = True
            return redirect("/admin")

    return render_template("admin_login.html")

# 👨‍💻 ADMIN PANEL
@app.route("/admin")
def admin():

    pending = supabase.table("missing_persons") \
        .select("*") \
        .eq("status", "pending") \
        .execute()

    approved = supabase.table("missing_persons") \
        .select("*") \
        .eq("status", "approved") \
        .execute()

    found = supabase.table("missing_persons") \
        .select("*") \
        .eq("status", "found") \
        .execute()
    feedbacks = supabase.table("feedback").select("*").execute()
    print(feedbacks.data) 
    informs = supabase.table("inform").select("*").execute()
     # DEBUG
    print(informs.data)    # DEBUG



    notifications = supabase.table("notifications").select("*").execute()

    return render_template("admin.html",
        pending=pending.data,
        approved=approved.data,
        found=found.data,
        feedbacks=feedbacks.data,
        informs=informs.data,
        notifications=notifications.data)
                             
@app.route("/approve/<int:id>")
def approve(id):
    supabase.table("missing_persons").update({"status": "approved"}).eq("id", id).execute()

    person = supabase.table("missing_persons").select("*").eq("id", id).execute().data[0]

    phone = person["phone"]

    
    citizens = supabase.table("citizens").select("*").execute().data

    for c in citizens:
       

       send_sms(phone, f"""
             🚨 Missing Alert!
              Name: {person['name']}
              IF  YOU FOUND THEM!!!
              Contact: {person['phone']}
               """)

    return redirect("/admin")

# ❌ REJECT
@app.route("/reject/<int:id>")
def reject(id):
    supabase.table("missing_persons").delete().eq("id", id).execute()
    return redirect("/admin")

# 📍 INFORM (MAP + LOCATION)
@app.route("/inform", methods=["GET", "POST"])
def inform():
    if request.method == "POST":
        location = request.form["location"]
        description = request.form["description"]

        # Optional: save to DB
        supabase.table("inform").insert({
            "location": location,
            "description": description
        }).execute()
        return redirect("/")   

    return render_template("inform.html")  
         



@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form.get("name")
        message = request.form.get("message")

        print("DEBUG:", name, message)  # 👈 VERY IMPORTANT

        supabase.table("feedback").insert({
            "name": name,
            "message": message
        }).execute()

        return redirect("/")
    
    return render_template("feedback.html")


@app.route("/found/<int:id>", methods=["GET", "POST"])
def found_login(id):

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # 🔥 check from database
        admin = supabase.table("admin") \
            .select("*") \
            .eq("username", username) \
            .eq("password", password) \
            .execute()

        if admin.data:
            # ✅ correct → mark as found
            supabase.table("missing_persons") \
                .update({"status": "found"}) \
                .eq("id", id) \
                .execute()

            return redirect("/update")

        else:
            return render_template("found_login.html", error="Invalid credentials")

    return render_template("found_login.html")
@app.route("/inform_found/<int:id>")
def inform_admin(id):

    person = supabase.table("missing_persons") \
        .select("*") \
        .eq("id", id) \
        .execute()

    p = person.data[0]

    # 🔥 check if already exists
    existing = supabase.table("notifications") \
        .select("*") \
        .eq("person_id", id) \
        .execute()

    if existing.data:
        return redirect("/update")   # already informed

    # ✅ insert only once
    supabase.table("notifications").insert({
        "person_id": id,
        "message": f"{p['name']} might be found!",
        "status": "pending"
    }).execute()

    return redirect("/update")

@app.route("/delete_notification/<int:id>")
def delete_notification(id):
    if not session.get("admin"):
        return "Unauthorized", 403


    supabase.table("notifications") \
        .delete() \
        .eq("id", id) \
        .execute()

    return redirect("/admin")
# 🔥 DELETE FEEDBACK
@app.route("/delete_feedback/<int:id>")
def delete_feedback(id):
    supabase.table("feedback").delete().eq("id", id).execute()
    feedbacks = supabase.table("feedback").select("*").execute()
    print("FEEDBACK DATA:", feedbacks.data)
    return redirect("/admin")


# 🔥 DELETE INFORM DATA
@app.route("/delete_inform/<int:id>")
def delete_inform(id):
    supabase.table("inform").delete().eq("id", id).execute()
    return redirect("/admin")


port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    send_sms(9959088388, "Twilio SMS working 🚀")
